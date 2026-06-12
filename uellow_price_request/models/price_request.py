# -*- coding: utf-8 -*-
"""Supplier price-update request.

A back-office tool: pick a brand / merchant (uellow.vendor) / supplier
contact / category, pull the matching products into a list, and print a
clean bilingual "Price Update List" the buyer can email to the supplier.
The supplier fills the *New Price* and *Available?* columns and sends it
back; the buyer types the answers in and (optionally) applies the new
prices to the catalogue in one click.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


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

    @api.depends('line_ids', 'line_ids.new_price')
    def _compute_counts(self):
        for r in self:
            r.product_count = len(r.line_ids)
            r.filled_count = len(r.line_ids.filtered(lambda l: l.new_price > 0))

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


class PriceRequestLine(models.Model):
    _name = 'uellow.price.request.line'
    _description = 'Price-Update Request Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    request_id = fields.Many2one(
        'uellow.price.request', required=True, ondelete='cascade')
    product_tmpl_id = fields.Many2one(
        'product.template', string='Product', required=True)
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
