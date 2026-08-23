# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request


def _resolve_units(ids, variant_map=None, qty_map=None):
    """Resolve a bundle to concrete purchasable units — one per template id,
    honouring an optional {template_id: variant_id} colour/variant choice and
    falling back to the template's default variant. Backward compatible: an
    old client that sends only template ids just gets default variants.
    Returns a list of dicts: {tmpl, variant, price, cost}."""
    # Coerce the variant map defensively (a list payload used to raise a 500).
    if not isinstance(variant_map, dict):
        variant_map = {}
    try:
        variant_map = {int(k): int(v) for k, v in variant_map.items()}
    except Exception:
        variant_map = {}
    # De-duplicate + cap the id list: min_items must count DISTINCT products
    # (duplicate ids used to clear the 2-item gate + inflate the discount), and
    # an unbounded list on a public endpoint is a DoS.
    seen, clean = set(), []
    for i in list(ids or [])[:50]:
        try:
            n = int(i)
        except Exception:
            continue
        if n > 0 and n not in seen:
            seen.add(n)
            clean.append(n)
    templates = request.env['product.template'].sudo().browse(clean).exists()
    website = getattr(request, 'website', None)
    cid = request.env.company.id

    def _allowed(t):
        # sellable, this company (never a company-7 World product → the old
        # "Incompatible companies" checkout crash), and this website.
        if not t.sale_ok:
            return False
        if t.company_id and t.company_id.id != cid:
            return False
        if website and t.website_id and t.website_id.id != website.id:
            return False
        return True

    templates = templates.filtered(_allowed)
    Var = request.env['product.product'].sudo()
    units = []
    for t in templates:
        chosen = variant_map.get(t.id)
        variant = Var.browse(chosen) if chosen else t.product_variant_id
        if not variant or variant.product_tmpl_id != t or not variant.active:
            variant = t.product_variant_id
        if not variant:
            continue
        units.append({
            'tmpl': t, 'variant': variant,
            'price': variant.list_price or t.list_price or 0.0,
            'cost': variant.standard_price or t.standard_price or 0.0,
            'qty': max(1, min(int((qty_map or {}).get(str(t.id), 1) or 1), 99)),
        })
    return units


def _lines_from_ids(ids, variant_map=None, qty_map=None):
    """Return (units, engine-lines). Each unit carries its quantity; the engine
    receives one line per physical unit (qty expanded) so subtotal/cost/margin
    all scale and the item count reflects total units."""
    units = _resolve_units(ids, variant_map, qty_map)
    lines = [{'price': u['price'], 'cost': u['cost']}
             for u in units for _ in range(u['qty'])]
    return units, lines


def _unit_item(u):
    """Serialised sheet item for a resolved unit (template + chosen variant)."""
    t, v = u['tmpl'], u['variant']
    multi = t.product_variant_count > 1
    return {
        'id': t.id, 'variant_id': v.id,
        'name': (v.display_name if multi else t.name) or '',
        'price': round(u['price'], 3),
        'qty': u.get('qty', 1),
        'line_total': round(u['price'] * u.get('qty', 1), 3),
        'url': t.website_url or ('/shop/%s' % t.id),
        'image': ('/web/image/product.product/%s/image_256' % v.id) if multi
                 else ('/web/image/product.template/%s/image_256' % t.id),
    }


def country_code():
    """Best-effort ISO country code for the current visitor."""
    code = ''
    try:
        gc = request.geoip
        code = (gc.get('country_code') if isinstance(gc, dict)
                else getattr(gc, 'country_code', None)) or ''
    except Exception:
        code = ''
    if not code and getattr(request, 'website', None) and request.website.company_id.country_id:
        code = request.website.company_id.country_id.code or ''
    return code


