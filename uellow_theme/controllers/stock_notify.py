# -*- coding: utf-8 -*-
import re
from odoo import http
from odoo.http import request


class UellowStockNotifyController(http.Controller):
    """Storefront 'notify me when back in stock' endpoint."""

    @http.route('/shop/notify-stock', type='json', auth='public',
                website=True, csrf=False)
    def notify_stock(self, product_id=None, variant_id=None, contact=None, **kw):
        contact = (contact or '').strip()
        digits = re.sub(r'\D', '', contact)
        looks_email = '@' in contact and '.' in contact.rsplit('@', 1)[-1]
        if not contact or not (looks_email or len(digits) >= 7):
            return {'ok': False, 'error': 'invalid'}
        try:
            tid = int(product_id)
        except Exception:
            return {'ok': False, 'error': 'noproduct'}
        env = request.env
        tmpl = env['product.template'].sudo().browse(tid)
        if not tmpl.exists():
            return {'ok': False, 'error': 'noproduct'}
        Notify = env['uellow.stock.notify'].sudo()
        dup = Notify.search([('product_tmpl_id', '=', tmpl.id),
                             ('contact', '=', contact),
                             ('state', '=', 'new')], limit=1)
        if dup:
            return {'ok': True, 'already': True}
        partner = False
        if not env.user._is_public():
            partner = env.user.partner_id
        Notify.create({
            'product_tmpl_id': tmpl.id,
            'product_id': int(variant_id) if variant_id else False,
            'contact': contact,
            'partner_id': partner.id if partner else False,
            'website_id': request.website.id if getattr(request, 'website', None) else False,
            'lang': env.context.get('lang') or '',
        })
        return {'ok': True}
