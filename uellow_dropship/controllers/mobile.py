# -*- coding: utf-8 -*-
"""Mobile-app API for the dropship catalog.

Matches the app's /api/mobile/v2 contract EXACTLY (type='http', GET, JSON
envelope {success, data}) so the Flutter "Dropship Mode" screens are near-copies
of the standard listing screens and can be called with UellowApi.getRaw():

  GET /api/mobile/v2/dropship/feed   -> {data: {items:[card], has_more, brand, total}}
  GET /api/mobile/v2/dropship/open   -> {data: {product_id, slug}}  (materializes)

Card JSON matches UellowProductCard.fromJson (name{en,ar}, price{amount,currency,
symbol,digits}, compare_price, discount_pct, image, has_video, badges, ...).
Tapping a card calls /open, which lazily materializes a real product and returns
its product id so the app opens the STANDARD product screen (no difference).
"""
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _ok(data):
    return request.make_response(
        json.dumps({'success': True, 'data': data}, default=str, ensure_ascii=False),
        headers=[('Content-Type', 'application/json'),
                 ('Cache-Control', 'no-store, no-cache, must-revalidate'),
                 ('Access-Control-Allow-Origin', '*')])


class DropshipMobile(http.Controller):

    def _enabled(self):
        v = request.env['ir.config_parameter'].sudo().get_param('uellow_dropship.enabled')
        return v in ('True', '1', 'true')

    def _money(self, amount, currency):
        return {
            'amount': round(amount or 0.0, 3),
            'currency': currency.name if currency else 'KWD',
            'symbol': (currency.symbol if currency else 'KD') or 'KD',
            'digits': 3,
        }

    def _card(self, rec, currency, show_video):
        # serve the image through the Uellow image proxy (absolute URL for the app),
        # never the raw provider CDN link
        base = request.httprequest.host_url.rstrip('/').replace('http://', 'https://', 1)
        image = ('%s/dropship/img/%s' % (base, rec.id)) if rec.image_url else ''
        return {
            'id': rec.id,                       # dropship.product id (see /open)
            'name': {'en': rec.title_en or '', 'ar': rec.title_ar or rec.title_en or ''},
            'slug': '',
            'image': image,
            'price': self._money(rec.sale_price, currency),
            'compare_price': self._money(rec.original_price, currency)
                if (rec.original_price and rec.original_price > rec.sale_price) else None,
            'discount_pct': int(rec.discount_percent or 0),
            'in_stock': True,
            'is_published': True,
            'badges': (['deal'] if rec.is_deal else []),
            'has_video': bool(rec.video_url) and show_video,
            'is_dropship': True,               # lets the app route tap -> /open
        }

    @http.route('/api/mobile/v2/dropship/feed', type='http', auth='public',
                methods=['GET'], csrf=False)
    def feed(self, page=1, per_page=None, category=None, search=None,
             deals_only=None, **kw):
        if not self._enabled():
            return _ok({'items': [], 'has_more': False, 'total': 0, 'enabled': False})
        ICP = request.env['ir.config_parameter'].sudo()
        page = max(int(page or 1), 1)
        per_page = int(per_page or ICP.get_param('uellow_dropship.products_per_page', 40) or 40)
        show_video = ICP.get_param('uellow_dropship.show_videos') in ('True', '1', 'true')

        domain = []
        if category:
            domain.append(('category', '=', str(category)))
        if search:
            domain += ['|', ('title_en', 'ilike', search), ('title_ar', 'ilike', search)]
        if deals_only in ('1', 'true', 'True', True):
            domain.append(('is_deal', '=', True))
        min_price = float(ICP.get_param('uellow_dropship.min_price', 0.0) or 0.0)
        if min_price:
            domain.append(('sale_price', '>=', min_price))

        Product = request.env['dropship.product'].sudo()
        currency = request.env.company.currency_id
        total = Product.search_count(domain)
        recs = Product.search(domain, order='is_deal desc, discount_percent desc, id desc',
                              limit=per_page, offset=(page - 1) * per_page)
        return _ok({
            'items': [self._card(r, currency, show_video) for r in recs],
            'has_more': (page * per_page) < total,
            'total': total,
            'brand': ICP.get_param('uellow_dropship.brand_name', 'Uellow World'),
            'enabled': True,
        })

    @http.route('/api/mobile/v2/dropship/open', type='http', auth='public',
                methods=['GET'], csrf=False)
    def open(self, id=None, **kw):
        """Materialize a listing and return its real product id for the app."""
        if not self._enabled() or not id:
            return _ok({'product_id': 0})
        rec = request.env['dropship.product'].sudo().browse(int(id)).exists()
        if not rec:
            return _ok({'product_id': 0})
        tmpl = rec._materialize()
        if not tmpl.website_published:
            tmpl.sudo().website_published = True
        request.env.cr.commit()
        try:
            slug = request.env['ir.http']._slug(tmpl)
        except Exception:  # noqa: BLE001
            slug = str(tmpl.id)
        return _ok({'product_id': tmpl.id, 'slug': slug})

    @http.route('/api/mobile/v2/dropship/categories', type='http', auth='public',
                methods=['GET'], csrf=False)
    def categories(self, limit=None, **kw):
        """Category tiles for the app World entry — mirrors the web _world_categories:
        bilingual label + emoji icon + product count, from the module-only
        dropship.category records. `code` is the stable, lang-neutral filter key the
        app passes back to /feed?category=<code>.
        """
        if not self._enabled():
            return _ok({'items': [], 'enabled': False})
        Product = request.env['dropship.product'].sudo()
        groups = Product.read_group([('category_name', '!=', False)],
                                    ['category_name'], ['category_name'])
        counts = {g['category_name']: (g.get('__count')
                                       or g.get('category_name_count') or 0)
                  for g in groups if g.get('category_name')}
        ar_lang = request.env['res.lang'].sudo().search(
            [('code', 'like', 'ar%'), ('active', '=', True)], limit=1)
        ar_code = ar_lang.code if ar_lang else 'ar_001'
        items = []
        for dc in request.env['dropship.category'].sudo().search([]):
            cnt = counts.get(dc.code)
            if not cnt:  # only categories that actually have products
                continue
            label_en = dc.with_context(lang='en_US').name or dc.code
            label_ar = dc.with_context(lang=ar_code).name or label_en
            items.append({
                'code': dc.code,                        # filter key for /feed
                'label': {'en': label_en, 'ar': label_ar},
                'icon': dc.icon or '🏷️',
                'count': cnt,
            })
        items.sort(key=lambda x: x['count'], reverse=True)
        if limit:
            items = items[:int(limit)]
        return _ok({'items': items, 'enabled': True})
