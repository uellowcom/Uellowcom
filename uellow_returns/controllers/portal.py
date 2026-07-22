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
        if not order.exists() or order.partner_id.commercial_partner_id != partner.commercial_partner_id:
            return {'error': 'Not authorized'}
        # IDOR guard: the return line MUST belong to THIS order — otherwise a
        # customer could attach another customer's (expensive) order line to
        # their own cheap auto-approved return and be refunded that line's value.
        line = request.env['sale.order.line'].sudo().browse(int(order_line_id))
        if not line.exists() or line.order_id.id != order.id:
            return {'error': 'Invalid order line'}
        ret = request.env['uellow.return.request'].sudo().create({
            'order_id': order.id,
            'order_line_id': line.id,
            'reason': reason,
            'description': description,
        })
        return {'ok': True, 'return_id': ret.id, 'state': ret.state}
