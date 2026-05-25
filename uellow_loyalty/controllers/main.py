from odoo import http
from odoo.http import request


class LoyaltyPortal(http.Controller):

    @http.route('/my/loyalty', type='http', auth='user', website=True)
    def loyalty_page(self, **kw):
        partner = request.env.user.partner_id
        account = request.env['uellow.loyalty.account'].sudo().search([
            ('partner_id', '=', partner.id)
        ], limit=1)
        if not account:
            account = request.env['uellow.loyalty.account'].sudo().create({
                'partner_id': partner.id
            })
        program = request.env['uellow.loyalty.program'].sudo().get_program()
        transactions = request.env['uellow.loyalty.transaction'].sudo().search([
            ('account_id', '=', account.id)
        ], limit=30, order='id desc')
        return request.render('uellow_loyalty.portal_loyalty', {
            'account': account,
            'program': program,
            'transactions': transactions,
        })

    @http.route('/loyalty/redeem', type='json', auth='user')
    def redeem_points(self, points, order_id=False):
        partner = request.env.user.partner_id
        account = request.env['uellow.loyalty.account'].sudo().search([
            ('partner_id', '=', partner.id)], limit=1)
        if not account:
            return {'error': 'No loyalty account'}
        try:
            discount = account.redeem_points(int(points), order_id=order_id)
            return {'ok': True, 'discount': discount, 'balance': account.balance}
        except Exception as e:
            return {'error': str(e)}
