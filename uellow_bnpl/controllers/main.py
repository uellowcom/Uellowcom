from odoo import http
from odoo.http import request


class BNPLController(http.Controller):

    @http.route('/bnpl/plans', type='json', auth='public')
    def get_plans(self, order_amount=0):
        plans = request.env['uellow.bnpl.plan'].sudo().search([
            ('active', '=', True),
            ('min_order_amount', '<=', float(order_amount)),
            ('max_order_amount', '>=', float(order_amount)),
        ])
        return plans.read(['id', 'name', 'installments', 'interval_days',
                           'admin_fee_pct', 'min_order_amount'])

    @http.route('/bnpl/apply', type='json', auth='user')
    def apply(self, order_id, plan_id):
        order = request.env['sale.order'].sudo().browse(int(order_id))
        plan = request.env['uellow.bnpl.plan'].sudo().browse(int(plan_id))
        if not order.exists() or not plan.exists():
            return {'error': 'Not found'}
        admin_fee = order.amount_total * plan.admin_fee_pct / 100
        app = request.env['uellow.bnpl.application'].sudo().create({
            'order_id': order.id,
            'plan_id': plan.id,
            'total_amount': order.amount_total + admin_fee,
            'admin_fee': admin_fee,
        })
        if not plan.requires_approval:
            app.action_approve()
        order.write({'bnpl_application_id': app.id, 'is_bnpl': True})
        return {'ok': True, 'application_id': app.id, 'state': app.state}
