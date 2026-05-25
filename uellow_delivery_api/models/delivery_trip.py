from odoo import models, fields, api


class DeliveryTrip(models.Model):
    """A delivery trip — groups multiple pickings for one driver."""
    _name = 'uellow.delivery.trip'
    _description = 'Delivery Trip'
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(readonly=True, default='New')
    driver_id = fields.Many2one('res.users', string='Driver', index=True)
    date = fields.Date('Trip Date', default=fields.Date.today)

    state = fields.Selection([
        ('draft',     'Draft'),
        ('assigned',  'Assigned'),
        ('in_progress','In Progress'),
        ('completed', 'Completed'),
    ], default='draft', index=True)

    picking_ids = fields.Many2many(
        'stock.picking', string='Deliveries',
    )
    total_orders = fields.Integer(compute='_compute_totals', store=True)
    cod_total = fields.Float('COD Total (KD)', compute='_compute_totals', store=True)
    cod_collected = fields.Float('COD Collected (KD)', default=0.0)

    @api.depends('picking_ids')
    def _compute_totals(self):
        for trip in self:
            trip.total_orders = len(trip.picking_ids)
            # Sum COD orders
            sale_orders = trip.picking_ids.mapped('sale_id')
            trip.cod_total = sum(
                o.amount_total for o in sale_orders
                if o.payment_term_id and 'cod' in (o.payment_term_id.name or '').lower()
            )

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('uellow.delivery.trip') or 'New'
        return super().create(vals_list)
