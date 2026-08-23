# -*- coding: utf-8 -*-
"""Group Lamma «شارك لمّتك» — JSON endpoints + public join page.

Every member is identified by a client `token` (persisted browser-side / app
side) and, when logged in, by their partner. All model writes go through sudo
because the flow is public-facing.
"""
import os

from odoo import http
from odoo.http import request
from odoo.addons.uellow_lamma.controllers.main import _resolve_units, country_code


def _partner():
    """Logged-in partner, else None (public user)."""
    try:
        if request.session.uid and not request.env.user._is_public():
            return request.env.user.partner_id
    except Exception:
        pass
    return None


def _token(payload=None, create=False):
    """Client token: explicit payload token wins (app), else the web session
    token (created on demand)."""
    tok = (payload or '').strip() if payload else ''
    if tok:
        return tok
    tok = request.session.get('lamma_group_token')
    if not tok and create:
        import random
        import string
        tok = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))
        request.session['lamma_group_token'] = tok
    return tok


def _find_group(code):
    if not code:
        return request.env['uellow.lamma.group'].sudo().browse()
    return request.env['uellow.lamma.group'].sudo().search(
        [('code', '=', code.strip().upper())], limit=1)


def _my_member(group, token, partner):
    me = group.member_ids.browse()
    if partner:
        me = group.member_ids.filtered(lambda m: m.partner_id.id == partner.id)[:1]
    if not me and token:
        me = group.member_ids.filtered(lambda m: m.token == token)[:1]
    return me


def _refresh_paid(group):
    """Mark members paid once their order is confirmed."""
    for m in group.member_ids:
        if not m.paid and m.sale_order_id and m.sale_order_id.state in ('sale', 'done'):
            m.paid = True
            m.paid_amount = m.sale_order_id.amount_total


