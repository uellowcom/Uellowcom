from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    loyalty_points_earned = fields.Integer('Points Earned', default=0)
    loyalty_points_redeemed = fields.Integer('Points Redeemed', default=0)
    loyalty_discount = fields.Float('Loyalty Discount (KD)', default=0.0)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            partner = order.partner_id
            program = self.env['uellow.loyalty.program'].get_program()
            if not program.active:
                continue
            account = self.env['uellow.loyalty.account'].get_or_create(partner)
            # Earn points
            points = int(order.amount_total * program.points_per_kd)
            # First purchase bonus
            if account.total_earned == 0:
                points += program.points_first_purchase
            account.earn_points(points, reason=order.name, order_id=order.id)
            order.loyalty_points_earned = points
        return res
