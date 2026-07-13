# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


class WarrantyCard(models.Model):
    _name = 'uellow.warranty.card'
    _description = 'Warranty Card'
    _order = 'date_start desc, id desc'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Warranty No.', default='New', copy=False, readonly=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, tracking=True)
    lot_serial = fields.Char(string='Serial / Lot')
    policy_id = fields.Many2one('uellow.warranty.policy', string='Policy', required=True, tracking=True)
    duration_months = fields.Integer(related='policy_id.duration_months', store=True, readonly=True)
    date_start = fields.Date(string='Start', default=fields.Date.context_today, required=True, tracking=True)
    date_end = fields.Date(string='Expiry', compute='_compute_date_end', store=True, tracking=True)
    days_left = fields.Integer(string='Days left', compute='_compute_days_left')
    state = fields.Selection(
        [('active', 'Active'), ('expired', 'Expired'),
         ('void', 'Void'), ('claimed', 'Claimed')],
        default='active', compute='_compute_state', store=True, tracking=True)
    voided = fields.Boolean(string='Voided')
    invoice_id = fields.Many2one('account.move', string='Source invoice', readonly=True)
    sale_id = fields.Many2one('sale.order', string='Sale order', readonly=True)
    pos_order_id = fields.Many2one('pos.order', string='POS order', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Delivery', readonly=True)
    source_label = fields.Char(compute='_compute_source_label', string='Source')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    claim_ids = fields.One2many('uellow.warranty.claim', 'card_id', string='Claims')
    claim_count = fields.Integer(compute='_compute_claim_count', string='Claim count')
    note = fields.Text()

    @api.depends('date_start', 'duration_months')
    def _compute_date_end(self):
        for r in self:
            if r.date_start and r.duration_months:
                r.date_end = r.date_start + relativedelta(months=r.duration_months)
            else:
                r.date_end = r.date_start

    def _compute_days_left(self):
        today = fields.Date.context_today(self)
        for r in self:
            r.days_left = (r.date_end - today).days if r.date_end else 0

    @api.depends('date_end', 'voided', 'claim_ids.state')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for r in self:
            if r.voided:
                r.state = 'void'
            elif any(c.state in ('approved', 'resolved') for c in r.claim_ids):
                r.state = 'claimed'
            elif r.date_end and r.date_end < today:
                r.state = 'expired'
            else:
                r.state = 'active'

    def _compute_claim_count(self):
        for r in self:
            r.claim_count = len(r.claim_ids)

    def _compute_source_label(self):
        for r in self:
            if r.pos_order_id:
                r.source_label = 'POS · %s' % r.pos_order_id.name
            elif r.invoice_id:
                r.source_label = 'Invoice · %s' % r.invoice_id.name
            elif r.sale_id:
                r.source_label = 'Order · %s' % r.sale_id.name
            else:
                r.source_label = 'Manual'

    @api.model
    def issue(self, partner, product, date_start=None, months=None,
              invoice=None, sale=None, pos=None, picking=None, company=None):
        """Idempotently issue a warranty card for a product from a source doc.
        Skips service products, no-warranty policies, and duplicates per source."""
        if not partner or not product or product.type == 'service':
            return self.browse()
        Policy = self.env['uellow.warranty.policy']
        policy = Policy._get_for_product(product)
        if not policy or policy.no_warranty:
            return self.browse()
        existing = self.search([
            ('product_id', '=', product.id),
            '|', '|', '|',
            ('invoice_id', '=', invoice.id if invoice else 0),
            ('sale_id', '=', sale.id if sale else 0),
            ('pos_order_id', '=', pos.id if pos else 0),
            ('picking_id', '=', picking.id if picking else 0),
        ], limit=1)
        if existing:
            return existing
        return self.create({
            'partner_id': partner.id,
            'product_id': product.id,
            'policy_id': policy.id,
            'date_start': date_start or fields.Date.context_today(self),
            'invoice_id': invoice.id if invoice else False,
            'sale_id': sale.id if sale else (invoice.line_ids.sale_line_ids[:1].order_id.id if invoice and invoice.line_ids.sale_line_ids else False),
            'pos_order_id': pos.id if pos else False,
            'picking_id': picking.id if picking else False,
            'company_id': (company or self.env.company).id,
        })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in (False, 'New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'uellow.warranty.card') or 'WRT/0001'
        return super().create(vals_list)

    def action_void(self):
        self.write({'voided': True})

    def action_unvoid(self):
        self.write({'voided': False})

    def action_view_claims(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Claims',
            'res_model': 'uellow.warranty.claim',
            'view_mode': 'list,form',
            'domain': [('card_id', '=', self.id)],
            'context': {'default_card_id': self.id},
        }

    def action_print_certificate(self):
        return self.env.ref(
            'uellow_warranty.action_report_warranty_certificate').report_action(self)

    @api.model
    def _cron_update_states(self):
        """Recompute states so expired warranties flip even without edits."""
        today = fields.Date.context_today(self)
        stale = self.search([('state', '=', 'active'), ('date_end', '<', today)])
        stale._compute_state()
