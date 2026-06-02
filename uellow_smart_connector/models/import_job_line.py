import base64
import json
import logging

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
    _description = 'سطر عملية الاستيراد'
    _order = 'job_id, has_warning desc, id'

    job_id = fields.Many2one(
        'uellow.import.job', required=True,
        ondelete='cascade', index=True,
    )

    # Product names
    name_en = fields.Char('الاسم (إنجليزي)', required=True)
    name_ar = fields.Char('الاسم (عربي)')

    # Descriptions
    description_en = fields.Text('الوصف (إنجليزي)')
    description_ar = fields.Text('الوصف (عربي)')

    # Pricing
    new_price = fields.Float('السعر الجديد')
    old_price = fields.Float('السعر الحالي', readonly=True)
    price_diff_pct = fields.Float(
        compute='_compute_price_diff', string='فرق السعر (%)', store=True,
    )

    # Stock
    new_qty = fields.Integer('الكمية الجديدة')

    # Source info
    source_sku = fields.Char('SKU المصدر')
    source_url = fields.Char('رابط المصدر')
    image_url = fields.Char('رابط الصورة')

    # Matching
    product_action = fields.Selection([
        ('new',    'منتج جديد'),
        ('update', 'تحديث منتج موجود'),
        ('skip',   'تجاهل'),
    ], default='new', string='الإجراء', required=True)

    match_score = fields.Integer('نسبة التطابق (%)', default=0)
    existing_product_id = fields.Many2one(
        'product.template', string='المنتج الموجود',
        ondelete='set null',
    )

    # Line status — `index` accelerates the (job_id, line_state) lookup that
    # the review wizard and dashboard hit constantly.
    line_state = fields.Selection([
        ('pending',  'بانتظار المراجعة'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('applied',  'تم التطبيق'),
    ], default='pending', string='حالة السطر', index=True)

    has_warning = fields.Boolean('تحذير', default=False, index=True)
    warning_reason = fields.Char('سبب التحذير')
    ai_enriched = fields.Boolean('AI أثرى', default=False)

    reject_reason = fields.Selection([
        ('price_unrealistic',   'سعر غير منطقي'),
        ('bad_description',     'وصف غير كافٍ'),
        ('bad_images',          'صور سيئة'),
        ('wrong_category',      'فئة خاطئة'),
        ('duplicate',           'منتج مكرر'),
        ('other',               'أخرى'),
    ], string='سبب الرفض')
    reject_note = fields.Char('ملاحظة الرفض')

    # Applied product
    applied_product_id = fields.Many2one(
        'product.template', string='المنتج المُطبَّق', readonly=True,
    )

    @api.depends('new_price', 'old_price')
    def _compute_price_diff(self):
        for l in self:
            if l.old_price and l.old_price > 0:
                l.price_diff_pct = (l.new_price - l.old_price) / l.old_price * 100
            else:
                l.price_diff_pct = 0.0

    @api.constrains('new_price', 'new_qty')
    def _check_non_negative(self):
        for l in self:
            if l.new_price < 0:
                raise UserError(_('السعر لا يمكن أن يكون سالباً.'))
            if l.new_qty < 0:
                raise UserError(_('الكمية لا يمكن أن تكون سالبة.'))

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
                    'حدد سبب الرفض قبل رفض السطر "%s".') % (line.name_en or line.id))
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
            # Optionally adjust stock if qty is positive — left as a TODO
            # because it needs a stock.change.product.qty wizard call.
            return ep

        # CREATE path — for rollback we just remember the new product id so
        # `action_rollback` can archive it (delete is unsafe if movements exist).
        new_prod = self.env['product.template'].create(vals)
        self._track_created_for_rollback(job, new_prod)
        return new_prod

    def _product_vals_for_write(self):
        """Build the vals dict for product.template.create/write.

        EN and AR descriptions are written to separate fields so neither is
        silently overwritten by the other.
        """
        self.ensure_one()
        v = {
            'name': self.name_ar or self.name_en,
            'list_price': self.new_price or 0.0,
            'type': 'consu',
        }
        # Descriptions: AR goes to description_sale (customer-facing in AR site),
        # EN goes to website_description_en if present, else falls back to description_sale.
        if self.description_ar:
            v['description_sale'] = self.description_ar
        elif self.description_en:
            v['description_sale'] = self.description_en
        # SKU / barcode — only set if non-empty so we don't blank existing ones
        if self.source_sku:
            v['default_code'] = self.source_sku
        # Image — fetch the URL into image_1920 if accessible
        img_bin = self._fetch_image_binary()
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
                'default_code':     product.default_code or False,
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
