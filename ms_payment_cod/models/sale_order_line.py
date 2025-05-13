from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _show_in_cart(self):
        res = super()._show_in_cart()
        cod_fee_product_id = self.env.ref('ms_payment_cod.product_product_cod')
        if self.product_id.id == cod_fee_product_id.id:
            res = False
        return res
