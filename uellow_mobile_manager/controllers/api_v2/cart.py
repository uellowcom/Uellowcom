"""
Cart endpoints — /api/mobile/v2/cart/*

get            GET                              → current cart
add            POST  product_id, qty, variant_id → cart
update         POST  line_id, qty                → cart
remove         POST  line_id                     → cart
clear          POST                              → cart
apply_coupon   POST  code                        → cart + applied?
remove_coupon  POST                              → cart

A cart is a draft sale.order. For guests we identify by session cookie
+ a `mobile_cart_token` we set on first add. The token is returned in
every cart response so the Flutter side can store it and pass it back
as `X-Cart-Token` (or include `?cart_token=`). Logged-in users always
use their res.partner; we transparently merge any guest token cart on
login (handled when issue_token is called by the v2 auth login).
"""
import logging

from odoo import fields, http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, current_partner,
    img_url, base_url, fmt_price, bilingual, get_website,
)

_logger = logging.getLogger(__name__)


def _cart_token():
    tok = request.httprequest.args.get('cart_token') \
        or request.httprequest.headers.get('X-Cart-Token') \
        or request.httprequest.cookies.get('mobile_cart_token')
    return (tok or '').strip()


def _get_or_create_order(create=True):
    """Return the draft cart for this request (or empty recordset).
    Mobile clients identify their guest cart via X-Cart-Token. Logged
    in users always get the partner's open draft order."""
    Order = request.env['sale.order'].sudo()
    partner = current_partner()
    if partner:
        order = Order.search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'draft'),
            ('website_id', '!=', False),
        ], limit=1, order='id desc')
        # Claim the guest cart: items added before signing in live on a
        # cart-token order owned by the public user. Without this, checkout
        # after the sign-in dialog sees the partner's (empty) order and
        # reports "cart is empty". Adopt it into the partner.
        tok = _cart_token()
        if tok:
            guest = Order.search([
                ('mobile_cart_token', '=', tok),
                ('state', '=', 'draft'),
            ], limit=1)
            if (guest and guest.exists() and guest.partner_id.id != partner.id
                    and guest.order_line.filtered(lambda l: not l.display_type)):
                # The GUEST cart wins. The user signed in mid-purchase (on the
                # way to buy what's in this cart) — merging the partner's old
                # draft cart into it silently inflated the checkout total
                # ("8.500 in the cart but 28.210 at checkout"). So: adopt the
                # guest cart as the partner's active cart and leave any old
                # draft cart untouched — it resurfaces only when the user
                # signs in WITHOUT an in-progress guest cart.
                try:
                    guest.sudo().write({
                        'partner_id': partner.id,
                        'partner_invoice_id': partner.id,
                        'partner_shipping_id': partner.id,
                    })
                except Exception:
                    guest.sudo().write({'partner_id': partner.id})
                return guest
        if not order and create:
            website = get_website()
            order = Order.create({
                'partner_id': partner.id,
                'website_id': website.id,
                'team_id': website.salesteam_id.id if website.salesteam_id else False,
            })
        return order

    # Guest path
    tok = _cart_token()
    if tok:
        order = Order.search([
            ('mobile_cart_token', '=', tok),
            ('state', '=', 'draft'),
        ], limit=1)
        if order:
            return order
    if not create:
        return Order.browse([])
    website = get_website()
    public_user = website.user_id or request.env.ref('base.public_user')
    import secrets
    new_token = secrets.token_urlsafe(24)
    order = Order.create({
        'partner_id': public_user.partner_id.id,
        'website_id': website.id,
        'mobile_cart_token': new_token,
    })
    return order


def _consolidate_lines(order):
    """Merge duplicate lines of the SAME product into one line (sum the
    quantities). Duplicates crept in via older cart merges / reorders; the
    customer expects re-adding a product to bump its qty, not add a new row."""
    seen = {}
    for l in order.order_line.filtered(
            lambda l: not l.display_type and not l.is_reward_line
            and not getattr(l, 'is_delivery', False)):
        key = l.product_id.id
        if key in seen:
            try:
                seen[key].product_uom_qty += l.product_uom_qty
                l.sudo().unlink()
            except Exception:
                pass
        else:
            seen[key] = l


