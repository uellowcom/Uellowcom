from odoo import http
from odoo.http import request


class ABTestController(http.Controller):

    @http.route('/ab/view/<int:test_id>', type='json', auth='public')
    def record_view(self, test_id, variant):
        test = request.env['uellow.ab.test'].sudo().browse(test_id)
        if test.exists() and test.state == 'running':
            if variant == 'a':
                test.a_views += 1
            else:
                test.b_views += 1
        return {'ok': True}

    @http.route('/ab/convert/<int:test_id>', type='json', auth='public')
    def record_conversion(self, test_id, variant, revenue=0.0):
        test = request.env['uellow.ab.test'].sudo().browse(test_id)
        if test.exists() and test.state == 'running':
            if variant == 'a':
                test.a_conversions += 1
                test.a_revenue += float(revenue)
            else:
                test.b_conversions += 1
                test.b_revenue += float(revenue)
        return {'ok': True}
