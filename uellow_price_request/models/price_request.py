# -*- coding: utf-8 -*-
"""Supplier price-update request.

A back-office tool: pick a brand / merchant (uellow.vendor) / supplier
contact / category, pull the matching products into a list, and print a
clean bilingual "Price Update List" the buyer can email to the supplier.
The supplier fills the *New Price* and *Available?* columns and sends it
back; the buyer types the answers in and (optionally) applies the new
prices to the catalogue in one click.
"""
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PriceRequest(models.Model):
    _name = 'uellow.price.request'
    _description = 'Supplier Price-Update Request'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(
        'Reference', default=lambda s: _('New'), copy=False, tracking=True)
    date = fields.Date('Date', default=fields.Date.context_today, tracking=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('sent', 'Sent to supplier'),
         ('received', 'Prices received'), ('applied', 'Applied')],
        default='draft', tracking=True, string='Status')

    source_type = fields.Selection(
        [('brand', 'Brand'), ('vendor', 'Merchant / Vendor'),
         ('supplier', 'Supplier (contact)'), ('category', 'Category'),
         ('all', 'All products')],
        string='Select by', default='brand', required=True)
    brand_id = fields.Many2one('product.brand', string='Brand')
    vendor_id = fields.Many2one('uellow.vendor', string='Merchant / Vendor')
    supplier_id = fields.Many2one(
        'res.partner', string='Supplier', domain=[('supplier_rank', '>', 0)])
    categ_id = fields.Many2one('product.category', string='Category')
    only_published = fields.Boolean('Only published products', default=False)
    limit = fields.Integer(
        'Max products', default=0,
        help="0 = no limit. Caps how many products are pulled.")

    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda s: s.env.company.currency_id.id)
    supplier_label = fields.Char(
        'Addressed to', compute='_compute_supplier_label', store=True,
        help="Name printed on the report header (the supplier/brand).")
    note = fields.Text(
        'Instructions to supplier',
        default=lambda s: s.env['ir.config_parameter'].sudo().get_param(
            'uellow_price_request.default_note', ''))

    line_ids = fields.One2many(
        'uellow.price.request.line', 'request_id', string='Lines',
        copy=False)
    product_count = fields.Integer(
        'Products', compute='_compute_counts', store=True)
    filled_count = fields.Integer(
        'New prices filled', compute='_compute_counts', store=True)

    # ── Workflow: send to a merchant who responds in portal/app ───────
    merchant_id = fields.Many2one(
        'uellow.vendor', string='Send to merchant',
        help="The merchant who receives this request in their portal and "
             "app to confirm or propose new prices.")
    sent_date = fields.Datetime('Sent on', readonly=True, copy=False)
    responded_date = fields.Datetime('Responded on', readonly=True, copy=False)
    default_margin = fields.Float(
        'Target margin %', default=lambda s: float(
            s.env['ir.config_parameter'].sudo().get_param(
                'uellow_price_request.default_margin', '25') or 25),
        help="Used by the auto-margin engine to suggest a selling price "
             "that preserves this markup over cost.")
    matched_count = fields.Integer(
        'Confirmed (match)', compute='_compute_counts', store=True)
    pending_approval_count = fields.Integer(
        'Awaiting your approval', compute='_compute_counts', store=True)

    @api.depends('source_type', 'brand_id', 'vendor_id', 'supplier_id',
                 'categ_id')
    def _compute_supplier_label(self):
        for r in self:
            label = ''
            if r.source_type == 'brand' and r.brand_id:
                label = r.brand_id.name
            elif r.source_type == 'vendor' and r.vendor_id:
                label = r.vendor_id.display_name
            elif r.source_type == 'supplier' and r.supplier_id:
                label = r.supplier_id.name
            elif r.source_type == 'category' and r.categ_id:
                label = r.categ_id.name
            elif r.source_type == 'all':
                label = _('All products')
            r.supplier_label = label or ''

    @api.depends('line_ids', 'line_ids.new_price', 'line_ids.line_state')
    def _compute_counts(self):
        for r in self:
            r.product_count = len(r.line_ids)
            r.filled_count = len(r.line_ids.filtered(lambda l: l.new_price > 0))
            r.matched_count = len(r.line_ids.filtered(
                lambda l: l.line_state == 'confirmed'))
            r.pending_approval_count = len(r.line_ids.filtered(
                lambda l: l.line_state == 'await'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uellow.price.request') or _('New')
        return super().create(vals_list)

    # ── domain builder ────────────────────────────────────────────────
    def _product_domain(self):
        self.ensure_one()
        domain = []
        if self.source_type == 'brand':
            if not self.brand_id:
                raise UserError(_("Pick a brand first."))
            domain.append(('brand_id', '=', self.brand_id.id))
        elif self.source_type == 'vendor':
            if not self.vendor_id:
                raise UserError(_("Pick a merchant/vendor first."))
            domain.append(('vendor_id', '=', self.vendor_id.id))
        elif self.source_type == 'supplier':
            if not self.supplier_id:
                raise UserError(_("Pick a supplier first."))
            # products that have this partner as a vendor (supplierinfo)
            seller = self.env['product.supplierinfo'].sudo().search(
                [('partner_id', '=', self.supplier_id.id)])
            tmpl_ids = seller.mapped('product_tmpl_id').ids
            domain.append(('id', 'in', tmpl_ids))
        elif self.source_type == 'category':
            if not self.categ_id:
                raise UserError(_("Pick a category first."))
            domain.append(('categ_id', 'child_of', self.categ_id.id))
        # 'all' → no extra filter
        if self.only_published:
            domain.append(('is_published', '=', True))
        domain.append(('sale_ok', '=', True))
        return domain

    # ── actions ───────────────────────────────────────────────────────
    def action_generate_lines(self):
        for r in self:
            r.line_ids.unlink()
            Tmpl = self.env['product.template'].sudo()
            recs = Tmpl.search(
                r._product_domain(), order='name asc',
                limit=(r.limit or None))
            lines = []
            for p in recs:
                lines.append((0, 0, {
                    'product_tmpl_id': p.id,
                    'current_price': p.list_price,
                    'cost': p.standard_price,
                }))
            r.line_ids = lines
        return True

    def action_mark_sent(self):
        self.write({'state': 'sent'})
        return True

    def action_apply_new_prices(self):
        """Write the supplier's New Price back onto the catalogue.
        Only lines with a positive new_price that differs are touched.
        Gated by the global toggle so it can be disabled entirely."""
        allow = self.env['ir.config_parameter'].sudo().get_param(
            'uellow_price_request.allow_apply', '1') in ('1', 'True', 'true')
        if not allow:
            raise UserError(_(
                "Applying prices is disabled in Settings. Enable "
                "'Allow applying supplier prices' first."))
        applied = 0
        for r in self:
            for ln in r.line_ids:
                if ln.new_price and ln.new_price > 0 \
                        and abs(ln.new_price - ln.product_tmpl_id.list_price) > 1e-6:
                    ln.product_tmpl_id.sudo().write({'list_price': ln.new_price})
                    ln.current_price = ln.new_price
                    applied += 1
                # reflect availability if the supplier marked it
                if ln.availability == 'no':
                    ln.product_tmpl_id.sudo().write({'sale_ok': True})
            r.state = 'applied'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Prices applied'),
                'message': _('%s product price(s) updated.') % applied,
                'type': 'success', 'sticky': False,
            },
        }

    def action_print_report(self):
        self.ensure_one()
        if not self.line_ids:
            self.action_generate_lines()
        if self.state == 'draft':
            self.state = 'sent'
        return self.env.ref(
            'uellow_price_request.action_report_price_request'
        ).report_action(self)

    # ── Digital workflow: send → merchant responds → you approve ──────
    def _default_merchant(self):
        """When targeting a single merchant, pre-fill merchant_id."""
        self.ensure_one()
        if not self.merchant_id and self.source_type == 'vendor' and self.vendor_id:
            self.merchant_id = self.vendor_id

    def action_send_to_merchant(self):
        """Push the request to the merchant's portal + app and notify them."""
        for r in self:
            r._default_merchant()
            if not r.merchant_id:
                raise UserError(_(
                    "Pick the merchant to send this request to "
                    "(field 'Send to merchant')."))
            if not r.line_ids:
                r.action_generate_lines()
            if not r.line_ids:
                raise UserError(_("No products to send."))
            # carry the target margin onto each line for the engine
            for ln in r.line_ids:
                if not ln.margin_target:
                    ln.margin_target = r.default_margin
            r.write({'state': 'sent',
                     'sent_date': fields.Datetime.now()})
            r._notify_merchant()
        return True

    def _notify_merchant(self):
        """FCM push + chatter to the merchant that a request awaits them."""
        self.ensure_one()
        try:
            partner = self.merchant_id.user_id.partner_id \
                or self.merchant_id.partner_id
            if partner:
                self.env['mobile.customer.notification'].sudo().push_role(
                    'notify_price_request', partner,
                    title_en='Price update request',
                    title_ar='طلب تحديث أسعار',
                    body_en='%s product(s) need your price confirmation.'
                            % len(self.line_ids),
                    body_ar='%s منتج بانتظار تأكيد سعرك.' % len(self.line_ids),
                    data={'type': 'price_request', 'id': self.id})
        except Exception:
            _logger.warning('price-request merchant push failed',
                            exc_info=True)
        self.message_post(body=_(
            "Sent to merchant %s — %s product(s).")
            % (self.merchant_id.display_name, len(self.line_ids)))

    def submit_response(self, responses):
        """Apply a merchant's response. `responses` is a list of dicts:
          {'line_id': int, 'action': 'match'|'price'|'oos', 'price': float}
        Matched / unchanged lines auto-confirm; changed lines (up or down)
        go to your approval inbox. Returns a summary dict."""
        self.ensure_one()
        by_id = {l.id: l for l in self.line_ids}
        confirmed = changed = oos = 0
        for resp in (responses or []):
            ln = by_id.get(int(resp.get('line_id', 0)))
            if not ln:
                continue
            action = resp.get('action')
            if action == 'oos':
                ln.action_out_of_stock()
                oos += 1
            elif action == 'match':
                ln.action_match()
                confirmed += 1
            elif action == 'price':
                ln.action_set_new_price(float(resp.get('price') or 0))
                if ln.line_state == 'confirmed':
                    confirmed += 1
                else:
                    changed += 1
        self.write({'state': 'received',
                    'responded_date': fields.Datetime.now()})
        self._notify_admin_response(confirmed, changed, oos)
        return {'confirmed': confirmed, 'changed': changed,
                'out_of_stock': oos,
                'pending_approval': self.pending_approval_count}

    def _notify_admin_response(self, confirmed, changed, oos):
        self.ensure_one()
        msg = _("Merchant %s responded: %s confirmed, %s changed "
                "(awaiting your approval), %s out of stock.") % (
                    self.merchant_id.display_name, confirmed, changed, oos)
        self.message_post(body=msg)
        # schedule an activity for the buyer when there are changes to approve
        if changed:
            try:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Price changes need approval — %s') % self.name,
                    note=msg)
            except Exception:
                _logger.debug('activity schedule failed', exc_info=True)
        # FCM to admin program partners (best effort)
        try:
            admins = self.env['mobile.customer.notification'].sudo() \
                ._admin_partners()
            if admins and changed:
                self.env['mobile.customer.notification'].sudo().push_role(
                    'notify_price_request', admins,
                    title_en='Price changes to approve',
                    title_ar='تغييرات أسعار بانتظار موافقتك',
                    body_en='%s changed price(s) from %s.'
                            % (changed, self.merchant_id.display_name),
                    body_ar='%s سعر متغيّر من %s.'
                            % (changed, self.merchant_id.display_name),
                    data={'type': 'price_request', 'id': self.id})
        except Exception:
            _logger.debug('admin push failed', exc_info=True)

    def action_approve_all(self):
        """Approve every awaiting line at the merchant's proposed price."""
        for r in self:
            r.line_ids.filtered(lambda l: l.line_state == 'await') \
                .action_approve()
            if not r.line_ids.filtered(lambda l: l.line_state == 'await'):
                r.state = 'applied'
        return True