def lamma_summary():
    """Compute the current session Lamma (used by web routes)."""
    ids = request.session.get('lamma_ids') or []
    vmap = request.session.get('lamma_variants') or {}
    ltype = request.session.get('lamma_type') or 'normal'
    qmap = request.session.get('lamma_qty') or {}
    cfg = request.env['uellow.lamma.config'].sudo().get_config()
    units, lines = _lines_from_ids(ids, vmap, qmap)
    q = cfg.compute_lamma(lines, ltype)
    q['items'] = [_unit_item(u) for u in units]
    q['label'] = cfg.brand_label
    q['badge'] = cfg.badge_text
    q['enabled'] = bool(cfg.active and cfg.enable_all_products
                        and cfg._country_enabled(country_code()))
    q['replace_add_to_cart'] = cfg.replace_add_to_cart
    q['min_items'] = cfg.min_items
    q['installment_enabled'] = cfg.installment_enabled
    q['installment_min_amount'] = cfg.installment_min_amount
    q['currency'] = (request.env.company.currency_id.symbol
                     or request.env.company.currency_id.name or 'KD')
    # ── tier progress (powers progress bar + celebration on web & app) ──
    try:
        _n = q.get('n') or len(units); _amt = q.get('subtotal') or 0.0
        _ts = []
        for t in cfg.tier_ids.sorted(lambda r: (r.min_qty, r.min_amount)):
            reached = (_n >= t.min_qty) if cfg.discount_mode == 'count' else (_amt >= t.min_amount)
            _ts.append({'pct': round(t.discount_pct, 1), 'min_qty': t.min_qty,
                        'min_amount': round(t.min_amount, 3), 'reached': reached})
        q['tiers'] = _ts
        q['tier_pct'] = round(q.get('discount_pct') or 0.0, 1)
        _nx = next((t for t in _ts if not t['reached']), None)
        if _nx:
            _prev = [t for t in _ts if t['reached']]
            if cfg.discount_mode == 'count':
                q['next_tier'] = {'pct': _nx['pct'], 'need_items': max(0, _nx['min_qty'] - _n), 'need_amount': 0.0}
                _b = _prev[-1]['min_qty'] if _prev else 0
                q['progress'] = min(1.0, max(0.0, (_n - _b) / max(1, _nx['min_qty'] - _b)))
            else:
                q['next_tier'] = {'pct': _nx['pct'], 'need_items': 0, 'need_amount': round(max(0.0, _nx['min_amount'] - _amt), 3)}
                _b = _prev[-1]['min_amount'] if _prev else 0.0
                q['progress'] = min(1.0, max(0.0, (_amt - _b) / max(0.001, _nx['min_amount'] - _b)))
        else:
            q['next_tier'] = None; q['progress'] = 1.0
    except Exception:
        q['tiers'] = []; q['next_tier'] = None; q['progress'] = 0.0; q['tier_pct'] = q.get('discount_pct') or 0.0
    q['_country'] = country_code()
    return q


def _log(action, product_id=None, summary=None, source='web'):
    try:
        request.env['uellow.lamma.activity'].sudo().log(action, product_id, summary, source)
    except Exception:
        pass


def _seed_lamma_from_cart():
    """When a Lamma is STARTED and the cart already has items, pull those cart
    products into the Lamma so they appear as added Lamma products (requested)."""
    try:
        order = request.website.sale_get_order()
        if not order:
            return
        ids = list(request.session.get('lamma_ids') or [])
        vmap = dict(request.session.get('lamma_variants') or {})
        removed = set(request.session.get('lamma_removed') or [])
        changed = False
        for l in order.order_line:
            if l.display_type or getattr(l, 'is_reward_line', False) or not l.product_id:
                continue
            t = l.product_id.product_tmpl_id
            if not t.sale_ok:
                continue
            if t.id in removed:
                continue  # user explicitly removed it — never re-seed
            if t.id not in ids:
                ids.append(t.id)
                changed = True
            vmap[str(t.id)] = l.product_id.id
            _sq = dict(request.session.get('lamma_qty') or {})
            _sq[str(t.id)] = max(1, min(int(l.product_uom_qty or 1), 99))
            request.session['lamma_qty'] = _sq
        if changed:
            request.session['lamma_ids'] = ids
            request.session['lamma_variants'] = vmap
    except Exception:
        pass




# ── Gamification / social helpers (leaderboard, savings, badges, abandoned) ──
def _cur_sym():
    c = request.env.company.currency_id
    return c.symbol or c.name or 'KD'


