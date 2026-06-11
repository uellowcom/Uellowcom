import base64
import json
import logging
import re

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ImportJobLine(models.Model):
    """
    One line per product found/matched in a Smart Connector job.
    Stores raw extracted data + AI-enriched data + review decision.
    """
    _name = 'uellow.import.job.line'
    _description = 'Import Job Line'
    _order = 'job_id, has_warning desc, id'

    job_id = fields.Many2one(
        'uellow.import.job', required=True,
        ondelete='cascade', index=True,
    )

    # Product names
    name_en = fields.Char('Name (EN)', required=True)
    name_ar = fields.Char('Name (AR)')

    # Descriptions
    description_en = fields.Text('Description (EN)')
    description_ar = fields.Text('Description (AR)')

    # Pricing — sale
    new_price = fields.Float('New Sale Price')
    old_price = fields.Float('Current Sale Price', readonly=True)
    price_diff_pct = fields.Float(
        compute='_compute_price_diff', string='Sale Δ (%)', store=True,
    )
    update_price = fields.Boolean('Update Sale Price', default=True)

    # Pricing — cost
    new_cost = fields.Float('New Cost')
    old_cost = fields.Float('Current Cost', readonly=True)
    cost_diff_pct = fields.Float(
        compute='_compute_price_diff', string='Cost Δ (%)', store=True,
    )
    update_cost = fields.Boolean('Update Cost', default=True)
    margin_pct = fields.Float(
        compute='_compute_price_diff', string='Margin (%)', store=True,
        help='(Sale − Cost) / Sale, using the new values.')

    # Stock
    new_qty = fields.Integer('New Quantity')

    # Identifiers — barcode & internal reference
    new_barcode = fields.Char('New Barcode')
    old_barcode = fields.Char('Current Barcode', readonly=True)
    update_barcode = fields.Boolean('Update Barcode', default=True)
    new_reference = fields.Char('New Reference')
    old_reference = fields.Char('Current Reference', readonly=True)
    update_reference = fields.Boolean('Update Reference', default=True)
    missing_info = fields.Char(
        compute='_compute_missing', string='Missing on Catalog', store=True,
        help='Fields empty on the matched product that this row can fill.')

    # eCommerce categorisation (website categories, used on create/re-classify)
    ecommerce_categ_ids = fields.Many2many(
        'product.public.category', string='eCommerce Categories')

    # Out-of-stock handling
    is_out_of_stock = fields.Boolean('Out of Stock (sheet)', readonly=True,
        help='The source row says the product is out of stock / qty 0 / unavailable.')
    existing_continue_selling = fields.Boolean(
        'Currently Continues Selling', readonly=True,
        help="The matched product's 'Continue selling when out of stock' flag.")
    disable_continue_selling = fields.Boolean(
        'Stop Selling When Out',
        help='On apply, turn OFF "Continue selling when Out-of-Stock" for this product.')
    show_continue_warn = fields.Boolean(compute='_compute_continue_warn')

    match_method = fields.Selection([
        ('barcode',  'Barcode match'),
        ('reference', 'Reference match'),
        ('name',     'Name (fuzzy)'),
        ('none',     'No match'),
    ], string='Matched by', default='none', readonly=True)

    # Source info
    source_sku = fields.Char('Source SKU')
    source_url = fields.Char('Source URL')
    image_url = fields.Char('Image URL')

    # Matching
    product_action = fields.Selection([
        ('new',    'New Product'),
        ('update', 'Update Existing Product'),
        ('skip',   'Ignore'),
    ], default='new', string='Action', required=True)

    match_score = fields.Integer('Match Confidence (%)', default=0)
    existing_product_id = fields.Many2one(
        'product.template', string='Existing Product',
        ondelete='set null',
    )

    # Line status — `index` accelerates the (job_id, line_state) lookup that
    # the review wizard and dashboard hit constantly.
    line_state = fields.Selection([
        ('pending',  'Awaiting Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('applied',  'Applied'),
    ], default='pending', string='Line Status', index=True)

    has_warning = fields.Boolean('Warning', default=False, index=True)
    warning_reason = fields.Char('Warning Reason')
    ai_enriched = fields.Boolean('AI Enriched', default=False)

    reject_reason = fields.Selection([
        ('price_unrealistic',   'Unreasonable Price'),
        ('bad_description',     'Insufficient Description'),
        ('bad_images',          'Bad Images'),
        ('wrong_category',      'Wrong Category'),
        ('duplicate',           'Duplicate Product'),
        ('other',               'Other'),
    ], string='Rejection Reason')
    reject_note = fields.Char('Rejection Note')

    # Applied product
    applied_product_id = fields.Many2one(
        'product.template', string='Applied Product', readonly=True,
    )

    @api.depends('new_price', 'old_price', 'new_cost', 'old_cost')
    def _compute_price_diff(self):
        for l in self:
            l.price_diff_pct = ((l.new_price - l.old_price) / l.old_price * 100
                                if l.old_price and l.old_price > 0 else 0.0)
            l.cost_diff_pct = ((l.new_cost - l.old_cost) / l.old_cost * 100
                               if l.old_cost and l.old_cost > 0 else 0.0)
            l.margin_pct = ((l.new_price - l.new_cost) / l.new_price * 100
                            if l.new_price and l.new_price > 0 else 0.0)

    @api.depends('is_out_of_stock', 'existing_continue_selling', 'product_action',
                 'existing_product_id')
    def _compute_continue_warn(self):
        for l in self:
            l.show_continue_warn = bool(
                l.product_action == 'update' and l.existing_product_id
                and l.is_out_of_stock and l.existing_continue_selling)

    def action_disable_continue_now(self):
        """Immediately turn OFF 'continue selling when out of stock' on the
        matched product (so it stops being sellable while out of stock)."""
        for line in self:
            if line.existing_product_id:
                line.existing_product_id.allow_out_of_stock_order = False
                line.existing_continue_selling = False
                line.disable_continue_selling = True
                line.job_id.message_post(body=_(
                    'Disabled continue-selling for "%s" (out of stock).'
                ) % (line.existing_product_id.name or line.name_en))

    @api.depends('product_action', 'old_barcode', 'old_reference',
                 'new_barcode', 'new_reference')
    def _compute_missing(self):
        for l in self:
            miss = []
            if l.product_action == 'update':
                if l.new_barcode and not l.old_barcode:
                    miss.append('Barcode')
                if l.new_reference and not l.old_reference:
                    miss.append('Reference')
            l.missing_info = ', '.join(miss)

    @api.constrains('new_price', 'new_qty')
    def _check_non_negative(self):
        for l in self:
            if l.new_price < 0:
                raise UserError(_('Price cannot be negative.'))
            if l.new_qty < 0:
                raise UserError(_('Quantity cannot be negative.'))

    def action_approve(self):
        # B6: ensure scalar writes on a recordset don't crash with `expected singleton`.
        for line in self:
            line.line_state = 'approved'
            if not line.product_action:
                line.product_action = 'new'

    def action_reject(self):
        # D5: require a reason — silent rejections lose audit trail.
        for line in self:
            if not line.reject_reason:
                raise UserError(_(
                    'Set a rejection reason before rejecting line "%s".') % (line.name_en or line.id))
            line.line_state = 'rejected'

    def action_apply(self):
        """Apply this single line to product catalog."""
        self.ensure_one()
        if self.line_state != 'approved':
            return
        product = self._apply_to_catalog()
        self.applied_product_id = product
        self.line_state = 'applied'

    # ──────────────────────────────────────────────────────────────────
    # Catalog write — also feeds rollback_data so action_rollback can
    # undo BOTH updates (restore old vals) AND creates (archive).
    # ──────────────────────────────────────────────────────────────────
    def _apply_to_catalog(self):
        """Create or update product.template from this line's data."""
        self.ensure_one()
        vals = self._product_vals_for_write()
        job = self.job_id

        if self.product_action == 'update' and self.existing_product_id:
            ep = self.existing_product_id
            self._snapshot_for_rollback(job, ep)
            ep.write(vals)
            self._apply_gallery(ep)
            # Optionally adjust stock if qty is positive — left as a TODO
            # because it needs a stock.change.product.qty wizard call.
            return ep

        # CREATE path — for rollback we just remember the new product id so
        # `action_rollback` can archive it (delete is unsafe if movements exist).
        new_prod = self.env['product.template'].create(vals)
        self._track_created_for_rollback(job, new_prod)
        self._apply_gallery(new_prod)
        return new_prod

    def _product_vals_for_write(self):
        """Build the vals dict for product.template.create/write.

        UPDATE: write ONLY the fields the reviewer toggled on (sale price, cost,
        barcode, reference) — never silently overwrite catalog name/identifiers.
        CREATE: write the full product (name, prices, identifiers, category,
        description, image).
        """
        self.ensure_one()
        is_new = not (self.product_action == 'update' and self.existing_product_id)

        if not is_new:
            # ── UPDATE: selective writes ──
            v = {}
            if self.update_price and self.new_price:
                v['list_price'] = self.new_price
            if self.update_cost and self.new_cost:
                v['standard_price'] = self.new_cost
            if self.update_barcode and self.new_barcode:
                v['barcode'] = self.new_barcode
            if self.update_reference and self.new_reference:
                v['default_code'] = self.new_reference
            if self.ecommerce_categ_ids:
                v['public_categ_ids'] = [(6, 0, self.ecommerce_categ_ids.ids)]
            if self.disable_continue_selling:
                v['allow_out_of_stock_order'] = False
            # translation only enriches the AR description, never clobbers name
            if self.ai_enriched and self.description_ar:
                v['description_sale'] = self.description_ar
            # fill the website body only when the catalog product has none yet,
            # so we never clobber copy a human already wrote.
            ep = self.existing_product_id
            if not (ep.website_description or '').strip():
                body = self._website_body_html()
                if body:
                    v['website_description'] = body
            # set a main image only when the product is missing one
            if not ep.image_1920:
                img_bin = self._main_image_b64()
                if img_bin:
                    v['image_1920'] = img_bin
            return v

        # ── CREATE: full product ──
        v = {
            'name': self.name_ar or self.name_en,
            'list_price': self.new_price or 0.0,
            'type': 'consu',
        }
        if self.new_cost:
            v['standard_price'] = self.new_cost
        if self.new_barcode:
            v['barcode'] = self.new_barcode
        if self.new_reference or self.source_sku:
            v['default_code'] = self.new_reference or self.source_sku
        if self.ecommerce_categ_ids:
            v['public_categ_ids'] = [(6, 0, self.ecommerce_categ_ids.ids)]
        if self.description_ar:
            v['description_sale'] = self.description_ar
        elif self.description_en:
            v['description_sale'] = self.description_en
        # eCommerce/website body — what shows on the product page. Prefer the
        # Arabic marketing description; fall back to English.
        body = self._website_body_html()
        if body:
            v['website_description'] = body
        img_bin = self._main_image_b64()
        if img_bin:
            v['image_1920'] = img_bin
        return v

    def _fetch_image_binary(self):
        """Return base64-encoded image bytes from `image_url`, or None on error."""
        self.ensure_one()
        url = (self.image_url or '').strip()
        if not (url.startswith('http://') or url.startswith('https://')):
            return None
        try:
            r = requests.get(url, timeout=10, stream=True)
            r.raise_for_status()
            # Cap to ~5 MB to avoid huge attachments
            chunks = []
            total = 0
            for chunk in r.iter_content(chunk_size=64 * 1024):
                chunks.append(chunk)
                total += len(chunk)
                if total > 5 * 1024 * 1024:
                    return None
            return base64.b64encode(b''.join(chunks))
        except Exception as e:
            _logger.info('Smart Connector: image fetch failed for %s: %s', url, e)
            return None

    def _main_image_b64(self):
        """Main product image: the chosen candidate (e.g. a photo embedded in
        the supplier sheet), else the first candidate, else the URL fetch."""
        self.ensure_one()
        cands = self.candidate_ids
        main = cands.filtered(lambda c: c.is_main and c.image) \
            or cands.filtered('image')[:1]
        if main and main[0].image:
            return main[0].image
        return self._fetch_image_binary()

    def _website_body_html(self):
        """Build the eCommerce body HTML from the (AI) description."""
        self.ensure_one()
        text = self.description_ar or self.description_en or ''
        text = text.strip()
        if not text:
            return False
        # already HTML? keep as-is; otherwise wrap paragraphs.
        if '<' in text and '>' in text:
            return text
        paras = [p.strip() for p in re.split(r'\n{2,}|\r\n\r\n', text) if p.strip()]
        return ''.join('<p>%s</p>' % p.replace('\n', '<br/>') for p in paras) \
            or '<p>%s</p>' % text

    def _apply_gallery(self, product):
        """Attach the non-main image candidates as the product's gallery —
        only when the product has no gallery yet (never clobber existing)."""
        self.ensure_one()
        if 'product.image' not in self.env:
            return
        if product.product_template_image_ids:
            return
        extras = self.candidate_ids.filtered(
            lambda c: c.image and c.include and not c.is_main)
        if not extras:
            return
        self.env['product.image'].create([{
            'product_tmpl_id': product.id,
            'name': (self.name_ar or self.name_en or _('Image'))[:60],
            'image_1920': c.image,
        } for c in extras])

    @staticmethod
    def _snapshot_for_rollback(job, product):
        """Store enough vals to undo a write — keys map to product fields."""
        rb = json.loads(job.rollback_data) if job.rollback_data else {}
        if not isinstance(rb, dict) or ('updates' not in rb and 'creates' not in rb):
            # Migrate the old flat shape {id: vals} → new shape.
            rb = {'updates': rb if isinstance(rb, dict) else {}, 'creates': []}
        rb.setdefault('updates', {})
        rb.setdefault('creates', [])
        # Don't overwrite an earlier snapshot — first one wins.
        pid = str(product.id)
        if pid not in rb['updates']:
            rb['updates'][pid] = {
                'name':             product.name,
                'description_sale': product.description_sale or '',
                'list_price':       product.list_price,
                'standard_price':   product.standard_price,
                'default_code':     product.default_code or False,
                'barcode':          product.barcode or False,
                'allow_out_of_stock_order': product.allow_out_of_stock_order,
                'active':           product.active,
            }
        job.rollback_data = json.dumps(rb)

    @staticmethod
    def _track_created_for_rollback(job, product):
        rb = json.loads(job.rollback_data) if job.rollback_data else {}
        if not isinstance(rb, dict) or ('updates' not in rb and 'creates' not in rb):
            rb = {'updates': rb if isinstance(rb, dict) else {}, 'creates': []}
        rb.setdefault('updates', {})
        rb.setdefault('creates', [])
        if product.id not in rb['creates']:
            rb['creates'].append(product.id)
        job.rollback_data = json.dumps(rb)
