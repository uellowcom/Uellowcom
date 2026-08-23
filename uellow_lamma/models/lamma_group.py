# -*- coding: utf-8 -*-
"""Group Lamma — «شارك لمّتك» collaborative buying.

Several people build ONE Lamma together; the margin-protected discount is
computed on the COMBINED basket (so the more everyone adds, the bigger the
discount for all) and then split back to each member proportionally to their
own subtotal — every member pays only their fair, discounted share.

Reuses the pricing engine on `uellow.lamma.config.compute_lamma`.
Identity works with or without login: each member carries a random `token`
the client stores; a logged-in member is also linked to their partner.
"""
import random
import string
from datetime import datetime, timedelta

from odoo import models, fields, api


def _gen_code():
    """Short, human-shareable, ambiguity-free code, e.g. YL-7K2Q."""
    alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'  # no O/0/I/1/L
    return 'YL-' + ''.join(random.choice(alphabet) for _ in range(4))


def _gen_token():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(32))


class LammaGroup(models.Model):
    _name = 'uellow.lamma.group'
    _description = 'Group Lamma (شارك لمّتك)'
    _order = 'create_date desc'

    code = fields.Char('Share code', index=True, copy=False, readonly=True)
    name = fields.Char('Name', default='لمّة جماعية')
    host_partner_id = fields.Many2one('res.partner', string='Host', ondelete='set null')
    website_id = fields.Many2one('website', ondelete='cascade')
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)
    lamma_type = fields.Selection(
        [('normal', 'Normal'), ('installment', 'Installment')],
        default='normal', string='Type')
    state = fields.Selection(
        [('open', 'Open'), ('locked', 'Locked'), ('done', 'Done'), ('expired', 'Expired')],
        default='open', index=True)
    expiry = fields.Datetime('Expires at')
    member_ids = fields.One2many('uellow.lamma.group.member', 'group_id', string='Members')
    line_ids = fields.One2many('uellow.lamma.group.line', 'group_id', string='Items')

    member_count = fields.Integer(compute='_compute_stats', store=False)
    item_count = fields.Integer(compute='_compute_stats', store=False)
    saved_total = fields.Float(compute='_compute_stats', store=False)

    _sql_constraints = [('code_uniq', 'unique(code)', 'Lamma group code must be unique.')]

    def _compute_stats(self):
        for g in self:
            g.member_count = len(g.member_ids)
            g.item_count = len(g.line_ids)
            try:
                g.saved_total = g._quote().get('saved', 0.0)
            except Exception:
                g.saved_total = 0.0

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    @api.model
    def create_group(self, host_token=None, host_name=None, partner=None,
                     lamma_type='normal', days=3):
        # Anti-spam: a single host token can't hold an unbounded number of open
        # groups. Past the cap, reuse their newest open group instead of minting
        # another (a public endpoint must not be a DB-fill vector).
        if host_token:
            Member = self.env['uellow.lamma.group.member'].sudo()
            open_hosted = Member.search(
                [('token', '=', host_token), ('is_host', '=', True),
                 ('group_id.state', '=', 'open')])
            if len(open_hosted) >= 8:
                newest = open_hosted.sorted(lambda m: m.group_id.id)[-1].group_id
                return newest
        code = _gen_code()
        while self.sudo().search_count([('code', '=', code)]):
            code = _gen_code()
        website = getattr(self.env, 'website', None) or self.env['website'].sudo().search([], limit=1)
        g = self.sudo().create({
            'code': code,
            'name': ('لمّة %s' % host_name) if host_name else 'لمّة جماعية',
            'host_partner_id': partner.id if partner else False,
            'website_id': website.id if website else False,
            'company_id': self.env.company.id,
            'lamma_type': lamma_type if lamma_type in ('normal', 'installment') else 'normal',
            'expiry': fields.Datetime.now() + timedelta(days=max(1, days)),
        })
        g._get_or_create_member(token=host_token, name=host_name, partner=partner, is_host=True)
        return g

    def _get_or_create_member(self, token=None, name=None, partner=None, is_host=False):
        """Find this member (by partner, else by token) or create them."""
        self.ensure_one()
        M = self.env['uellow.lamma.group.member'].sudo()
        member = M.browse()
        if partner:
            member = M.search([('group_id', '=', self.id), ('partner_id', '=', partner.id)], limit=1)
        if not member and token:
            member = M.search([('group_id', '=', self.id), ('token', '=', token)], limit=1)
        if member:
            vals = {}
            if partner and not member.partner_id:
                vals['partner_id'] = partner.id
            if name and not member.name:
                vals['name'] = name
            if vals:
                member.write(vals)
            return member
        return M.create({
            'group_id': self.id,
            'token': token or _gen_token(),
            'partner_id': partner.id if partner else False,
            'name': name or (partner.name if partner else 'ضيف'),
            'is_host': is_host,
        })

    def _check_expiry(self):
        for g in self:
            if g.state == 'open' and g.expiry and g.expiry < fields.Datetime.now():
                g.state = 'expired'

    @api.model
    def _cron_expire(self):
        now = fields.Datetime.now()
        self.sudo().search([('state', '=', 'open'), ('expiry', '<', now)]).write({'state': 'expired'})

    # ------------------------------------------------------------------
    # pricing — combined quote + fair per-member split
    # ------------------------------------------------------------------
    def _engine_lines(self, lines=None):
        """Resolve group lines → engine dicts [{price, cost, member_id, line}]."""
        self.ensure_one()
        lines = lines if lines is not None else self.line_ids
        cid = self.company_id.id or self.env.company.id
        wid = self.website_id.id
        out = []
        for l in lines:
            v = l.product_id
            t = l.product_tmpl_id
            if not v or not t or not t.sale_ok:
                continue
            if t.company_id and t.company_id.id != cid:      # never a World/company-7 leak
                continue
            if wid and t.website_id and t.website_id.id != wid:
                continue
            out.append({
                'price': v.list_price or t.list_price or 0.0,
                'cost': v.standard_price or t.standard_price or 0.0,
                'member_id': l.member_id.id,
                'line': l,
            })
        return out

    def _quote(self):
        """Combined margin-protected quote for the whole group + per-member split."""
        self.ensure_one()
        cfg = self.env['uellow.lamma.config'].sudo().get_config()
        eng = self._engine_lines()
        q = cfg.compute_lamma([{'price': e['price'], 'cost': e['cost']} for e in eng],
                              self.lamma_type)
        subtotal = q.get('subtotal') or 0.0
        saved = q.get('saved') or 0.0
        # Split the safe total discount by each member's MARGIN HEADROOM (mirrors
        # the solo engine), NOT by raw subtotal — otherwise a thin-margin member
        # in a high-headroom group could be handed a discount their own items
        # can't bear and their share would fall below cost. Headroom-weighting
        # guarantees each member's slice stays at/above their own floor margin.
        is_inst = self.lamma_type == 'installment'
        fm = min(cfg.min_margin_pct + (cfg.installment_extra_margin if is_inst else 0.0), 99.0)

        def _floor_price(c):
            return c / (1 - fm / 100.0) if fm < 100 else float('inf')

        def _headroom(e):
            if not cfg.discount_zero_cost and (e['cost'] or 0.0) <= 0.0:
                return 0.0
            return max(0.0, e['price'] - _floor_price(e['cost']))

        per_member = {}
        for e in eng:
            m = per_member.setdefault(e['member_id'], {'subtotal': 0.0, 'n': 0, 'head': 0.0})
            m['subtotal'] += e['price']
            m['n'] += 1
            m['head'] += _headroom(e)
        total_head = sum(m['head'] for m in per_member.values())
        splits = {}
        for mid, m in per_member.items():
            if saved <= 0:
                share_saved = 0.0
            elif total_head > 1e-9:
                share_saved = min(saved * (m['head'] / total_head), m['head'])
            elif subtotal > 0:
                share_saved = saved * (m['subtotal'] / subtotal)
            else:
                share_saved = 0.0
            pays = round(m['subtotal'] - share_saved, 3)
            splits[mid] = {
                'subtotal': round(m['subtotal'], 3),
                'saved': round(m['subtotal'] - pays, 3),
                'pays': pays,
                'n': m['n'],
            }
        # Reconcile the group header to the sum of what members actually pay
        # (each share is rounded independently, so the displayed group total must
        # equal their sum to the fil — no phantom 0.001 discrepancy).
        if splits:
            q['pays'] = round(sum(s['pays'] for s in splits.values()), 3)
            q['saved'] = round(subtotal - q['pays'], 3)
            q['discount_pct'] = round((q['saved'] / subtotal * 100.0) if subtotal > 0 else 0.0, 2)
        q['splits'] = splits
        return q

    def _member_split(self, member):
        q = self._quote()
        return q.get('splits', {}).get(member.id,
                                       {'subtotal': 0.0, 'saved': 0.0, 'pays': 0.0, 'n': 0})

    def _member_line_discounts(self, member):
        """Per-line discount % that realises exactly the member's share, spread
        across their own lines by MARGIN HEADROOM (mirrors _recompute_lamma) so
        no single line — even in a mixed-margin basket — drops below its floor.
        Returns {product_variant_id: discount_pct}."""
        self.ensure_one()
        cfg = self.env['uellow.lamma.config'].sudo().get_config()
        split = self._member_split(member)
        saved = round(split['subtotal'] - split['pays'], 3)
        is_inst = self.lamma_type == 'installment'
        fm = min(cfg.min_margin_pct + (cfg.installment_extra_margin if is_inst else 0.0), 99.0)

        def _floor_price(c):
            return c / (1 - fm / 100.0) if fm < 100 else float('inf')

        rows = []
        for l in member.line_ids:
            v = l.product_id or l.product_tmpl_id.product_variant_id
            if not v:
                continue
            price = v.list_price or 0.0
            cost = v.standard_price or 0.0
            head = (max(0.0, price - _floor_price(cost))
                    if (cfg.discount_zero_cost or cost > 0) else 0.0)
            rows.append({'vid': v.id, 'price': price, 'head': head})
        total_h = sum(r['head'] for r in rows)
        out = {}
        for r in rows:
            if saved <= 0 or total_h <= 0 or r['price'] <= 0 or r['head'] <= 0:
                disc = 0.0
            else:
                share = saved * (r['head'] / total_h)
                disc = min(100.0, share / r['price'] * 100.0)
            out[r['vid']] = round(disc, 4)
        return out

    def _share_url(self):
        base = (self.website_id and self.website_id.domain or '').rstrip('/')
        return (base + '/lamma/g/' + self.code) if base else ('/lamma/g/' + self.code)

    def _notify(self, kind, actor=None):
        """Push a group event to the members it concerns (those linked to a
        partner — guests without an account simply aren't targeted)."""
        self.ensure_one()
        if 'mobile.notification' not in self.env:
            return
        Notif = self.env['mobile.notification'].sudo()
        actor_name = (actor.name if actor else 'أحد الأعضاء')
        data = {'type': 'lamma_group', 'code': self.code, 'url': self._share_url()}
        title = 'لمّة يلو 🧺'
        if kind == 'join':
            targets = self.member_ids.filtered(lambda m: m.is_host and m != actor)
            msg = '%s انضم للمّتك «%s» 🎉' % (actor_name, self.name or 'الجماعية')
        elif kind == 'add':
            # notify the HOST only (not every member on every product) to avoid
            # a burst of pushes while friends build their baskets.
            targets = self.member_ids.filtered(lambda m: m.is_host and m != actor)
            msg = '%s أضاف منتجًا للّمة — اقتربتم من خصم أكبر 🔥' % actor_name
        elif kind == 'lock':
            targets = self.member_ids.filtered(lambda m: not m.is_host)
            msg = 'لمّتكم «%s» جاهزة — ادفع نصيبك 💳' % (self.name or 'الجماعية')
        else:
            return
        for m in targets:
            if not m.partner_id:
                continue
            try:
                Notif.create_notification(m.partner_id.id, title, msg,
                                          notification_type='info', data=data,
                                          send_push=True)
            except Exception:
                pass

    def _maybe_close(self):
        """Close the group once every member who added items has paid."""
        for g in self:
            if g.state != 'locked':
                continue
            payers = g.member_ids.filtered(lambda m: m.line_ids)
            if payers and all(m.paid for m in payers):
                g.state = 'done'

    # ------------------------------------------------------------------
    # serialisation for web/app
    # ------------------------------------------------------------------
    def to_dict(self, token=None, partner=None):
        self.ensure_one()
        self._check_expiry()
        self._maybe_close()
        cfg = self.env['uellow.lamma.config'].sudo().get_config()
        q = self._quote()
        base = (self.website_id and self.website_id.domain or '').rstrip('/')
        me = None
        if partner:
            me = self.member_ids.filtered(lambda m: m.partner_id.id == partner.id)[:1]
        if not me and token:
            me = self.member_ids.filtered(lambda m: m.token == token)[:1]
        symbol = (self.company_id.currency_id.symbol
                  or self.company_id.currency_id.name or 'KD')
        members = []
        for m in self.member_ids.sorted(lambda r: (not r.is_host, r.id)):
            sp = q.get('splits', {}).get(m.id, {})
            members.append({
                'id': m.id,
                'name': m.name or 'ضيف',
                'is_host': m.is_host,
                'is_me': bool(me and m.id == me.id),
                'paid': m.paid,
                'n': sp.get('n', 0),
                'subtotal': sp.get('subtotal', 0.0),
                'pays': sp.get('pays', 0.0),
                'saved': sp.get('saved', 0.0),
                'items': [it._item_dict() for it in m.line_ids],
                'initial': (m.name or 'ض')[:1],
            })
        n = q.get('n', 0)
        # progress: next tier target (by count) + free-shipping target
        next_tier = None
        for t in cfg.tier_ids.sorted(lambda r: r.min_qty):
            if n < t.min_qty:
                next_tier = {'need': t.min_qty - n, 'at': t.min_qty, 'pct': t.discount_pct}
                break
        fsi = cfg.free_shipping_items or 0
        my = (q.get('splits', {}).get(me.id) if me else None) or {}
        return {
            'code': self.code,
            'name': self.name,
            'state': self.state,
            'lamma_type': self.lamma_type,
            'expiry': self.expiry and fields.Datetime.to_string(self.expiry),
            'host': (self.host_partner_id.name if self.host_partner_id else
                     (self.member_ids.filtered('is_host')[:1].name or 'المضيف')),
            'currency': symbol,
            'n': n,
            'subtotal': q.get('subtotal', 0.0),
            'pays': q.get('pays', 0.0),
            'saved': q.get('saved', 0.0),
            'discount_pct': q.get('discount_pct', 0.0),
            'free_shipping': q.get('free_shipping', False),
            'free_shipping_items': fsi,
            'next_tier': next_tier,
            'members': members,
            'member_count': len(members),
            'me': ({'id': me.id, 'name': me.name, 'is_host': me.is_host,
                    'token': me.token, 'paid': me.paid,
                    'pays': my.get('pays', 0.0), 'saved': my.get('saved', 0.0),
                    'n': my.get('n', 0)} if me else None),
            'min_items': cfg.min_items,
            'max_discount_pct': cfg.max_discount_pct,
            'installment_enabled': cfg.installment_enabled,
            'share_url': (base + '/lamma/g/' + self.code) if base else ('/lamma/g/' + self.code),
        }


