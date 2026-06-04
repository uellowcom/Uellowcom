# -*- coding: utf-8 -*-
"""
Vendor portal — promotion joins (/my/vendor/promotions)
=======================================================
Vendors see open + running campaigns with their dates, pick their OWN
products with a discount % each (validated against the campaign's
min/max), and submit. The request shows live per-line status
(pending / approved / rejected) as the admin moderates it.
"""
from odoo import http
from odoo.http import request


class VendorPromotionsPortal(http.Controller):

    def _get_vendor(self):
        if request.env.user._is_public():
            return False
        Vendor = request.env['uellow.vendor'].sudo()
        vendor = Vendor.search([('user_id', '=', request.env.user.id)], limit=1)
        if not vendor:
            vendor = Vendor.search(
                [('partner_id', '=', request.env.user.partner_id.id)], limit=1)
        return vendor

    @http.route('/my/vendor/promotions', type='http', auth='user', website=True)
    def vendor_promotions(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        Promo = request.env['mobile.app.promotion'].sudo()
        promos = Promo.search([
            ('state', 'in', ('open', 'running')),
            ('vendor_joinable', '=', True),
            ('active', '=', True),
        ], order='date_from')
        my_lines = request.env['mobile.promotion.line'].sudo().search([
            ('vendor_id', '=', vendor.id)], order='create_date desc')
        my_products = request.env['product.template'].sudo().search([
            ('vendor_id', '=', vendor.id), ('active', '=', True),
        ], order='name') if 'vendor_id' in \
            request.env['product.template']._fields else \
            request.env['product.template'].sudo().browse([])
        return request.render(
            'uellow_mobile_manager.portal_vendor_promotions', {
                'vendor': vendor,
                'promos': promos,
                'my_lines': my_lines,
                'my_products': my_products,
                'page_name': 'vendor_promotions',
            })

    @http.route('/my/vendor/promotions/join', type='http', auth='user',
                methods=['POST'], website=True, csrf=True)
    def vendor_promotion_join(self, **kw):
        vendor = self._get_vendor()
        if not vendor:
            return request.redirect('/my')
        Promo = request.env['mobile.app.promotion'].sudo()
        promo = Promo.browse(int(kw.get('promotion_id') or 0))
        if not promo.exists() or promo.state not in ('open', 'running') \
                or not promo.vendor_joinable:
            return request.redirect('/my/vendor/promotions')
        Line = request.env['mobile.promotion.line'].sudo()
        # form posts product_ids[] + matching discount_<product_id> inputs
        ids = request.httprequest.form.getlist('product_ids')
        for pid_raw in ids:
            try:
                pid = int(pid_raw)
                pct = float(kw.get('discount_%s' % pid) or 0)
            except Exception:
                continue
            pct = max(promo.min_discount_pct,
                      min(promo.max_discount_pct, pct))
            # vendor may only submit their own products
            tmpl = request.env['product.template'].sudo().browse(pid)
            if not tmpl.exists():
                continue
            if 'vendor_id' in tmpl._fields and \
                    tmpl.vendor_id.id != vendor.id:
                continue
            if Line.search_count([('promotion_id', '=', promo.id),
                                  ('product_tmpl_id', '=', pid)]):
                continue
            Line.create({
                'promotion_id': promo.id,
                'product_tmpl_id': pid,
                'vendor_id': vendor.id,
                'discount_pct': pct,
                'note': (kw.get('note') or '').strip()[:200],
                'state': 'pending',
            })
        return request.redirect('/my/vendor/promotions')