def _augment_tiers(cfg, q, n, amount):
    """Attach tier-progress (tiers/next_tier/progress/tier_pct) — shared by web + app."""
    try:
        _ts = []
        for t in cfg.tier_ids.sorted(lambda r: (r.min_qty, r.min_amount)):
            reached = (n >= t.min_qty) if cfg.discount_mode == 'count' else (amount >= t.min_amount)
            _ts.append({'pct': round(t.discount_pct, 1), 'min_qty': t.min_qty,
                        'min_amount': round(t.min_amount, 3), 'reached': reached})
        q['tiers'] = _ts
        q['tier_pct'] = round(q.get('discount_pct') or 0.0, 1)
        _nx = next((t for t in _ts if not t['reached']), None)
        if _nx:
            _prev = [t for t in _ts if t['reached']]
            if cfg.discount_mode == 'count':
                q['next_tier'] = {'pct': _nx['pct'], 'need_items': max(0, _nx['min_qty'] - n), 'need_amount': 0.0}
                _b = _prev[-1]['min_qty'] if _prev else 0
                q['progress'] = min(1.0, max(0.0, (n - _b) / max(1, _nx['min_qty'] - _b)))
            else:
                q['next_tier'] = {'pct': _nx['pct'], 'need_items': 0, 'need_amount': round(max(0.0, _nx['min_amount'] - amount), 3)}
                _b = _prev[-1]['min_amount'] if _prev else 0.0
                q['progress'] = min(1.0, max(0.0, (amount - _b) / max(0.001, _nx['min_amount'] - _b)))
        else:
            q['next_tier'] = None; q['progress'] = 1.0
    except Exception:
        q.setdefault('tiers', []); q.setdefault('next_tier', None)
        q.setdefault('progress', 0.0); q['tier_pct'] = q.get('discount_pct') or 0.0
    return q


def _mask_name(nm):
    nm = (nm or '').strip()
    if not nm:
        return 'زائر يلو'
    p = nm.split()
    return p[0] + ((' ' + p[1][0] + '.') if len(p) > 1 and p[1] else '')


def _act():
    return request.env['uellow.lamma.activity'].sudo()


def _who():
    pid = False
    try:
        if not request.env.user._is_public():
            pid = request.env.user.partner_id.id
    except Exception:
        pid = False
    sid = getattr(getattr(request, 'session', None), 'sid', '') or ''
    return pid, sid


def _owner_dom(pid, sid):
    return (['|', ('partner_id', '=', pid), ('session_key', '=', sid)]
            if pid else [('session_key', '=', sid)])


def _app_partner():
    """Resolve the Flutter app's authenticated partner id (Bearer token), or False."""
    try:
        from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import current_partner
        p = current_partner()
        return p.id if p else False
    except Exception:
        return False


def _lb_leaderboard(days=1, limit=8):
    from datetime import timedelta
    since = fields.Datetime.now() - timedelta(days=days)
    recs = _act().search([('action', '=', 'checkout'),
                          ('create_date', '>=', since), ('discount', '>', 0)])
    agg = {}
    for r in recs:
        key = ('p', r.partner_id.id) if r.partner_id else ('s', r.session_key or r.id)
        e = agg.setdefault(key, {'name': _mask_name(r.partner_id.name if r.partner_id else ''),
                                 'saved': 0.0, 'items': 0})
        e['saved'] += (r.discount or 0.0); e['items'] += (r.items or 0)
    rows = sorted(agg.values(), key=lambda x: -x['saved'])[:limit]
    tot = round(sum(x['saved'] for x in agg.values()), 3)
    for i, r in enumerate(rows):
        r['rank'] = i + 1; r['saved'] = round(r['saved'], 3)
    return {'rows': rows, 'community_total': tot, 'currency': _cur_sym()}


def _lb_savings(days=30, pid=None, sid=None):
    from datetime import timedelta
    if pid is None and sid is None:
        pid, sid = _who()
    since = fields.Datetime.now() - timedelta(days=days)
    recs = _act().search(_owner_dom(pid, sid) + [('action', '=', 'checkout'),
                         ('create_date', '>=', since), ('discount', '>', 0)])
    return {'saved': round(sum(r.discount or 0 for r in recs), 3),
            'count': len(recs), 'days': days, 'currency': _cur_sym()}