def _esc(t):
    return (t or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _group_pct(g):
    try:
        return int(round((g._quote() or {}).get('discount_pct') or 0))
    except Exception:
        return 0


def _inject_og(request, g, html):
    """Inject dynamic Open-Graph meta so WhatsApp/social render a rich card."""
    try:
        base = (request.httprequest.host_url or '').rstrip('/').replace('http://', 'https://')
        pct = _group_pct(g)
        host = ((g.host_partner_id.name or '').split(' ')[0]) if g.host_partner_id else 'يلو'
        title = ('🧺 انضم للمّة %s ووفّر %d٪!' % (host, pct)) if pct else ('🧺 انضم للمّة %s على يلو' % host)
        desc = 'خصم جماعي محمي بربح مضمون — كل ما زاد الأعضاء زاد التوفير. انضم بكود %s 🐝' % g.code
        img = '%s/lamma/g/%s/card.png' % (base, g.code)
        url = '%s/lamma/g/%s' % (base, g.code)
        meta = ('<meta property="og:type" content="website"/>'
                '<meta property="og:site_name" content="Uellow"/>'
                '<meta property="og:title" content="%s"/>'
                '<meta property="og:description" content="%s"/>'
                '<meta property="og:image" content="%s"/>'
                '<meta property="og:image:width" content="1200"/>'
                '<meta property="og:image:height" content="630"/>'
                '<meta property="og:url" content="%s"/>'
                '<meta name="twitter:card" content="summary_large_image"/>'
                '<meta name="twitter:title" content="%s"/>'
                '<meta name="twitter:image" content="%s"/>') % (
            _esc(title), _esc(desc), img, url, _esc(title), img)
        if '</head>' in html:
            return html.replace('</head>', meta + '</head>', 1)
        return meta + html
    except Exception:
        return html


def _render_card(env, code, pct, saved, members, items):
    import io as _io
    import base64 as _b64
    from PIL import Image, ImageDraw, ImageFont
    W, H = 1200, 630
    im = Image.new('RGB', (W, H), (245, 195, 32))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / float(H)
        d.line([(0, y), (W, y)],
               fill=(int(245 + 10 * t), int(195 - 37 * t), int(32 + 37 * t)))
    dark = (65, 36, 2)
    brown = (90, 60, 10)
    TB = '/usr/share/fonts/truetype/tajawal/Tajawal-Black.ttf'
    TR = '/usr/share/fonts/truetype/tajawal/Tajawal-Bold.ttf'

    def F(sz, black=True):
        try:
            return ImageFont.truetype(TB if black else TR, sz)
        except Exception:
            return ImageFont.load_default()

    # basket glyph (top-right), drawn (no emoji font needed)
    d.arc((980, 78, 1092, 168), 180, 360, fill=dark, width=16)
    d.polygon([(956, 168), (1116, 168), (1092, 268), (980, 268)], fill=dark)
    d.rounded_rectangle((944, 150, 1128, 180), radius=14, fill=(50, 28, 2))
    # logo (top-left)
    _logo_ok = False
    try:
        lb = env['res.company'].sudo().browse(1).logo or env['website'].sudo().browse(1).logo
        if lb:
            lg = Image.open(_io.BytesIO(_b64.b64decode(lb))).convert('RGBA')
            lg.thumbnail((300, 96))
            im.paste(lg, (70, 62), lg)
            _logo_ok = True
    except Exception:
        _logo_ok = False
    if not _logo_ok:
        d.text((70, 60), 'uellow', font=F(88), fill=dark)
    # big discount
    d.text((66, 176), '%d%%' % pct, font=F(300), fill=dark)
    d.text((78, 486), 'GROUP  LAMMA', font=F(60), fill=brown)
    # code chip
    d.rounded_rectangle((78, 556, 78 + 380, 556 + 60), radius=18, fill=dark)
    d.text((104, 566), 'JOIN   %s' % code, font=F(40), fill=(245, 195, 32))
    # right column: saved + counts
    d.text((760, 300), '%.1f KD' % (saved or 0.0), font=F(96), fill=dark)
    d.text((766, 410), 'saved together', font=F(38, False), fill=brown)
    d.text((766, 470), '%d items   %d members' % (items, members), font=F(36, False), fill=brown)
    buf = _io.BytesIO()
    im.save(buf, 'PNG')
    return buf.getvalue()


class LammaGroupCtrl(http.Controller):

    # -------------------------------------------------- create
    @http.route('/lamma/group/create', type='json', auth='public', website=True)
    def create(self, lamma_type=None, name=None, token=None, seed_session=True, **kw):
        Group = request.env['uellow.lamma.group'].sudo()
        partner = _partner()
        tok = _token(token, create=True)
        host_name = name or (partner.name if partner else None)
        g = Group.create_group(host_token=tok, host_name=host_name, partner=partner,
                               lamma_type=(lamma_type or 'normal'))
        host = g.member_ids.filtered('is_host')[:1]
        # seed the host's items from the current session Lamma (if any)
        if seed_session and host:
            ids = request.session.get('lamma_ids') or []
            vmap = request.session.get('lamma_variants') or {}
            self._add_units(g, host, ids, vmap)
        request.session['lamma_group_code'] = g.code
        return g.to_dict(token=tok, partner=partner)

    # -------------------------------------------------- state
    @http.route('/lamma/group/state', type='json', auth='public', website=True)
    def state(self, code=None, token=None, **kw):
        g = _find_group(code or request.session.get('lamma_group_code'))
        if not g:
            return {'error': 'not_found'}
        _refresh_paid(g)
        return g.to_dict(token=_token(token), partner=_partner())

    # -------------------------------------------------- join
    @http.route('/lamma/group/join', type='json', auth='public', website=True)
    def join(self, code=None, name=None, token=None, **kw):
        g = _find_group(code)
        if not g:
            return {'error': 'not_found'}
        if g.state not in ('open',):
            return {'error': g.state}
        partner = _partner()
        tok = _token(token, create=True)
        me = g._get_or_create_member(token=tok, name=name, partner=partner, is_host=False)
        g._notify('join', actor=me)
        request.session['lamma_group_code'] = g.code
        return g.to_dict(token=tok, partner=partner)

    # -------------------------------------------------- add / remove
    @http.route('/lamma/group/add', type='json', auth='public', website=True)
    def add(self, code=None, product_id=None, variant_id=None, token=None, **kw):
        g = _find_group(code or request.session.get('lamma_group_code'))
        if not g or g.state != 'open':
            return {'error': 'closed'}
        partner = _partner()
        tok = _token(token, create=True)
        me = _my_member(g, tok, partner)
        if not me:
            me = g._get_or_create_member(token=tok, partner=partner)
        vmap = {str(int(product_id)): int(variant_id)} if variant_id else {}
        self._add_units(g, me, [product_id], vmap)
        g._notify('add', actor=me)
        return g.to_dict(token=tok, partner=partner)

    @http.route('/lamma/group/remove', type='json', auth='public', website=True)
    def remove(self, code=None, product_id=None, token=None, **kw):
        g = _find_group(code or request.session.get('lamma_group_code'))
        if not g or g.state != 'open':
            return {'error': 'closed'}
        partner = _partner()
        tok = _token(token)
        me = _my_member(g, tok, partner)
        if me and product_id:
            line = me.line_ids.filtered(lambda l: l.product_tmpl_id.id == int(product_id))[:1]
            if line:
                line.unlink()
        return g.to_dict(token=tok, partner=partner)

    @http.route('/lamma/group/import_session', type='json', auth='public', website=True)
    def import_session(self, code=None, token=None, **kw):
        """Pull the member's current session Lamma items into the group — the
        web 'add my products' shortcut (browse /shop, build a Lamma, import)."""
        g = _find_group(code or request.session.get('lamma_group_code'))
        if not g or g.state != 'open':
            return {'error': 'closed'}
        partner = _partner()
        tok = _token(token, create=True)
        me = _my_member(g, tok, partner) or g._get_or_create_member(token=tok, partner=partner)
        ids = request.session.get('lamma_ids') or []
        vmap = request.session.get('lamma_variants') or {}
        self._add_units(g, me, ids, vmap)
        request.session['lamma_ids'] = []
        request.session['lamma_variants'] = {}
        return g.to_dict(token=tok, partner=partner)

    def _add_units(self, group, member, ids, vmap):
        """Resolve template ids → validated units and add any not already in the
        member's list (dedup by template)."""
        units = _resolve_units(ids, vmap)
        have = set(member.line_ids.mapped('product_tmpl_id').ids)
        Line = request.env['uellow.lamma.group.line'].sudo()
        for u in units:
            t = u['tmpl']
            if t.id in have:
                continue
            Line.create({
                'group_id': group.id,
                'member_id': member.id,
                'product_tmpl_id': t.id,
                'product_id': u['variant'].id,
            })
            have.add(t.id)

    # -------------------------------------------------- lock (host)
    @http.route('/lamma/group/lock', type='json', auth='public', website=True)
    def lock(self, code=None, token=None, **kw):
        g = _find_group(code or request.session.get('lamma_group_code'))
        if not g:
            return {'error': 'not_found'}
        me = _my_member(g, _token(token), _partner())
        if not me or not me.is_host:
            return {'error': 'not_host'}
        if g.state == 'open':
            g.state = 'locked'
            g._notify('lock', actor=me)
        return g.to_dict(token=_token(token), partner=_partner())

    # -------------------------------------------------- pay my share
    @http.route('/lamma/group/pay', type='json', auth='public', website=True)
    def pay(self, code=None, token=None, **kw):
        g = _find_group(code or request.session.get('lamma_group_code'))
        if not g:
            return {'error': 'not_found'}
        partner = _partner()
        tok = _token(token)
        me = _my_member(g, tok, partner)
        if not me or not me.line_ids:
            return {'error': 'empty'}
        discs = g._member_line_discounts(me)  # {variant_id: pct}, headroom-spread
        order = request.website.sale_get_order(force_create=True)
        for l in me.line_ids:
            v = l.product_id or l.product_tmpl_id.product_variant_id
            if not v:
                continue
            existing = order.order_line.filtered(
                lambda ol: ol.product_id.id == v.id and not ol.display_type
                and not ol.is_reward_line)
            if not existing:
                order._cart_update(product_id=v.id, add_qty=1)
        for l in me.line_ids:
            v = l.product_id or l.product_tmpl_id.product_variant_id
            line = order.order_line.filtered(
                lambda ol: ol.product_id.id == v.id and not ol.display_type
                and not ol.is_reward_line)[:1]
            if line:
                line.write({'discount': discs.get(v.id, 0.0), 'is_lamma': False})
        me.sale_order_id = order.id
        return {'redirect': '/shop/cart'}

    # -------------------------------------------------- public join page
    @http.route('/lamma/g/<code>', type='http', auth='public', website=True, sitemap=False)
    def landing(self, code, **kw):
        g = _find_group(code)
        if not g:
            return request.redirect('/shop')
        request.session['lamma_group_code'] = g.code
        path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', 'static', 'src', 'group.html'))
        try:
            with open(path, 'r', encoding='utf-8') as f:
                html = f.read()
        except Exception:
            return request.redirect('/shop')
        html = html.replace('__CODE__', g.code)
        html = _inject_og(request, g, html)
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ])

    @http.route('/lamma/g/<code>/card.png', type='http', auth='public',
                website=True, sitemap=False)
    def share_card(self, code, **kw):
        g = _find_group(code)
        if not g:
            return request.not_found()
        try:
            q = g._quote() or {}
        except Exception:
            q = {}
        pct = int(round(q.get('discount_pct') or 0))
        saved = q.get('saved') or g.saved_total or 0.0
        try:
            png = _render_card(request.env, g.code, pct, saved,
                               g.member_count or 1, g.item_count or 0)
        except Exception:
            return request.redirect('/web/image/website/1/logo')
        return request.make_response(png, headers=[
            ('Content-Type', 'image/png'),
            ('Cache-Control', 'public, max-age=600'),
        ])