def _free_shipping_threshold(order):
    """Resolve the free-shipping threshold. Priority:
       1. ir.config_parameter `uellow_mobile.free_shipping_threshold`
       2. Smallest `delivery.carrier.amount` among free-over carriers
       Returns the amount or None if no free-shipping promo is set up."""
    try:
        ICP = request.env['ir.config_parameter'].sudo()
        # v2.1.23 — the Settings field (uellow_free_shipping.threshold_kwd)
        # now feeds the cart progress bar too; legacy param kept as backup.
        raw = (ICP.get_param('uellow_free_shipping.threshold_kwd', '')
               or ICP.get_param('uellow_mobile.free_shipping_threshold', ''))
        if raw:
            try:
                v = float(raw)
                if v > 0:
                    return v
            except Exception:
                pass
        Carrier = request.env['delivery.carrier'].sudo()
        carriers = Carrier.search([
            ('website_published', '=', True),
            ('free_over', '=', True),
        ])
        if not carriers:
            return None
        amounts = [c.amount for c in carriers if c.amount]
        return min(amounts) if amounts else None
    except Exception:
        return None


def _available_shipping_methods(order):
    """List published delivery carriers + their rate for this cart.
    Uses Uellow's per-zone pricing when configured; falls back to the
    carrier's standard rate_shipment / fixed price."""
    try:
        Carrier = request.env['delivery.carrier'].sudo()
        carriers = Carrier.search([('website_published', '=', True)])
        cur = order.currency_id or request.env.company.currency_id
        out = []
        for c in carriers:
            rate = None
            zone_match = None
            # Prefer Uellow zones if defined for this carrier
            if c.uellow_zone_ids:
                z = request.env['uellow.delivery.zone'].sudo().quote_for(
                    c, order.partner_shipping_id or order.partner_id)
                if z:
                    rate = z.price
                    _win_en = getattr(z, 'delivery_window', '') or ''
                    _win_ar = getattr(z, 'delivery_window_ar', '') or _win_en
                    zone_match = {
                        'id': z.id, 'name': z.name,
                        'cutoff_time': z.cutoff_time or '',
                        'delivery_window': {'en': _win_en, 'ar': _win_ar},
                        # v2.1.2 — COD surcharge (config only; not yet folded
                        # into the total — awaiting activation decision).
                        'cash_surcharge': getattr(z, 'cash_surcharge', 0.0) or 0.0,
                    }
            if rate is None:
                try:
                    res = c.rate_shipment(order)
                    if res.get('success'):
                        rate = res.get('price', 0)
                except Exception:
                    pass
            is_free = bool(c.free_over and order.amount_untaxed >= (c.amount or 0))
            if is_free:
                rate = 0.0
            _rate_money = fmt_price(rate or 0, cur) if rate is not None else None
            out.append({
                'id': c.id,
                'name': bilingual(c, 'name'),
                # 'price' is what the app reads; keep 'rate' for compatibility.
                'price': _rate_money,
                'rate': _rate_money,
                'delivery_type': c.delivery_type,
                'is_free': is_free,
                'zone': zone_match,
            })
        return out
    except Exception:
        return []


def serialize_cart(order):
    if not order:
        return _empty_cart()
    cur = order.currency_id or request.env.company.currency_id
    lines = []
    # Exclude delivery (shipping) lines — they are NOT cart products and must
    # never show as an item or inflate the subtotal.
    for line in order.order_line.filtered(
            lambda l: not l.display_type and not getattr(l, 'is_delivery', False)):
        product = line.product_id
        lines.append({
            'id':           line.id,
            'product_id':   product.product_tmpl_id.id,
            'variant_id':   product.id,
            'name':         bilingual(product.product_tmpl_id, 'name'),
            'sku':          product.default_code or '',
            'image':        img_url('product.product', product.id, 'image_256',
                                    unique=product.write_date),
            'qty':          line.product_uom_qty,
            'unit_price':   fmt_price(line.price_unit, cur),
            'subtotal':     fmt_price(line.price_subtotal, cur),
            'total':        fmt_price(line.price_total, cur),
            'attributes':   [{
                'attribute': bilingual(ptav.attribute_id, 'name'),
                'value':     bilingual(ptav.product_attribute_value_id, 'name'),
            } for ptav in product.product_template_attribute_value_ids],
        })

    # Discounts (coupons / loyalty / per-line %). Computed robustly so the
    # value shows whether the coupon is a reward LINE or a per-line percentage
    # discount. `subtotal` below is the GROSS (pre-discount) so that
    # subtotal − discount (+ shipping + tax) == total. For carts with no
    # discount this is identical to the old behaviour (gross == net).
    sale_lines = order.order_line.filtered(
        lambda l: not l.display_type and not l.is_reward_line
        and not getattr(l, 'is_delivery', False))
    gross = sum((l.price_unit or 0.0) * (l.product_uom_qty or 0.0) for l in sale_lines)
    net = sum(l.price_subtotal for l in sale_lines)
    line_discount = max(0.0, gross - net)
    reward_discount = sum(-cl.price_total
                          for cl in order.order_line.filtered(lambda l: l.is_reward_line))
    discount = line_discount + reward_discount
    coupon_codes = []
    try:
        coupon_codes = [c.code for c in order.applied_coupon_ids]
    except Exception:
        pass

    threshold = _free_shipping_threshold(order)
    free_ship = None
    if threshold:
        gap = max(0.0, threshold - order.amount_untaxed)
        pct = min(1.0, (order.amount_untaxed / threshold) if threshold else 0)
        free_ship = {
            'threshold': fmt_price(threshold, cur),
            'remaining': fmt_price(gap, cur),
            'progress': round(pct, 4),
            'qualified': gap <= 0,
        }

    return {
        'order_id': order.id,
        'cart_token': order.mobile_cart_token or '',
        'currency': cur.name,
        'lines': lines,
        'line_count': len(lines),
        'totals': {
            'subtotal': fmt_price(gross if discount else order.amount_untaxed, cur),
            'tax':      fmt_price(order.amount_tax, cur),
            'shipping': fmt_price(order.amount_delivery or 0, cur),
            'discount': fmt_price(discount, cur),
            'total':    fmt_price(order.amount_total, cur),
        },
        'coupons': coupon_codes,
        'free_shipping': free_ship,
        'shipping_methods': _available_shipping_methods(order),
    }


