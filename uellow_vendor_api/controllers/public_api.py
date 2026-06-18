# -*- coding: utf-8 -*-
"""Vendor Open API — external REST surface authenticated by API key.

A vendor's own systems (ERP / store) call these with header
  X-API-Key: uk_live_xxxxxxxx
Read scope → GET endpoints; write scope → stock updates."""
import functools
from xml.sax.saxutils import escape

from odoo import http
from odoo.http import request

from ._common import safe_endpoint, get_payload, ok, fail


def _api_key():
    # header first; fall back to ?key= so URL-fetch consumers (Google Merchant,
    # Meta catalog) can authenticate a plain feed URL.
    return (request.httprequest.headers.get('X-API-Key')
            or request.httprequest.headers.get('x-api-key')
            or request.httprequest.args.get('key') or '').strip()


def _auth():
    """Return (vendor, key) or (None, None)."""
    return request.env['vendor.api.key'].sudo().authenticate(_api_key())


def require_api_key(scope=None):
    """Decorator: resolve the API key, stash (vendor, key) on the request."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapped(self, *args, **kwargs):
            vendor, key = _auth()
            if not vendor:
                return fail('API_KEY_INVALID', 'Missing or invalid X-API-Key', 401)
            if not vendor.cap('api'):
                return fail('FORBIDDEN', 'API access disabled for this account', 403)
            if scope == 'write' and key.scope != 'write':
                return fail('SCOPE', 'This key is read-only', 403)
            request.uellow_api_vendor = vendor
            request.uellow_api_key = key
            return fn(self, *args, **kwargs)
        return wrapped
    return deco


class VendorPublicApiController(http.Controller):

    @http.route('/api/public/v1/ping', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_api_key()
    def ping(self, **kw):
        v = request.uellow_api_vendor
        return ok({'vendor_id': v.id, 'vendor': v.display_name,
                   'scope': request.uellow_api_key.scope, 'status': 'ok'})

    @http.route('/api/public/v1/products', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_api_key()
    def products(self, **kw):
        v = request.uellow_api_vendor
        prods = request.env['product.template'].sudo().search(
            [('vendor_id', '=', v.id)], limit=500)
        out = [{
            'id': t.id, 'name': t.name, 'sku': t.default_code or '',
            'barcode': t.barcode or '', 'price': t.list_price,
            'cost': t.standard_price, 'qty': t.qty_available,
            'published': t.is_published,
            'approval': t.vendor_approval_state,
        } for t in prods]
        return ok(out, meta={'count': len(out)})

    @http.route('/api/public/v1/orders', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_api_key()
    def orders(self, **kw):
        v = request.uellow_api_vendor
        p = get_payload()
        domain = [('vendor_id', '=', v.id)]
        if p.get('state'):
            domain.append(('state', '=', p['state']))
        orders = request.env['sale.order'].sudo().search(
            domain, limit=200, order='date_order desc')
        out = [{
            'id': o.id, 'name': o.name, 'state': o.state,
            'amount_total': o.amount_total, 'currency': o.currency_id.name,
            'date': o.date_order,
            'lines': [{'product_id': l.product_id.id, 'name': l.name,
                       'qty': l.product_uom_qty, 'price': l.price_unit}
                      for l in o.order_line if l.product_id.product_tmpl_id.vendor_id.id == v.id],
        } for o in orders]
        return ok(out, meta={'count': len(out)})

    @http.route('/api/public/v1/products/<int:pid>/stock', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_api_key(scope='write')
    def set_stock(self, pid, **kw):
        v = request.uellow_api_vendor
        if not v.cap('update_stock'):
            return fail('FORBIDDEN', 'Stock updates disabled for this account', 403,
                        capability='update_stock')
        t = request.env['product.template'].sudo().browse(pid)
        if not t.exists() or t.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Product not found', 404)
        try:
            qty = float(get_payload().get('qty'))
        except (TypeError, ValueError):
            return fail('BAD_QTY', 'numeric qty required')
        product = t.product_variant_id
        loc = request.env['stock.location'].sudo().search(
            [('usage', '=', 'internal')], limit=1)
        if not product or not loc:
            return fail('NO_LOCATION', 'No stock location/variant', 500)
        cur = product.with_context(location=loc.id).qty_available
        delta = qty - cur
        if delta:
            request.env['stock.quant'].sudo().with_context(inventory_mode=True)._update_available_quantity(
                product, loc, delta)
        return ok({'id': pid, 'qty': qty})

    # ── Social catalog feed (Google Merchant / Meta) ─────────────
    def _feed_products(self, v):
        return request.env['product.template'].sudo().search([
            ('vendor_id', '=', v.id), ('is_published', '=', True),
            ('sale_ok', '=', True),
        ], limit=2000)

    @http.route('/api/public/v1/feed.xml', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_api_key()
    def feed_xml(self, **kw):
        v = request.uellow_api_vendor
        base = request.httprequest.host_url.rstrip('/')
        cur = (v.currency_id.name if v.currency_id else 'KWD')
        items = []
        for t in self._feed_products(v):
            desc = t.website_description or t.description_sale or t.name or ''
            img = '%s/web/image/product.template/%s/image_1024' % (base, t.id)
            link = base + (t.website_url or '/shop')
            avail = 'in stock' if t.qty_available > 0 else 'out of stock'
            brand = t.brand_id.name if 'brand_id' in t._fields and t.brand_id else 'Uellow'
            items.append(
                '<item>'
                '<g:id>%s</g:id><g:title>%s</g:title><g:description>%s</g:description>'
                '<g:link>%s</g:link><g:image_link>%s</g:image_link>'
                '<g:availability>%s</g:availability><g:price>%.3f %s</g:price>'
                '<g:brand>%s</g:brand><g:condition>new</g:condition>'
                '<g:mpn>%s</g:mpn>'
                '</item>' % (
                    t.id, escape(t.name or ''), escape(desc[:4000]),
                    escape(link), escape(img), avail, t.list_price, cur,
                    escape(brand), escape(t.default_code or str(t.id))))
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">'
            '<channel><title>%s — Uellow</title><link>%s</link>'
            '<description>Product feed</description>%s</channel></rss>'
            % (escape(v.display_name or 'Vendor'), escape(base), ''.join(items)))
        return request.make_response(xml.encode('utf-8'), headers=[
            ('Content-Type', 'application/xml; charset=utf-8')])

    @http.route('/api/public/v1/feed.csv', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_api_key()
    def feed_csv(self, **kw):
        import csv
        import io
        v = request.uellow_api_vendor
        base = request.httprequest.host_url.rstrip('/')
        cur = (v.currency_id.name if v.currency_id else 'KWD')
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(['id', 'title', 'description', 'link', 'image_link',
                    'availability', 'price', 'brand', 'condition', 'mpn'])
        for t in self._feed_products(v):
            desc = (t.website_description or t.description_sale or t.name or '')
            img = '%s/web/image/product.template/%s/image_1024' % (base, t.id)
            link = base + (t.website_url or '/shop')
            avail = 'in stock' if t.qty_available > 0 else 'out of stock'
            brand = t.brand_id.name if 'brand_id' in t._fields and t.brand_id else 'Uellow'
            w.writerow([t.id, t.name or '', desc[:4000], link, img, avail,
                        '%.3f %s' % (t.list_price, cur), brand, 'new',
                        t.default_code or str(t.id)])
        return request.make_response(buf.getvalue().encode('utf-8'), headers=[
            ('Content-Type', 'text/csv; charset=utf-8'),
            ('Content-Disposition', 'attachment; filename="catalog.csv"')])
