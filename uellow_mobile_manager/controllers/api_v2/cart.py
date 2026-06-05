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
from datetime import datetime, timedelta

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


# ── Selective checkout (v2.1.65) ────────────────────────────────────
# The customer checks SOME lines in the cart and pays for only those.
# Mechanics: at confirm time the UNSELECTED lines move to a fresh draft
# order which becomes the live cart (it gets the guest token / is the
# newest draft for logged-in users). The original order proceeds through
# the untouched payment/confirm pipeline with only the selected lines,
# so shipping, free-shipping thresholds, coupons and webhooks all see
# the correct subset totals automatically.

def selected_line_ids(src):
    """Parse a `line_ids` value from query/payload — accepts a list or a
    comma-separated string. Returns a list of ints (possibly empty)."""
    raw = src.get('line_ids')
    if raw in (None, '', []):
        return []
    items = raw if isinstance(raw, (list, tuple)) \
        else str(raw).replace(' ', '').split(',')
    out = []
    for x in items:
        try:
            out.append(int(x))
        except Exception:
            continue
    return out


def _product_lines(order):
    return order.order_line.filtered(
        lambda l: not l.display_type and not l.is_reward_line
        and not getattr(l, 'is_delivery', False))


class _SubsetRollback(Exception):
    """Internal: forces the savepoint in subset_view to roll back."""


def subset_view(order, line_ids, fn):
    """Run fn() with the order TEMPORARILY reduced to the selected lines
    (inside a savepoint that is always rolled back). Used by the summary
    and shipping-rate endpoints so the customer sees totals/rates for
    exactly what they selected, without mutating the real cart."""
    keep = set(line_ids)
    drop = _product_lines(order).filtered(lambda l: l.id not in keep)
    if not drop or len(drop) == len(_product_lines(order)):
        return fn()                      # nothing to trim / bad selection
    holder = {}
    try:
        with request.env.cr.savepoint():
            drop.sudo().unlink()
            try:
                if hasattr(order, '_update_programs_and_rewards'):
                    order._update_programs_and_rewards()
            except Exception:
                pass
            holder['v'] = fn()
            raise _SubsetRollback()
    except _SubsetRollback:
        pass
    request.env.invalidate_all()
    return holder['v']


def split_cart_for_checkout(order, line_ids):
    """Keep ONLY the selected lines on the order being placed; move the
    rest to a fresh draft order that becomes the customer's cart.
    Returns the remainder order, or None when everything was selected.
    Raises ValueError when none of the ids belong to this cart."""
    keep = set(line_ids)
    plines = _product_lines(order)
    selected = plines.filtered(lambda l: l.id in keep)
    if not selected:
        raise ValueError('none of the selected lines belong to this cart')
    move = plines - selected
    if not move:
        return None
    Order = request.env['sale.order'].sudo()
    vals = {
        'partner_id': order.partner_id.id,
        'partner_invoice_id': order.partner_invoice_id.id,
        'partner_shipping_id': order.partner_shipping_id.id,
        'website_id': order.website_id.id if order.website_id else False,
        'company_id': order.company_id.id,
        'team_id': order.team_id.id if order.team_id else False,
    }
    if order.pricelist_id:
        vals['pricelist_id'] = order.pricelist_id.id
    tok = order.mobile_cart_token or ''
    if tok:
        vals['mobile_cart_token'] = tok    # guest cart identity follows the remainder
    remainder = Order.create(vals)
    move.sudo().write({'order_id': remainder.id})
    order.sudo().write({
        'mobile_checkout_split': True,
        'mobile_split_token': tok or False,
        'mobile_cart_token': False,
    })
    # Re-evaluate coupon rewards on both sides — a coupon whose minimum
    # is no longer met by the paid subset must not keep its discount.
    for o in (order, remainder):
        try:
            if hasattr(o, '_update_programs_and_rewards'):
                o._update_programs_and_rewards()
        except Exception:
            pass
    _logger.info('selective checkout: order %s keeps %s line(s), '
                 'remainder cart %s got %s line(s)',
                 order.id, len(selected), remainder.id, len(move))
    return remainder


