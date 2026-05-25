from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VendorLocation(models.Model):
    """
    Every approved vendor gets one sub-location inside the main Uellow warehouse.
    Location path: WH/VND-{id}-{name}
    """
    _name = 'uellow.vendor.location'
    _description = 'Vendor Sub-Warehouse Location'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one(
        'res.partner', string='Vendor',
        required=True, ondelete='restrict', index=True,
    )
    location_id = fields.Many2one(
        'stock.location', string='Sub-warehouse Location',
        readonly=True,
    )
    location_name = fields.Char(
        compute='_compute_location_name', store=True,
    )
    state = fields.Selection([
        ('active', 'نشط'),
        ('suspended', 'موقوف'),
        ('closed', 'مغلق'),
    ], default='active', string='State', index=True)

    storage_fee = fields.Float('رسوم التخزين (KD/وحدة/شهر)', default=0.5)
    max_days = fields.Integer('أقصى مدة تخزين', default=90)

    restock_count = fields.Integer(compute='_compute_counts', string='طلبات تزويد')
    units_stored = fields.Integer(compute='_compute_counts', string='Units Stored')

    @api.depends('location_id')
    def _compute_location_name(self):
        for r in self:
            r.location_name = r.location_id.complete_name if r.location_id else ''

    def _compute_counts(self):
        for r in self:
            r.restock_count = self.env['uellow.restock.request'].search_count([
                ('vendor_location_id', '=', r.id),
                ('state', 'in', ('draft', 'submitted', 'approved')),
            ])
            if r.location_id:
                quants = self.env['stock.quant'].search([('location_id', '=', r.location_id.id)])
                r.units_stored = int(sum(q.quantity for q in quants))
            else:
                r.units_stored = 0

    @api.model
    def create_for_vendor(self, partner):
        existing = self.search([('partner_id', '=', partner.id)], limit=1)
        if existing:
            return existing
        main_wh = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1)
        if not main_wh:
            raise UserError(_('لا يوجد مخزن رئيسي. أنشئ مخزناً أولاً.'))
        safe = ''.join(c if c.isalnum() else '' for c in partner.name.upper())[:15]
        loc = self.env['stock.location'].create({
            'name': f'VND-{partner.id}-{safe}',
            'location_id': main_wh.lot_stock_id.id,
            'usage': 'internal',
            'comment': f'مخزن فرعي: {partner.name}',
        })
        return self.create({
            'partner_id': partner.id,
            'location_id': loc.id,
            'state': 'active',
        })

    def action_suspend(self):
        self.state = 'suspended'

    def action_activate(self):
        self.state = 'active'

    def action_view_stock(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'مخزون {self.partner_id.name}',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [('location_id', '=', self.location_id.id)],
        }
