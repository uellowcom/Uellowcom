# -*- coding: utf-8 -*-
"""
Vendor self-service shipping methods — /my/vendor/shipping
==========================================================
When `uellow_delivery.vendor_carriers_enabled` is on, vendors manage
their OWN delivery.carrier records (vendor_id = their vendor): create,
edit price/labels, enable/disable. At checkout these methods are only
offered when the WHOLE cart belongs to that vendor.
"""
from odoo import http, _
from odoo.http import request


def _vendor_carriers_enabled():
    return (request.env['ir.config_parameter'].sudo().get_param(
        'uellow_delivery.vendor_carriers_enabled') or '') in ('1', 'True', 'true')


class VendorShippingPortal(http.Controller):

    def _get_vendor(self):
        if request.env.user._is_public():
            return False
        Vendor = request.env['uellow.vendor'].sudo()
        vendor = Vendor.search([('user_id', '=', request.env.user.id)], limit=1)
        if not vendor:
            vendor = Vendor.search(
                [('partner_id', '=', request.env.user.partner_id.id)], limit=1)
        return vendor

    @http.route('/my/vendor/shipping', type='http', auth='user', website=True)
    def vendor_shipping(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        carriers = request.env['delivery.carrier'].sudo().with_context(
            active_test=False).search([('vendor_id', '=', vendor.id)])
        return request.render(
            'delivery_carrier_portal.portal_vendor_shipping', {
                'vendor': vendor,
                'carriers': carriers,
                'enabled': _vendor_carriers_enabled(),
                'page_name': 'vendor_shipping',
            })

    @http.route('/my/vendor/shipping/save', type='http', auth='user',
                methods=['POST'], website=True, csrf=True)
    def vendor_shipping_save(self, **kw):
        vendor = self._get_vendor()
        if not vendor or not _vendor_carriers_enabled():
            return request.redirect('/my/vendor/shipping')
        Carrier = request.env['delivery.carrier'].sudo()
        cid = int(kw.get('carrier_id') or 0)
        try:
            price = float(kw.get('price') or 0)
        except Exception:
            price = 0.0
        vals = {
            'name': (kw.get('name') or '').strip() or _('My delivery'),
            'public_label_en': (kw.get('label_en') or '').strip(),
            'public_label_ar': (kw.get('label_ar') or '').strip(),
            'public_desc_en': (kw.get('desc_en') or '').strip(),
            'public_desc_ar': (kw.get('desc_ar') or '').strip(),
            'fixed_price': price,
        }
        if cid:
            c = Carrier.with_context(active_test=False).browse(cid)
            if c.exists() and c.vendor_id.id == vendor.id:
                c.write(vals)
        else:
            # The carrier needs a delivery product — reuse/create one.
            prod = request.env['product.product'].sudo().search(
                [('default_code', '=', 'VENDOR_SHIP_%s' % vendor.id)], limit=1)
            if not prod:
                prod = request.env['product.product'].sudo().create({
                    'name': '%s Delivery' % (vendor.store_name_en or 'Vendor'),
                    'default_code': 'VENDOR_SHIP_%s' % vendor.id,
                    'type': 'service',
                    'sale_ok': False, 'purchase_ok': False,
                    'list_price': 0.0,
                })
            vals.update({
                'delivery_type': 'fixed',
                'product_id': prod.id,
                'vendor_id': vendor.id,
                'is_published': True,
                'website_published': True,
                'uellow_channel': 'both',
            })
            Carrier.create(vals)
        return request.redirect('/my/vendor/shipping')

    @http.route('/my/vendor/shipping/toggle/<int:carrier_id>', type='http',
                auth='user', methods=['POST'], website=True, csrf=True)
    def vendor_shipping_toggle(self, carrier_id, **kw):
        vendor = self._get_vendor()
        if vendor:
            c = request.env['delivery.carrier'].sudo().with_context(
                active_test=False).browse(carrier_id)
            if c.exists() and c.vendor_id.id == vendor.id:
                c.active = not c.active
        return request.redirect('/my/vendor/shipping')