def _lb_badges(pid=None, sid=None):
    if pid is None and sid is None:
        pid, sid = _who()
    ck = _act().search(_owner_dom(pid, sid) + [('action', '=', 'checkout')])
    n = len(ck); saved = sum(c.discount or 0 for c in ck)
    ndays = len({c.create_date.date() for c in ck if c.create_date})
    ingroup = bool(pid and request.env['uellow.lamma.group'].sudo().search_count(
        [('host_partner_id', '=', pid)]))
    defs = [
        {'key': 'expert', 'emoji': '🎉', 'name': 'بطل البداية', 'earned': n >= 1, 'hint': 'أكمل أول لمّة'},
        {'key': 'gold', 'emoji': '👑', 'name': 'ملك التوفير', 'earned': saved >= 20, 'hint': 'وفّر ٢٠ د.ك'},
        {'key': 'hunter', 'emoji': '🎯', 'name': 'قنّاص الصفقات', 'earned': n >= 5, 'hint': 'أكمل ٥ لمّات'},
        {'key': 'leader', 'emoji': '🤝', 'name': 'زعيم الجماعة', 'earned': ingroup, 'hint': 'ابدأ لمّة جماعية'},
        {'key': 'streak', 'emoji': '🔥', 'name': 'لهيب متواصل', 'earned': ndays >= 3, 'hint': 'لمّة في ٣ أيام'},
        {'key': 'legend', 'emoji': '💎', 'name': 'أسطورة يلو', 'earned': saved >= 100, 'hint': 'وفّر ١٠٠ د.ك'},
        {'key': 'emperor', 'emoji': '🏆', 'name': 'إمبراطور التوفير', 'earned': saved >= 250, 'hint': 'وفّر ٢٥٠ د.ك'},
    ]
    return {'badges': defs, 'earned': sum(1 for d in defs if d['earned']),
            'total': len(defs), 'saved_total': round(saved, 3), 'checkouts': n,
            'currency': _cur_sym()}


def _lb_abandoned(pid=None, sid=None):
    from datetime import timedelta
    if pid is None and sid is None:
        pid, sid = _who()
    dom = _owner_dom(pid, sid)
    since = fields.Datetime.now() - timedelta(days=7)
    last = _act().search(dom + [('action', 'in', ['add', 'start']),
                         ('create_date', '>=', since)], order='create_date desc', limit=1)
    if not last:
        return {'has': False}
    if _act().search_count(dom + [('action', '=', 'checkout'),
                           ('create_date', '>=', last.create_date)]):
        return {'has': False}
    return {'has': True, 'items': last.items or 0,
            'product': last.product_id.name if last.product_id else '',
            'saved_hint': round(last.discount or 0, 3), 'currency': _cur_sym()}


