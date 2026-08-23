# -*- coding: utf-8 -*-
import json
import logging
from odoo import http
from odoo.http import request
from .main import (_lines_from_ids, _unit_item, country_code,
                    _augment_tiers, _lb_leaderboard, _lb_savings,
                    _lb_badges, _lb_abandoned, _app_partner)

_logger = logging.getLogger(__name__)


def _json(data, status=200):
    return request.make_json_response(data, status=status)


class LammaMobile(http.Controller):
    """Mobile API for لمّة يلو (consumed by the Flutter app). Public, read-only,
    stateless — the app holds the bundle and asks the server to price it."""

    @http.route('/api/mobile/v2/lamma/config', type='http', auth='public',
                methods=['GET'], csrf=False, cors='*')
    def config(self, **kw):
        cfg = request.env['uellow.lamma.config'].sudo().get_config()
        cur = request.env.company.currency_id
        return _json({
            'enabled': bool(cfg.active and cfg.enable_all_products
                            and cfg._country_enabled(kw.get('country') or country_code())),
            'label': cfg.brand_label,
            'badge': cfg.badge_text,
            'enable_all_products': cfg.enable_all_products,
            'replace_add_to_cart': cfg.replace_add_to_cart,
            'auto_start': cfg.auto_start,
            'min_items': cfg.min_items,
            'discount_mode': cfg.discount_mode,
            'max_discount_pct': cfg.max_discount_pct,
            'min_margin_pct': cfg.min_margin_pct,
            'free_shipping_items': cfg.free_shipping_items,
            'tiers': [{'min_qty': t.min_qty, 'min_amount': t.min_amount,
                       'discount_pct': t.discount_pct} for t in cfg.tier_ids],
            'installment': {
                'enabled': cfg.installment_enabled,
                'extra_margin_pct': cfg.installment_extra_margin,
                'provider': cfg.installment_provider,
                'max_months': cfg.installment_max_months,
                'min_amount': cfg.installment_min_amount,
            },
            'currency': cur.symbol or cur.name or 'KD',
        })

    @http.route('/api/mobile/v2/lamma/cart-items', type='http', auth='public',
                methods=['GET'], csrf=False, cors='*')
    def cart_items(self, **kw):
        """Template + variant ids of the products in the CURRENT cart — the app
        uses this to seed / auto-start the Lamma from what's already in the cart."""
        try:
            from odoo.addons.uellow_mobile_manager.controllers.api_v2.cart import _get_or_create_order
            order = _get_or_create_order(create=False)
            out = []
            if order:
                for l in order.order_line:
                    if (l.display_type or getattr(l, 'is_reward_line', False)
                            or not l.product_id):
                        continue
                    t = l.product_id.product_tmpl_id
                    if not t.sale_ok:
                        continue
                    out.append({'product_id': t.id, 'variant_id': l.product_id.id})
            return _json({'items': out})
        except Exception:
            return _json({'items': []})

    @http.route('/api/mobile/v2/lamma/quote', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def quote(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        try:
            payload = json.loads(request.httprequest.get_data() or b'{}')
        except Exception:
            payload = {}
        try:
            ids = payload.get('product_ids') or []
            vmap = payload.get('variants') or {}
            ltype = payload.get('type') or 'normal'
            quantities = payload.get('quantities') or {}
            cfg = request.env['uellow.lamma.config'].sudo().get_config()
            units, lines = _lines_from_ids(ids, vmap, quantities)  # de-dups + filters server-side
            q = cfg.compute_lamma(lines, ltype)
            cur = request.env.company.currency_id
            q['currency'] = cur.symbol or cur.name or 'KD'
            q['items'] = [_unit_item(u) for u in units]
            _augment_tiers(cfg, q, q.get('n') or len(units), q.get('subtotal') or 0.0)
            return _json(q)
        except Exception as e:
            _logger.exception('lamma quote failed: %s', e)
            return _json({'n': 0, 'items': [], 'saved': 0.0, 'pays': 0.0,
                          'subtotal': 0.0, 'eligible': False}, status=200)

    @http.route('/api/mobile/v2/lamma/hub', type='http', auth='public',
                methods=['GET'], csrf=False, cors='*')
    def hub(self, **kw):
        try:
            pid = _app_partner()
            data = {'leaderboard': _lb_leaderboard(int(kw.get('days') or 7))}
            if pid:
                data['savings'] = _lb_savings(30, pid=pid, sid='')
                data['badges'] = _lb_badges(pid=pid, sid='')
                data['abandoned'] = _lb_abandoned(pid=pid, sid='')
                data['authed'] = True
            else:
                data['authed'] = False
            return _json(data)
        except Exception as e:
            _logger.exception('lamma hub failed: %s', e)
            return _json({'leaderboard': {'rows': [], 'community_total': 0.0}, 'authed': False})

    @http.route('/api/mobile/v2/lamma/leaderboard', type='http', auth='public',
                methods=['GET'], csrf=False, cors='*')
    def leaderboard(self, **kw):
        try:
            return _json(_lb_leaderboard(int(kw.get('days') or 1)))
        except Exception as e:
            _logger.exception('lamma leaderboard failed: %s', e)
            return _json({'rows': [], 'community_total': 0.0, 'currency': 'KD'})

    @http.route('/api/mobile/v2/lamma/variants', type='http', auth='public',
                methods=['GET'], csrf=False, cors='*')
    def variants(self, **kw):
        """Selectable colour/variants for a product — the app shows a picker
        when there is more than one so the customer bundles a specific colour."""
        tid = int(kw.get('product_id') or 0)
        t = request.env['product.template'].sudo().browse(tid).exists()
        cur = request.env.company.currency_id
        if not t:
            return _json({'multi': False, 'variants': []})
        out = []
        for v in t.product_variant_ids.filtered(lambda x: x.active):
            attrs = v.product_template_attribute_value_ids
            label = ', '.join(a.name for a in attrs) or (v.display_name or t.name or '')
            color = ''
            for a in attrs:
                hc = a.product_attribute_value_id.html_color
                if hc:
                    color = hc
                    break
            out.append({
                'variant_id': v.id, 'label': label, 'color': color,
                'price': round(v.list_price or t.list_price or 0.0, 3),
                'image': '/web/image/product.product/%s/image_256' % v.id,
            })
        return _json({'multi': len(out) > 1, 'variants': out,
                      'currency': cur.symbol or cur.name or 'KD'})

    @http.route('/api/mobile/v2/lamma/checkout', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def app_checkout(self, **kw):
        """Add the Lamma products to the app cart with the server-recomputed,
        margin-protected discount. Reuses uellow_mobile_manager's order
        resolution (partner/guest cart) so it integrates with the app cart.
        The discount is re-derived here + via _recompute_lamma — never trusted
        from the client."""
        if request.httprequest.method == 'OPTIONS':
            return _json({'ok': True})
        try:
            payload = json.loads(request.httprequest.get_data() or b'{}')
        except Exception:
            payload = {}
        ids = payload.get('product_ids') or []
        vmap = payload.get('variants') or {}
        ltype = payload.get('type') or 'normal'
        cfg = request.env['uellow.lamma.config'].sudo().get_config()
        units, _lines = _lines_from_ids(ids, vmap)
        if len(units) < max(1, cfg.min_items):
            _logger.info('lamma app checkout need_more: sent=%s resolved=%s min=%s',
                         ids, len(units), cfg.min_items)
            return _json({'ok': False, 'error': 'need_more', 'min_items': cfg.min_items}, status=400)
        # Gate on the VISITOR's country (not the company's) — same as the web
        # path and the /config endpoint; otherwise app gating is a no-op.
        visitor_cc = payload.get('country') or country_code()
        if not cfg._country_enabled(visitor_cc):
            return _json({'ok': False, 'error': 'disabled'}, status=403)
        try:
            from odoo.addons.uellow_mobile_manager.controllers.api_v2.cart import _get_or_create_order
            q = cfg.compute_lamma(_lines, ltype)
            order = _get_or_create_order(create=True)
            if not order:
                return _json({'ok': False, 'error': 'no_order'}, status=500)
            Line = request.env['sale.order.line'].sudo()
            cfg._strip_lamma_rewards(order, cfg._coupon_program())  # clean any legacy coupon
            for u in units:
                variant = u['variant']
                line = order.order_line.filtered(
                    lambda l: l.product_id == variant and not getattr(l, 'is_reward_line', False)
                    and not l.display_type)[:1]
                if not line:
                    line = Line.create({'order_id': order.id, 'product_id': variant.id,
                                        'product_uom_qty': 1})
                line.write({'is_lamma': True, 'lamma_type': ltype})
            # Margin-safe discount applied PER LINE (not an order coupon) — it can
            # never survive product removal, go negative, or be replayed elsewhere.
            order._recompute_lamma()
            request.env['uellow.lamma.activity'].sudo().log('checkout', None, {
                'type': ltype, 'n': q['n'], 'subtotal': q['subtotal'],
                'saved': q['saved'], '_country': visitor_cc or ''}, 'app')
            # Return the cart token of the order we populated so the app reads
            # back the SAME cart (otherwise it shows empty right after checkout).
            return _json({'ok': True, 'order_id': order.id,
                          'cart_token': order.mobile_cart_token or ''})
        except Exception as e:
            _logger.exception('lamma app checkout failed: %s', e)
            return _json({'ok': False, 'error': 'server'}, status=500)