def _empty_cart():
    cur = request.env.company.currency_id
    return {
        'order_id': None,
        'cart_token': '',
        'currency': cur.name,
        'lines': [],
        'line_count': 0,
        'totals': {
            'subtotal': fmt_price(0, cur), 'tax': fmt_price(0, cur),
            'shipping': fmt_price(0, cur), 'discount': fmt_price(0, cur),
            'total': fmt_price(0, cur),
        },
        'coupons': [],
        'free_shipping': None,
        'shipping_methods': [],
    }


class MobileCartAPI(http.Controller):

    @http.route('/api/mobile/v2/cart', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def get_cart(self, **kw):
        order = _get_or_create_order(create=False)
        return ok({'cart': serialize_cart(order)})

    @http.route('/api/mobile/v2/cart/add', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def add(self, **kw):
        p = get_payload()
        try:
            qty = float(p.get('qty', 1) or 1)
            # Flutter app sends `product_id` = product.template ID (what
            # the user is looking at on screen). Only when they explicitly
            # pass `variant_id` do we treat it as product.product.
            variant_id = int(p.get('variant_id') or 0)
            tmpl_id    = int(p.get('product_id') or 0)
        except Exception:
            return fail('BAD_REQUEST', 'product_id and qty required')
        if (not variant_id and not tmpl_id) or qty <= 0:
            return fail('BAD_REQUEST', 'product_id and qty required')

        product = request.env['product.product'].sudo().browse([])
        if variant_id:
            product = request.env['product.product'].sudo().browse(variant_id)
            if not product.exists():
                product = request.env['product.product'].sudo().browse([])
        if not product and tmpl_id:
            tmpl = request.env['product.template'].sudo().browse(tmpl_id)
            if tmpl.exists() and tmpl.product_variant_ids:
                product = tmpl.product_variant_ids[0]
        if not product:
            return fail('NOT_FOUND', 'Product not found', 404)

        order = _get_or_create_order(create=True)
        existing = order.order_line.filtered(lambda l: l.product_id == product and not l.is_reward_line)
        if existing:
            existing[0].product_uom_qty += qty
        else:
            request.env['sale.order.line'].sudo().create({
                'order_id': order.id,
                'product_id': product.id,
                'product_uom_qty': qty,
            })
        _consolidate_lines(order)
        order = request.env['sale.order'].sudo().browse(order.id)
        return ok({'cart': serialize_cart(order)})

    @http.route('/api/mobile/v2/cart/update', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def update(self, **kw):
        p = get_payload()
        try:
            line_id = int(p.get('line_id') or 0)
            qty     = float(p.get('qty', 0) or 0)
        except Exception:
            return fail('BAD_REQUEST', 'line_id and qty required')
        if not line_id:
            return fail('BAD_REQUEST', 'line_id required')
        line = request.env['sale.order.line'].sudo().browse(line_id)
        if not line.exists():
            return fail('NOT_FOUND', 'Line not found', 404)
        if qty <= 0:
            line.unlink()
        else:
            line.product_uom_qty = qty
        return ok({'cart': serialize_cart(line.order_id)})

    @http.route('/api/mobile/v2/cart/remove', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def remove(self, **kw):
        p = get_payload()
        try:
            line_id = int(p.get('line_id') or 0)
        except Exception:
            return fail('BAD_REQUEST', 'line_id required')
        line = request.env['sale.order.line'].sudo().browse(line_id)
        order_id = line.order_id.id if line.exists() else None
        if line.exists():
            line.unlink()
        order = request.env['sale.order'].sudo().browse(order_id) if order_id else None
        return ok({'cart': serialize_cart(order)})

    @http.route('/api/mobile/v2/cart/clear', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def clear(self, **kw):
        order = _get_or_create_order(create=False)
        if order:
            order.order_line.unlink()
        return ok({'cart': serialize_cart(order)})

    @http.route('/api/mobile/v2/cart/apply-coupon', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def apply_coupon(self, **kw):
        p = get_payload()
        code = (p.get('code') or '').strip()
        if not code:
            return fail('BAD_REQUEST', 'code required')
        order = _get_or_create_order(create=False)
        if not order:
            return fail('NO_CART', 'Cart is empty', 400)
        applied = False
        try:
            res = order._try_apply_code(code) if hasattr(order, '_try_apply_code') else None
            if isinstance(res, dict) and res.get('error'):
                return fail('COUPON_INVALID', res['error'], 400)
            applied = True
        except Exception as e:
            return fail('COUPON_FAILED', str(e), 400)
        return ok({'applied': applied, 'cart': serialize_cart(order)})

    @http.route('/api/mobile/v2/cart/remove-coupon', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def remove_coupon(self, **kw):
        order = _get_or_create_order(create=False)
        if order:
            # Drop reward lines
            order.order_line.filtered('is_reward_line').unlink()
            try:
                order.applied_coupon_ids = [(5, 0, 0)]
            except Exception:
                pass
        return ok({'cart': serialize_cart(order)})

    # ──────────────────────────────────────────────────────────────────
    # Multi-select bulk operations + share-cart
    # ──────────────────────────────────────────────────────────────────

    @http.route('/api/mobile/v2/cart/bulk-remove', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def bulk_remove(self, **kw):
        p = get_payload()
        ids = [int(x) for x in (p.get('line_ids') or []) if str(x).isdigit()]
        order = _get_or_create_order(create=False)
        if order and ids:
            order.order_line.filtered(lambda l: l.id in ids).unlink()
        return ok({'cart': serialize_cart(order)})

    @http.route('/api/mobile/v2/cart/bulk-wishlist', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def bulk_wishlist(self, **kw):
        p = get_payload()
        ids = [int(x) for x in (p.get('line_ids') or []) if str(x).isdigit()]
        order = _get_or_create_order(create=False)
        if not order or not ids:
            return ok({'cart': serialize_cart(order)})
        lines = order.order_line.filtered(lambda l: l.id in ids)
        partner = current_partner()
        if partner:
            Wish = request.env['product.wishlist'].sudo()
            for ln in lines:
                if not Wish.search_count([
                    ('partner_id', '=', partner.id),
                    ('product_id', '=', ln.product_id.id),
                ]):
                    try:
                        Wish.create({
                            'partner_id': partner.id,
                            'product_id': ln.product_id.id,
                            'currency_id': ln.currency_id.id,
                            'price': ln.price_unit,
                        })
                    except Exception:
                        pass
        lines.unlink()
        return ok({'cart': serialize_cart(order)})

    @http.route('/api/mobile/v2/cart/share', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def share_cart(self, **kw):
        """Create a one-time share token. Recipient can open the link to
        adopt the items into their own cart."""
        order = _get_or_create_order(create=False)
        if not order or not order.order_line:
            return fail('NO_CART', 'Cart is empty', 400)
        Share = request.env['mobile.cart.share'].sudo()
        share = Share.create({
            'order_id': order.id,
            'partner_id': order.partner_id.id if order.partner_id else False,
            'lines_json': _share_lines_snapshot(order),
        })
        site = (request.env['ir.config_parameter'].sudo()
                .get_param('web.base.url') or base_url()).rstrip('/')
        url = '%s/cart/share/%s' % (site, share.token)
        return ok({'url': url, 'token': share.token})


def _share_lines_snapshot(order):
    """JSON snapshot of cart lines so the share survives even if the
    original order changes."""
    import json
    items = []
    for ln in order.order_line.filtered(lambda l: not l.is_reward_line):
        items.append({
            'product_id': ln.product_id.id,
            'name': ln.product_id.display_name,
            'qty': float(ln.product_uom_qty or 1),
            'price': float(ln.price_unit or 0),
        })
    return json.dumps(items)
