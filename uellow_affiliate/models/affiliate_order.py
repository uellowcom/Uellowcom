# -*- coding: utf-8 -*-
"""Affiliate-submitted orders: the agent fills customer + items, Uellow
admin reviews, approval creates the real sale.order + pending commission."""
from odoo import api, fields, models
from odoo.exceptions import UserError


class UellowAffiliateOrder(models.Model):
    _name = 'uellow.affiliate.order'
    _description = 'Affiliate submitted order'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(default=lambda self: self.env['ir.sequence']
                       .next_by_code('uellow.affiliate.order') or 'AFF-ORD')
    affiliate_id = fields.Many2one('uellow.affiliate', required=True,
                                   ondelete='cascade', index=True)
    state = fields.Selection([
        ('draft', '✏️ Draft'),
        ('submitted', '📨 Submitted'),
        ('approved', '✅ Approved'),
        ('rejected', '❌ Rejected'),
    ], default='draft', required=True, tracking=True, index=True)

    # customer data the agent collected
    customer_name = fields.Char(required=True)
    customer_phone = fields.Char(required=True)
    customer_area = fields.Char(string='Area / City')
    customer_address = fields.Text(string='Address details')
    customer_note = fields.Text(string='Note for delivery')

    line_ids = fields.One2many('uellow.affiliate.order.line', 'order_id',
                               string='Items')
    amount_total = fields.Monetary(compute='_compute_total', store=True,
                                   currency_field='currency_id')
    est_commission = fields.Monetary(compute='_compute_total', store=True,
                                     currency_field='currency_id',
                                     string='Estimated commission')
    sale_order_id = fields.Many2one('sale.order', readonly=True,
                                    ondelete='set null')
    reject_reason = fields.Char()
    website_id = fields.Many2one('website')
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id)

    @api.depends('line_ids.qty', 'line_ids.price_unit',
                 'line_ids.commission_pct')
    def _compute_total(self):
        for o in self:
            o.amount_total = sum(l.qty * l.price_unit for l in o.line_ids)
            o.est_commission = sum(
                l.qty * l.price_unit * (l.commission_pct / 100.0)
                for l in o.line_ids)

    def action_submit(self):
        for o in self:
            if not o.line_ids:
                raise UserError('Add at least one item before submitting.')
            o.state = 'submitted'

    def action_approve(self):
        """Create the real sale.order: find-or-create the customer by
        phone, copy the lines, link the affiliate, book the PENDING
        commission. Confirmation of the SO is left to normal ops flow."""
        Partner = self.env['res.partner'].sudo()
        for o in self.filtered(lambda r: r.state == 'submitted'):
            phone = (o.customer_phone or '').strip()
            partner = Partner.search(
                ['|', ('phone', '=', phone), ('mobile', '=', phone)],
                limit=1) if phone else Partner
            if not partner:
                partner = Partner.create({
                    'name': o.customer_name,
                    'phone': phone,
                    'street': (o.customer_address or '')[:128],
                    'city': o.customer_area or '',
                    'company_type': 'person',
                })
            so_vals = {
                'partner_id': partner.id,
                'origin': o.name,
                'uellow_affiliate_id': o.affiliate_id.id,
                'note': 'Affiliate order by %s (%s).\n%s' % (
                    o.affiliate_id.name, o.affiliate_id.code,
                    o.customer_note or ''),
                'order_line': [(0, 0, {
                    'product_id': l.product_id.id,
                    'product_uom_qty': l.qty,
                    'price_unit': l.price_unit,
                }) for l in o.line_ids],
            }
            if o.website_id:
                so_vals['website_id'] = o.website_id.id
            so = self.env['sale.order'].sudo().create(so_vals)
            try:
                so.action_confirm()
            except Exception:
                pass    # leave as quotation if confirmation rules block it
            o.write({'state': 'approved', 'sale_order_id': so.id})
            self.env['uellow.affiliate.commission'].sudo().create({
                'affiliate_id': o.affiliate_id.id,
                'sale_order_id': so.id,
                'source': 'submitted',
                'base_amount': o.amount_total,
                'amount': o.est_commission,
                'note': o.name,
            })

    def action_reject(self):
        self.filtered(lambda r: r.state == 'submitted').write(
            {'state': 'rejected'})


class UellowAffiliateOrderLine(models.Model):
    _name = 'uellow.affiliate.order.line'
    _description = 'Affiliate submitted order line'

    order_id = fields.Many2one('uellow.affiliate.order', required=True,
                               ondelete='cascade')
    product_id = fields.Many2one('product.product', required=True,
                                 ondelete='restrict')
    qty = fields.Float(default=1.0, required=True)
    price_unit = fields.Float(string='Unit price')
    commission_pct = fields.Float(string='Commission %')

    @api.onchange('product_id')
    def _onchange_product(self):
        for l in self:
            if l.product_id:
                l.price_unit = l.product_id.list_price
                if l.order_id.affiliate_id:
                    l.commission_pct = (l.order_id.affiliate_id
                                        .commission_pct_for(
                                            l.product_id.product_tmpl_id))
