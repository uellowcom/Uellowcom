from odoo import http
from odoo.http import request


class SupplierPortal(http.Controller):

    def _get_supplier(self):
        user = request.env.user
        return request.env['uellow.supplier.profile'].sudo().search([
            ('user_id', '=', user.id)], limit=1) or \
            request.env['uellow.supplier.profile'].sudo().search([
                ('partner_id', '=', user.partner_id.id)], limit=1)

    @http.route('/my/supplier', type='http', auth='user', website=True)
    def supplier_dashboard(self, **kw):
        supplier = self._get_supplier()
        if not supplier:
            return request.redirect('/my')
        orders = request.env['purchase.order'].sudo().search([
            ('partner_id', '=', supplier.partner_id.id),
            ('state', 'in', ('purchase', 'done')),
        ], limit=10, order='date_order desc')
        return request.render('uellow_supplier_portal.supplier_dashboard', {
            'supplier': supplier, 'orders': orders,
        })

    @http.route('/my/supplier/confirm/<int:order_id>', type='json', auth='user')
    def confirm_order(self, order_id, note=''):
        supplier = self._get_supplier()
        if not supplier:
            return {'error': 'No supplier profile'}
        order = request.env['purchase.order'].sudo().browse(order_id)
        if order.partner_id != supplier.partner_id:
            return {'error': 'Not authorized'}
        from odoo import fields as F
        order.write({
            'supplier_confirmed': True,
            'supplier_confirmed_at': F.Datetime.now(),
            'supplier_note': note,
        })
        return {'ok': True}

    @http.route('/my/supplier/tracking/<int:order_id>', type='json', auth='user')
    def update_tracking(self, order_id, tracking_number):
        supplier = self._get_supplier()
        if not supplier:
            return {'error': 'No supplier profile'}
        order = request.env['purchase.order'].sudo().browse(order_id)
        if order.partner_id != supplier.partner_id:
            return {'error': 'Not authorized'}
        order.tracking_number = tracking_number
        return {'ok': True}
