from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    supplier_confirmed = fields.Boolean('Supplier Confirmed', default=False)
    supplier_confirmed_at = fields.Datetime('Confirmed At')
    tracking_number = fields.Char('Tracking Number')
    is_dropship = fields.Boolean('Dropship Order', default=False)
    supplier_note = fields.Text('Supplier Note')
