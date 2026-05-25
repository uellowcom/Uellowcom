from odoo import models, fields, api, _


class SaleOrder(models.Model):
    """Extend sale.order with vendor info and commission tracking."""
    _inherit = 'sale.order'

    vendor_id = fields.Many2one(
        'uellow.vendor', string='Vendor',
        index=True, ondelete='set null',
    )
    vendor_rating = fields.Float('Vendor Rating', default=0.0)
    commission_id = fields.Many2one(
        'uellow.vendor.commission', string='Commission',
        readonly=True, copy=False,
    )
    flash_sale_id = fields.Many2one(
        'uellow.flash.sale', string='Flash Sale',
        ondelete='set null', copy=False,
    )
    is_flash_sale = fields.Boolean(
        compute='_compute_is_flash_sale', store=True,
    )

    @api.depends('flash_sale_id')
    def _compute_is_flash_sale(self):
        for o in self:
            o.is_flash_sale = bool(o.flash_sale_id)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.vendor_id and not order.commission_id:
                commission = self.env['uellow.vendor.commission'].create_from_order(order)
                if commission:
                    order.commission_id = commission
        return res