class LammaWeb(http.Controller):
    """Session-based Lamma cart for the web storefront. New JSON routes only —
    nothing here overrides core cart/checkout behaviour."""

    @http.route('/lamma/get', type='json', auth='public', website=True)
    def get(self, **kw):
        # Auto-start: if enabled in settings and the cart already holds enough
        # products, activate the Lamma automatically (seed it from the cart) so
        # the bar appears on its own — no manual "add to Lamma" needed.
        cfg = request.env['uellow.lamma.config'].sudo().get_config()
        if (cfg.auto_start and not (request.session.get('lamma_ids') or [])
                and not request.session.get('lamma_dismissed')):
            try:
                order = request.website.sale_get_order()
                cnt = len(order.order_line.filtered(
                    lambda l: l.product_id and not l.display_type
                    and not getattr(l, 'is_reward_line', False))) if order else 0
                if cnt >= max(2, cfg.min_items):
                    _seed_lamma_from_cart()
            except Exception:
                pass
        return lamma_summary()

    @http.route('/lamma/add', type='json', auth='public', website=True)
    def add(self, product_id, lamma_type=None, variant_id=None, **kw):
        ids = list(request.session.get('lamma_ids') or [])
        pid = int(product_id)
        if pid not in ids:
            ids.append(pid)
        request.session['lamma_ids'] = ids
        _qm = dict(request.session.get('lamma_qty') or {})
        _qm.setdefault(str(pid), 1)
        request.session['lamma_qty'] = _qm
        rm = list(request.session.get('lamma_removed') or [])
        if pid in rm:
            rm.remove(pid)
            request.session['lamma_removed'] = rm
        request.session['lamma_dismissed'] = False
        # remember the chosen colour/variant for this product, if any
        if variant_id:
            vmap = dict(request.session.get('lamma_variants') or {})
            vmap[str(pid)] = int(variant_id)
            request.session['lamma_variants'] = vmap
        started = len(ids) == 1
        if lamma_type in ('normal', 'installment'):
            request.session['lamma_type'] = lamma_type
        if started:
            _seed_lamma_from_cart()  # bring existing cart items into the new Lamma
        s = lamma_summary()
        _log('start' if started else 'add', pid, s)
        return s

    @http.route('/lamma/remove', type='json', auth='public', website=True)
    def remove(self, product_id, **kw):
        ids = list(request.session.get('lamma_ids') or [])
        pid = int(product_id)
        if pid in ids:
            ids.remove(pid)
        request.session['lamma_ids'] = ids
        rm = list(request.session.get('lamma_removed') or [])
        if pid not in rm:
            rm.append(pid)
            request.session['lamma_removed'] = rm
        vmap = dict(request.session.get('lamma_variants') or {})
        if vmap.pop(str(pid), None) is not None:
            request.session['lamma_variants'] = vmap
        _qm = dict(request.session.get('lamma_qty') or {})
        if _qm.pop(str(pid), None) is not None:
            request.session['lamma_qty'] = _qm
        s = lamma_summary()
        _log('remove', pid, s)
        return s

    @http.route('/lamma/type', type='json', auth='public', website=True)
    def set_type(self, lamma_type, **kw):
        request.session['lamma_type'] = 'installment' if lamma_type == 'installment' else 'normal'
        s = lamma_summary()
        _log('type', None, s)
        return s

    @http.route('/lamma/clear', type='json', auth='public', website=True)
    def clear(self, **kw):
        request.session['lamma_ids'] = []
        request.session['lamma_variants'] = {}
        request.session['lamma_qty'] = {}
        request.session['lamma_dismissed'] = True
        s = lamma_summary()
        _log('clear', None, s)
        return s

    @http.route('/lamma/qty', type='json', auth='public', website=True)
    def set_qty(self, product_id, qty, **kw):
        pid = int(product_id)
        ids = request.session.get('lamma_ids') or []
        if pid in ids:
            qm = dict(request.session.get('lamma_qty') or {})
            qm[str(pid)] = max(1, min(int(qty or 1), 99))
            request.session['lamma_qty'] = qm
        return lamma_summary()

    @http.route('/lamma/leaderboard', type='json', auth='public', website=True)
    def leaderboard(self, days=1, **kw):
        return _lb_leaderboard(int(days or 1))

    @http.route('/lamma/savings', type='json', auth='public', website=True)
    def savings(self, **kw):
        return _lb_savings()

    @http.route('/lamma/badges', type='json', auth='public', website=True)
    def badges(self, **kw):
        return _lb_badges()

    @http.route('/lamma/abandoned', type='json', auth='public', website=True)
    def abandoned(self, **kw):
        return _lb_abandoned()

    @http.route('/lamma/checkout', type='json', auth='public', website=True)
    def checkout(self, **kw):
        """Turn the session Lamma into cart lines with the server-recomputed,
        margin-protected discount applied per line (native sale.order.line.discount).
        The price is re-derived here — the client value is never trusted."""
        ids = request.session.get('lamma_ids') or []
        vmap = request.session.get('lamma_variants') or {}
        ltype = request.session.get('lamma_type') or 'normal'
        qmap = request.session.get('lamma_qty') or {}
        cfg = request.env['uellow.lamma.config'].sudo().get_config()
        if not cfg._country_enabled(country_code()):
            return {'error': 'disabled'}
        units, lines = _lines_from_ids(ids, vmap, qmap)
        if len(units) < max(1, cfg.min_items):
            return {'error': 'need_more', 'min_items': cfg.min_items}
        q = cfg.compute_lamma(lines, ltype)
        # Add the chosen variants, mark them as Lamma lines, and apply the
        # margin-safe discount PER LINE (never an order-level coupon: that used
        # to survive product removal → negative totals, and leaked a replayable
        # code). Per-line self-corrects and can never exceed the line's value.
        order = request.website.sale_get_order(force_create=True)
        cfg._strip_lamma_rewards(order, cfg._coupon_program())  # clean any legacy coupon
        for u in units:
            # idempotent: don't bump qty of a product already in the cart on a
            # repeated checkout (that used to silently inflate quantities).
            existing = order.order_line.filtered(
                lambda l: l.product_id.id == u['variant'].id
                and not l.is_reward_line and not l.display_type)
            if not existing:
                order._cart_update(product_id=u['variant'].id, add_qty=u['qty'])
            elif existing[:1].product_uom_qty != u['qty']:
                existing[:1].write({'product_uom_qty': u['qty']})
        for u in units:
            line = order.order_line.filtered(
                lambda l: l.product_id.id == u['variant'].id
                and not l.is_reward_line and not l.display_type)[:1]
            if line:
                line.write({'is_lamma': True, 'lamma_type': ltype})
        order._recompute_lamma()
        _log('checkout', None, {'type': ltype, 'n': q['n'], 'subtotal': q['subtotal'],
                                'saved': q['saved'], '_country': country_code()})
        request.session['lamma_ids'] = []
        request.session['lamma_variants'] = {}
        return {'redirect': '/shop/cart'}
