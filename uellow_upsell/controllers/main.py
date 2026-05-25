from odoo import http
from odoo.http import request


class UpsellController(http.Controller):

    @http.route('/upsell/recommendations', type='json', auth='public')
    def get_recommendations(self, product_id, rule_type='crosssell', limit=4):
        recs = request.env['uellow.upsell.rule'].sudo().get_recommendations(
            int(product_id), rule_type, limit)
        return {'products': recs}

    @http.route('/upsell/click', type='json', auth='public')
    def track_click(self, rule_id):
        rule = request.env['uellow.upsell.rule'].sudo().browse(int(rule_id))
        if rule.exists():
            rule.click_count += 1
        return {'ok': True}
