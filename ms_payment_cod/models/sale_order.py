from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.price_total', 'order_line.price_subtotal')
    def _compute_amount_cod_fee(self):
        self.amount_cod_fee = 0.0
        for order in self.filtered('website_id'):
            cod_fee_product_id = self.env.ref('ms_payment_cod.product_product_cod')
            cod_fee_lines = order.order_line.filtered(lambda l: l.product_id.id == cod_fee_product_id.id)
            order.amount_cod_fee = sum(cod_fee_lines.mapped('price_total'))

    amount_cod_fee = fields.Monetary(
        string="COD Amount",
        compute='_compute_amount_cod_fee',
    )
    
    def _has_cod_fee_products(self):
        has_cod_fee_products = False
        cod_fee_product_id = self.env.ref('ms_payment_cod.product_product_cod')
        cod_line_ids = self.order_line.filtered(lambda l: l.product_id.id == cod_fee_product_id.id)
        if cod_line_ids:
            has_cod_fee_products = True
        return has_cod_fee_products

    def add_cod_fee(self):
        self = self.sudo()
        cod_fee_product_id = self.env.ref('ms_payment_cod.product_product_cod')
        cod_line_ids = self.order_line.filtered(lambda l: l.product_id.id == cod_fee_product_id.id)
        cod_line_ids.unlink()
        cod_fee_amount = self.get_cod_fee_amount()
        self.order_line.create({
            'order_id': self.id,
            'product_id': cod_fee_product_id.id,
            'name': cod_fee_product_id.display_name,
            'product_uom_qty': 1,
            'product_uom': cod_fee_product_id.uom_id.id,
            'price_unit': cod_fee_amount,
        })

    def get_cod_fee_amount(self):
        self = self.sudo()
        cod_fee_amount = 0.0
        provider_id = self.env.ref('ms_payment_cod.payment_provider_cod')
        amount_total = self.currency_id._convert(
            self.amount_total,
            self.env.company.currency_id,
            self.env.company,
            fields.Datetime.now(),
            round=False
        )
        rule_id = self.env['payment.provider.cod.rule'].search([
            ('provider_id', '=', provider_id.id),
            '|',
            ('min_amount', '=', 0),
            ('min_amount', '<=', amount_total),
            '|',
            ('max_amount', '=', 0),
            ('max_amount', '>=', amount_total),
        ], limit=1)
        if rule_id:
            if rule_id.pricing_based == 'fixed':
                cod_fee_amount = rule_id.fixed_amount
            else:
                cod_fee_amount = amount_total * rule_id.percentage_amount / 100
            cod_fee_amount = self.env.company.currency_id._convert(
                cod_fee_amount,
                self.currency_id,
                self.company_id,
                fields.Datetime.now(),
                round=False
            )
        return cod_fee_amount

    def get_cod_fee_amount_str(self):
        cod_fee_amount = self.get_cod_fee_amount()
        if self.company_id.currency_id.position == 'after':
            cod_fee_amount_str = f'{cod_fee_amount} {self.company_id.currency_id.symbol}'
        else:
            cod_fee_amount_str = f'{self.company_id.currency_id.symbol} {cod_fee_amount}'
        return cod_fee_amount_str
