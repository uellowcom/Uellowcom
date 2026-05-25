from odoo import http
from odoo.http import request


class PersonalizationController(http.Controller):

    @http.route('/personalized/products', type='json', auth='public')
    def get_personalized(self, limit=8):
        partner_id = False
        user = request.env.user
        if user and not user._is_public():
            partner_id = user.partner_id.id
        return request.env['uellow.personalization.rule'].sudo().get_for_visitor(
            partner_id=partner_id, limit=limit)

    @http.route('/personalized/track', type='json', auth='public')
    def track_view(self, product_id):
        user = request.env.user
        if user and not user._is_public():
            behavior = request.env['uellow.customer.behavior'].sudo().search([
                ('partner_id', '=', user.partner_id.id)], limit=1)
            if not behavior:
                behavior = request.env['uellow.customer.behavior'].sudo().create(
                    {'partner_id': user.partner_id.id})
            behavior.record_view(int(product_id))
        return {'ok': True}