class LammaGroupMember(models.Model):
    _name = 'uellow.lamma.group.member'
    _description = 'Group Lamma Member'
    _order = 'is_host desc, id'

    group_id = fields.Many2one('uellow.lamma.group', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', ondelete='set null')
    token = fields.Char('Client token', index=True, copy=False)
    name = fields.Char('Name', default='ضيف')
    is_host = fields.Boolean('Host', default=False)
    paid = fields.Boolean('Paid', default=False)
    paid_amount = fields.Float('Paid amount')
    sale_order_id = fields.Many2one('sale.order', ondelete='set null')
    line_ids = fields.One2many('uellow.lamma.group.line', 'member_id', string='Items')


class LammaGroupLine(models.Model):
    _name = 'uellow.lamma.group.line'
    _description = 'Group Lamma Item'

    group_id = fields.Many2one('uellow.lamma.group', required=True, ondelete='cascade', index=True)
    member_id = fields.Many2one('uellow.lamma.group.member', required=True, ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one('product.template', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', ondelete='cascade')

    def _item_dict(self):
        self.ensure_one()
        t, v = self.product_tmpl_id, self.product_id
        multi = t.product_variant_count > 1
        return {
            'id': t.id,
            'variant_id': v.id if v else None,
            'name': (v.display_name if (multi and v) else t.name) or '',
            'price': round((v.list_price if v else t.list_price) or 0.0, 3),
            'image': ('/web/image/product.product/%s/image_256' % v.id) if (multi and v)
                     else ('/web/image/product.template/%s/image_256' % t.id),
            'url': t.website_url or ('/shop/%s' % t.id),
        }