def reclaim_stale_splits(cart):
    """Merge back the lines of selective-checkout orders whose ONLINE
    payment was abandoned: still draft, split flag set, idle for 90+
    minutes and no live payment transaction. Runs on cart open (cheap,
    indexed search) so the customer never loses products."""
    try:
        if not cart:
            return
        Order = request.env['sale.order'].sudo()
        cutoff = (datetime.now() - timedelta(minutes=90)) \
            .strftime('%Y-%m-%d %H:%M:%S')
        dom = [('id', '!=', cart.id), ('state', '=', 'draft'),
               ('mobile_checkout_split', '=', True),
               ('write_date', '<', cutoff)]
        partner = current_partner()
        if partner:
            dom.append(('partner_id', '=', partner.id))
        else:
            tok = _cart_token()
            if not tok:
                return
            dom.append(('mobile_split_token', '=', tok))
        for stale in Order.search(dom, limit=5):
            txs = getattr(stale, 'transaction_ids', None)
            if txs and any(t.state in ('done', 'authorized', 'pending')
                           for t in txs):
                continue                     # a payment may still land
            for l in _product_lines(stale):
                same = _product_lines(cart).filtered(
                    lambda x: x.product_id == l.product_id)
                if same:
                    same[0].product_uom_qty += l.product_uom_qty
                else:
                    l.sudo().write({'order_id': cart.id})
            stale.sudo().write({'mobile_checkout_split': False})
            try:
                stale.action_cancel()
            except Exception:
                stale.sudo().write({'state': 'cancel'})
            _logger.info('selective checkout: reclaimed abandoned split '
                         'order %s back into cart %s', stale.id, cart.id)
    except Exception:
        _logger.debug('reclaim_stale_splits failed', exc_info=True)


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
        dom = [('website_published', '=', True), ('free_over', '=', True)]
        # v2.1.56 — website scoping (17 sites: a carrier of another
        # country must not feed this site's progress bar).
        try:
            from ._common import get_website
            wid = get_website().id
            dom = ['|', ('website_id', '=', False),
                   ('website_id', '=', wid)] + dom
        except Exception:
            pass
        carriers = Carrier.search(dom)
        # v2.1.56 — express carriers are outside the free-shipping engine
        # (per Settings), so their free-over must not set the bar either.
        excl = (ICP.get_param('uellow_free_shipping.express_excluded', '1')
                or '1').strip() in ('1', 'True', 'true')
        if excl:
            carriers = carriers.filtered(lambda c: not carrier_is_express(c))
        if not carriers:
            return None
        amounts = [c.amount for c in carriers if c.amount]
        return min(amounts) if amounts else None
    except Exception:
        return None



# ─── v2.1.51 — FREE-SHIPPING ENGINE ──────────────────────────────────
# One source of truth used by the cart methods list, the checkout
# picker AND the confirm pricing, so what the customer sees is always
# what they pay. Free sources (standard delivery only when the express
# exclusion is ON):
#   1. carrier's own "free over" amount
#   2. a free-shipping COUPON reward applied on the order
#   3. product flags (rule: any / all / off — Settings)
#   4. the global threshold (Settings)

def carrier_is_express(c):
    """Explicit flag first, name heuristic (express/سريع) as fallback."""
    try:
        if 'uellow_is_express' in c._fields and c.uellow_is_express:
            return True
        blob = ' '.join(filter(None, [
            c.name or '',
            getattr(c, 'public_label_en', '') or '',
            getattr(c, 'public_label_ar', '') or '',
        ])).lower()
        return 'express' in blob or 'سريع' in blob
    except Exception:
        return False