class PriceRequestLine(models.Model):
    _name = 'uellow.price.request.line'
    _description = 'Price-Update Request Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        'uellow.price.request', required=True, ondelete='cascade')
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product', required=True)
    image_128 = fields.Image(
        'Image', related='product_tmpl_id.image_128', readonly=True,
        help="Product thumbnail, shown on each line and in the report.")
    default_code = fields.Char(
        'SKU', related='product_tmpl_id.default_code', store=True)
    barcode = fields.Char(
        'Barcode', related='product_tmpl_id.barcode', store=True)
    currency_id = fields.Many2one(related='request_id.currency_id')

    current_price = fields.Float('Current Price', digits='Product Price')
    cost = fields.Float('Cost', digits='Product Price')
    new_price = fields.Float('New Price', digits='Product Price')
    availability = fields.Selection(
        [('yes', 'Available'), ('no', 'Out of stock')],
        string='Available?')
    moq = fields.Char('MOQ')
    line_note = fields.Char('Note')

    # ── Workflow per line ─────────────────────────────────────────────
    response = fields.Selection(
        [('match', 'Match (keep current)'),
         ('changed', 'New price'),
         ('oos', 'Out of stock')],
        string='Merchant response', copy=False)
    line_state = fields.Selection(
        [('pending', 'Pending'),
         ('confirmed', 'Confirmed'),
         ('await', 'Awaiting approval'),
         ('approved', 'Approved'),
         ('rejected', 'Rejected')],
        string='Line status', default='pending', copy=False, index=True)
    responded_on = fields.Datetime('Responded on', copy=False)
    margin_target = fields.Float('Target margin %')
    delta = fields.Float(
        'Δ', compute='_compute_delta', store=True, digits='Product Price')
    delta_pct = fields.Float('Δ %', compute='_compute_delta', store=True)
    new_margin_pct = fields.Float(
        'Margin after %', compute='_compute_delta', store=True)
    suggested_price = fields.Float(
        'Auto-suggested sell', compute='_compute_delta', store=True,
        digits='Product Price',
        help="Price that preserves the target margin over current cost; the "
             "engine never lets approved price drop your margin below it.")

    @api.depends('new_price', 'current_price', 'cost', 'margin_target')
    def _compute_delta(self):
        for l in self:
            np = l.new_price or 0.0
            l.delta = (np - l.current_price) if np else 0.0
            l.delta_pct = (l.delta / l.current_price * 100.0) \
                if (np and l.current_price) else 0.0
            l.new_margin_pct = ((np - l.cost) / np * 100.0) \
                if np else 0.0
            # auto-margin: lowest sell that keeps the target markup on cost
            mt = (l.margin_target or 0.0) / 100.0
            l.suggested_price = round(l.cost * (1.0 + mt), 3) if l.cost else np

    def action_match(self):
        """Merchant keeps the current price → auto-confirmed, no approval."""
        for l in self:
            l.write({
                'new_price': l.current_price,
                'response': 'match',
                'line_state': 'confirmed',
                'availability': 'yes',
                'responded_on': fields.Datetime.now(),
            })
        return True

    def action_set_new_price(self, price):
        """Merchant proposes a price. Same as current → auto-confirm;
        any change (up or down) → awaiting your approval."""
        for l in self:
            same = abs((price or 0.0) - l.current_price) <= 1e-6
            l.write({
                'new_price': price,
                'response': 'match' if same else 'changed',
                'line_state': 'confirmed' if same else 'await',
                'availability': 'yes',
                'responded_on': fields.Datetime.now(),
            })
        return True

    def action_out_of_stock(self):
        for l in self:
            l.write({'response': 'oos', 'availability': 'no',
                     'line_state': 'confirmed',
                     'responded_on': fields.Datetime.now()})
        return True

    def action_approve(self):
        """You approve the merchant's new price → write it to the catalogue."""
        for l in self:
            if l.new_price and l.new_price > 0 and abs(
                    l.new_price - l.product_tmpl_id.list_price) > 1e-6:
                l.product_tmpl_id.sudo().write({'list_price': l.new_price})
            l.current_price = l.new_price
            l.line_state = 'approved'
        return True

    def action_reject(self):
        """Keep the current price; mark the proposed change rejected."""
        for l in self:
            l.write({'line_state': 'rejected'})
        return True
