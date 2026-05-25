from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class FlashSale(models.Model):
    """
    Flash sale — vendor schedules a time-limited discount.
    Uellow takes an extra 1% commission on Flash Sale orders.
    """
    _name = 'uellow.flash.sale'
    _description = 'Flash Sale'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'start_datetime desc'

    name = fields.Char('Sale Name', required=True, default='Flash Sale')
    vendor_id = fields.Many2one(
        'uellow.vendor', required=True, ondelete='cascade', index=True,
    )
    state = fields.Selection([
        ('draft',    'Draft'),
        ('active',   'Active'),
        ('ended',    'Ended'),
        ('cancelled','Cancelled'),
    ], default='draft', string='Status', tracking=True, index=True)

    start_datetime = fields.Datetime('Start', required=True)
    end_datetime = fields.Datetime('End', required=True)
    discount_pct = fields.Float('Discount (%)', required=True)
    extra_commission = fields.Float(
        'Extra Commission (%)', default=1.0,
        help='Additional commission Uellow charges on Flash Sale orders',
    )
    max_quantity = fields.Integer('Max Units', default=0,
                                  help='0 = unlimited')

    product_ids = fields.Many2many(
        'product.template', string='Products',
        relation='uellow_flash_sale_products',
    )

    # Stats
    units_sold = fields.Integer('Units Sold', default=0, readonly=True)
    revenue = fields.Float('Revenue', default=0.0, readonly=True)

    # Countdown display
    remaining_seconds = fields.Integer(
        compute='_compute_remaining', string='Remaining Seconds',
    )

    @api.depends('end_datetime')
    def _compute_remaining(self):
        now = fields.Datetime.now()
        for sale in self:
            if sale.end_datetime and sale.end_datetime > now:
                delta = sale.end_datetime - now
                sale.remaining_seconds = int(delta.total_seconds())
            else:
                sale.remaining_seconds = 0

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for sale in self:
            if sale.end_datetime <= sale.start_datetime:
                raise UserError(_('End date must be after start date.'))
            if not sale.product_ids:
                raise UserError(_('Select at least one product.'))

    def action_activate(self):
        for sale in self:
            sale.state = 'active'
            # Apply pricelist discounts (website_sale)
            sale._apply_discounts()

    def action_end(self):
        for sale in self:
            sale.state = 'ended'
            sale._remove_discounts()

    def action_cancel(self):
        for sale in self:
            sale.state = 'cancelled'
            sale._remove_discounts()

    def _apply_discounts(self):
        """Set sale price on products."""
        for product in self.product_ids:
            if not product.lst_price:
                continue
            sale_price = product.lst_price * (1 - self.discount_pct / 100)
            product.write({
                'flash_sale_id': self.id,
                'flash_sale_price': sale_price,
            })

    def _remove_discounts(self):
        """Remove sale prices."""
        self.product_ids.filtered(
            lambda p: p.flash_sale_id == self
        ).write({'flash_sale_id': False, 'flash_sale_price': 0.0})

    @api.model
    def cron_update_flash_sales(self):
        """Cron: activate due sales, end expired ones."""
        now = fields.Datetime.now()
        # Activate
        due = self.search([
            ('state', '=', 'draft'),
            ('start_datetime', '<=', now),
        ])
        due.action_activate()
        # End expired
        expired = self.search([
            ('state', '=', 'active'),
            ('end_datetime', '<=', now),
        ])
        expired.action_end()