def order_free_shipping_reason(order):
    """Order-level free-shipping source or None.
    Returns {'reason': code, 'label': {en, ar}}."""
    ICP = request.env['ir.config_parameter'].sudo()
    # 1) coupon with a free-shipping reward
    try:
        for l in order.order_line:
            rw = getattr(l, 'reward_id', False)
            if rw and getattr(rw, 'reward_type', '') == 'shipping':
                return {'reason': 'coupon',
                        'label': {'en': 'Free shipping coupon',
                                  'ar': 'كوبون شحن مجاني'}}
        for prog in getattr(order, 'no_code_promo_program_ids',
                            request.env['loyalty.program'].browse([])):
            pass
    except Exception:
        pass
    # 2) product flags per rule
    try:
        rule = (ICP.get_param('uellow_free_shipping.product_rule', 'any')
                or 'any').strip()
        if rule in ('any', 'all'):
            prods = [l.product_id.product_tmpl_id
                     for l in order.order_line
                     if l.product_id and not l.display_type
                     and not getattr(l, 'is_reward_line', False)
                     and not getattr(l, 'is_delivery', False)]
            if prods:
                flags = [bool(hasattr(t, '_is_free_shipping')
                              and t._is_free_shipping()) for t in prods]
                hit = any(flags) if rule == 'any' else all(flags)
                if hit:
                    return {'reason': 'product',
                            'label': {'en': 'Free-shipping product',
                                      'ar': 'منتج بشحن مجاني'}}
    except Exception:
        pass
    # 3) global threshold
    try:
        thr = _free_shipping_threshold(order)
        if thr and order.amount_untaxed >= thr:
            return {'reason': 'threshold',
                    'label': {'en': 'Order above %s' % thr,
                              'ar': 'طلب فوق %s' % thr}}
    except Exception:
        pass
    return None


def effective_shipping_price(order, carrier, base_price):
    """(price, free_label_or_None) after the engine. Express services
    are untouched when the exclusion setting is ON (default)."""
    try:
        ICP = request.env['ir.config_parameter'].sudo()
        excl = (ICP.get_param('uellow_free_shipping.express_excluded', '1')
                or '1').strip() in ('1', 'True', 'true')
        if excl and carrier_is_express(carrier):
            return base_price, None
        # carrier's own free-over
        if getattr(carrier, 'free_over', False) and                 order.amount_untaxed >= (getattr(carrier, 'amount', 0) or 0):
            return 0.0, {'en': 'Free over %s' % (carrier.amount or 0),
                         'ar': 'مجاني فوق %s' % (carrier.amount or 0)}
        r = order_free_shipping_reason(order)
        if r:
            return 0.0, r['label']
    except Exception:
        pass
    return base_price, None


