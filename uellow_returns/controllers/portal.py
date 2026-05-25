from odoo import http
from odoo.http import request


class ReturnPortal(http.Controller):

    @http.route('/my/returns', type='http', auth='user', website=True)
    def my_returns(self, **kw):
        partner = request.env.user.partner_id
        returns = request.env['uellow.return.request'].sudo().search([
            ('partner_id', '=', partner.id)
        ], order='id desc', limit=20)
        return request.render('uellow_returns.portal_returns', {
            'returns': returns,
        })

    @http.route('/my/returns/new', type='json', auth='user')
    def new_return(self, order_id, order_line_id, reason, description=''):
        partner = request.env.user.partner_id
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if order.partner_id != partner:
            return {'error': 'Not authorized'}
        ret = request.env['uellow.return.request'].sudo().create({
            'order_id': int(order_id),
            'order_line_id': int(order_line_id),
            'reason': reason,
            'description': description,
        })
        return {'ok': True, 'return_id': ret.id, 'state': ret.state}