def _available_shipping_methods(order):
    """List published delivery carriers + their rate for this cart.
    Uses Uellow's per-zone pricing when configured; falls back to the
    carrier's standard rate_shipment / fixed price."""
    try:
        Carrier = request.env['delivery.carrier'].sudo()
        # v2.1.56 — website + destination scoping (was: every published
        # carrier on every site).
        dom = [('website_published', '=', True)]
        try:
            from ._common import get_website
            wid = get_website().id
            dom = ['|', ('website_id', '=', False),
                   ('website_id', '=', wid)] + dom
        except Exception:
            pass
        carriers = Carrier.search(dom)
        try:
            ship_to = order.partner_shipping_id or order.partner_id
            cc = (ship_to.country_id.code or '') if ship_to and \
                ship_to.country_id else ''
            carriers = carriers.filtered(
                lambda c: not hasattr(c, 'available_for_order')
                or c.available_for_order(order, country_code=cc,
                                         channel='app'))
        except Exception:
            pass
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
            # v2.1.51 — unified free-shipping engine (flags / threshold /
            # coupon / carrier free-over; express excluded per Settings).
            rate, free_label = effective_shipping_price(order, c, rate)
            is_free = free_label is not None
            _rate_money = fmt_price(rate or 0, cur) if rate is not None else None
            out.append({
                'id': c.id,
                'name': bilingual(c, 'name'),
                # 'price' is what the app reads; keep 'rate' for compatibility.
                'price': _rate_money,
                'rate': _rate_money,
                'delivery_type': c.delivery_type,
                'is_free': is_free,
                'free_label': free_label,
                'is_express': carrier_is_express(c),
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
    # v2.1.56 — promo-code PROGRAMS (rule codes) don't live in
    # applied_coupon_ids; surface them too so the app can show/remove them.
    try:
        coupon_codes += [r.code for r in order.code_enabled_rule_ids
                         if r.code and r.code not in coupon_codes]
    except Exception:
        pass

    threshold = _free_shipping_threshold(order)
    free_ship = None
    # v2.1.57 — a flagged product / flagged category / free-shipping
    # coupon means the order ALREADY ships free: show the bar fully
    # qualified instead of asking the customer to add more.
    _reason = order_free_shipping_reason(order)
    if _reason and _reason.get('reason') in ('product', 'coupon'):
        free_ship = {
            'threshold': fmt_price(threshold or 0, cur),
            'remaining': fmt_price(0, cur),
            'progress': 1.0,
            'qualified': True,
            'reason': _reason['reason'],
            'label': _reason.get('label'),
        }
    elif threshold:
        gap = max(0.0, threshold - order.amount_untaxed)
        pct = min(1.0, (order.amount_untaxed / threshold) if threshold else 0)
        free_ship = {
            'threshold': fmt_price(threshold, cur),
            'remaining': fmt_price(gap, cur),
            'progress': round(pct, 4),
            'qualified': gap <= 0,
            'reason': 'threshold',
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
        if order:
            # Recover products from any abandoned selective checkout.
            reclaim_stale_splits(order)
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
            # v2.1.51 — _try_apply_code only REGISTERS the code; the reward
            # still has to be claimed or no discount line ever appears
            # (the "coupon does nothing" bug). Claim the first applicable
            # reward of each returned coupon, Odoo-policy compliant.
            if isinstance(res, dict):
                for coupon, rewards in res.items():
                    for reward in rewards:
                        try:
                            r2 = order._apply_program_reward(reward, coupon)
                            if not (isinstance(r2, dict) and r2.get('error')):
                                applied = True
                                break
                        except Exception:
                            continue
            try:
                if hasattr(order, '_update_programs_and_rewards'):
                    order._update_programs_and_rewards()
            except Exception:
                pass
            # a discount line present = definitely applied (covers
            # automatic programs that skip the claim step)
            if order.order_line.filtered('is_reward_line'):
                applied = True
            if not applied:
                return fail('COUPON_NOT_APPLICABLE',
                            'This coupon does not apply to your cart — '
                            'check its conditions / هذا الكوبون لا ينطبق '
                            'على سلتك، راجع شروطه', 400)
        except Exception as e:
            return fail('COUPON_FAILED', str(e), 400)
        return ok({'applied': applied, 'cart': serialize_cart(order)})

    @http.route('/api/mobile/v2/cart/remove-coupon', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def remove_coupon(self, **kw):
        # v2.1.56 — accepts an optional `code`: removes ONLY that coupon and
        # its reward lines (the × button used to wipe every applied coupon).
        # Without a code it keeps the old wipe-all behaviour.
        p = get_payload()
        code = (p.get('code') or '').strip()
        order = _get_or_create_order(create=False)
        if order and code:
            # v2.1.73 — COMPREHENSIVE coupon removal. A typed code spawns
            # several linked records that each, if left behind, make
            # _update_programs_and_rewards() re-apply the discount:
            #   • applied_coupon_ids (the card, code may differ from typed)
            #   • code_enabled_rule_ids (the rule that was unlocked)
            #   • coupon_point_ids (Odoo 18 point ledger — THE main culprit)
            #   • reward lines on the order
            # We resolve the program from ALL of: typed code on a card, the
            # rule code, applied cards, and coupon_point_ids — then nuke
            # everything tied to those programs.
            # Resolve the program(s) for this code. The typed code lives
            # on the RULE (and order.code_enabled_rule_ids) while the
            # coupon card gets an auto-generated code — so search globally.
            programs = request.env['loyalty.program']
            try:
                programs |= request.env['loyalty.rule'].sudo().search(
                    [('code', '=', code)]).mapped('program_id')
                programs |= request.env['loyalty.card'].sudo().search(
                    [('code', '=', code)]).mapped('program_id')
                programs |= order.code_enabled_rule_ids.filtered(
                    lambda r: (r.code or '') == code).mapped('program_id')
            except Exception:
                pass
            # cards/rules belonging to those programs (any code)
            cards = order.applied_coupon_ids.filtered(
                lambda c: c.program_id in programs or (c.code or '') == code)
            rules = request.env['loyalty.rule']
            try:
                rules = order.code_enabled_rule_ids.filtered(
                    lambda r: r.program_id in programs or (r.code or '') == code)
            except Exception:
                pass
            # reward lines
            order.order_line.filtered(
                lambda l: l.is_reward_line and (
                    (l.coupon_id and (l.coupon_id in cards
                                      or l.coupon_id.program_id in programs))
                    or (l.reward_id and l.reward_id.program_id in programs))
            ).unlink()
            # point ledger — by program OR by the typed code on the coupon
            try:
                order.coupon_point_ids.filtered(
                    lambda cp: cp.coupon_id.program_id in programs
                    or (cp.coupon_id.code or '') == code).unlink()
            except Exception:
                pass
            if cards:
                order.applied_coupon_ids = [(3, c.id) for c in cards]
            if rules:
                order.code_enabled_rule_ids = [(3, r.id) for r in rules]
            try:
                order._update_programs_and_rewards()
            except Exception:
                pass
            # safety net: if the recompute somehow re-created a reward line
            # for a removed program, strip it again.
            try:
                order.order_line.filtered(
                    lambda l: l.is_reward_line and l.reward_id
                    and l.reward_id.program_id in programs).unlink()
            except Exception:
                pass
        elif order:
            # Drop reward lines
            order.order_line.filtered('is_reward_line').unlink()
            try:
                order.applied_coupon_ids = [(5, 0, 0)]
            except Exception:
                pass
            try:
                order.code_enabled_rule_ids = [(5, 0, 0)]
            except Exception:
                pass
            try:
                order.coupon_point_ids.unlink()
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
        serial = share.serial or ''
        return ok({
            'url': url, 'token': share.token,
            # v2.1.66 — human serial (typed instead of scanning) + the
            # grouped display form the dialog shows.
            'serial': serial,
            'serial_display': '-'.join(
                [serial[i:i + 4] for i in range(0, len(serial), 4)]),
        })

    @http.route('/api/mobile/v2/cart/import', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def import_cart(self, **kw):
        """v2.1.66 — adopt a shared cart by QR scan / pasted link /
        typed serial. Merges the shared items into the caller's cart
        (guest or logged-in) and returns the updated cart."""
        import json as _json
        p = get_payload()
        share = request.env['mobile.cart.share'].sudo().find_by_code(
            p.get('code') or '')
        if not share:
            return fail('SHARE_NOT_FOUND',
                        'Cart code not found or expired / الرمز غير صحيح '
                        'أو منتهي الصلاحية', 404)
        try:
            items = _json.loads(share.lines_json or '[]')
        except Exception:
            items = []
        if not items:
            return fail('SHARE_EMPTY', 'This shared cart is empty', 400)
        order = _get_or_create_order(create=True)
        added = 0
        Product = request.env['product.product'].sudo()
        for it in items:
            try:
                pid = int(it.get('product_id') or 0)
                qty = float(it.get('qty') or 1)
            except Exception:
                continue
            product = Product.browse(pid)
            if not product.exists() or not product.active:
                continue
            same = order.order_line.filtered(
                lambda l: l.product_id.id == pid and not l.display_type
                and not l.is_reward_line
                and not getattr(l, 'is_delivery', False))
            try:
                if same:
                    same[0].product_uom_qty += qty
                else:
                    order.order_line = [(0, 0, {
                        'product_id': pid,
                        'product_uom_qty': qty,
                    })]
                added += 1
            except Exception:
                _logger.warning('cart import: failed product %s', pid,
                                exc_info=True)
        share.adopted_count += 1
        return ok({'cart': serialize_cart(order), 'added': added})


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
