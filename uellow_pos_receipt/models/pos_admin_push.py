# -*- coding: utf-8 -*-
"""
POS → Admin console pushes (v2.2.10)
====================================
Pings the admins' Uellow app on:
- every new POS sale (order reaches paid/done/invoiced)
- POS session OPEN
- POS session CLOSE (with the session total)

The engine (``mobile.customer.notification.push_admins``) lives in
uellow_mobile_manager — we only call it when it is installed, so this
module keeps zero hard dependency on it.
"""
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)

_PAID_STATES = ('paid', 'done', 'invoiced')


def _engine(env):
    if 'mobile.customer.notification' in env:
        return env['mobile.customer.notification'].sudo()
    return None


def _fmt_amt(amount, currency):
    try:
        return '%s %s' % (('%.{0}f'.format(currency.decimal_places or 3)
                           % (amount or 0.0)), currency.symbol or '')
    except Exception:
        return str(amount or 0)


class PosOrderAdminPush(models.Model):
    _inherit = 'pos.order'

    def _admin_push_sale(self):
        eng = _engine(self.env)
        if not eng:
            return
        for o in self:
            try:
                amt = _fmt_amt(o.amount_total, o.currency_id)
                items = int(sum(l.qty for l in o.lines))
                eng.push_admins(
                    'notify_admin_pos_order',
                    '🧾 POS sale %s — %s' % (o.name or o.pos_reference or '',
                                             amt),
                    '🧾 عملية بيع POS %s — %s' % (
                        o.name or o.pos_reference or '', amt),
                    '%d item(s) · %s' % (items, o.session_id.name or ''),
                    '%d منتج · %s' % (items, o.session_id.name or ''),
                    {'type': 'admin_pos_order', 'id': str(o.id)})
            except Exception:
                _logger.debug('admin pos order push failed', exc_info=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        try:
            records.filtered(
                lambda o: o.state in _PAID_STATES)._admin_push_sale()
        except Exception:
            _logger.debug('pos create admin push failed', exc_info=True)
        return records

    def write(self, vals):
        prev = {}
        if vals.get('state') in _PAID_STATES:
            prev = {o.id: o.state for o in self}
        res = super().write(vals)
        if prev:
            try:
                self.filtered(
                    lambda o: prev.get(o.id) not in _PAID_STATES
                    and o.state in _PAID_STATES)._admin_push_sale()
            except Exception:
                _logger.debug('pos write admin push failed', exc_info=True)
        return res


class PosSessionAdminPush(models.Model):
    _inherit = 'pos.session'

    def write(self, vals):
        watch = vals.get('state')
        prev = {s.id: s.state for s in self} if watch else {}
        res = super().write(vals)
        if not watch:
            return res
        eng = _engine(self.env)
        if not eng:
            return res
        for s in self:
            if prev.get(s.id) == s.state:
                continue   # no transition
            cur = s.currency_id or self.env.company.currency_id
            try:
                if s.state == 'opened':
                    # v2.2.27 — include the OPENING cash float so the admin
                    # sees how much the drawer started with.
                    opening = _fmt_amt(
                        getattr(s, 'cash_register_balance_start', 0.0) or 0.0,
                        cur)
                    eng.push_admins(
                        'notify_admin_pos_session',
                        '🟢 POS opened — %s · float %s' % (s.name or '',
                                                           opening),
                        '🟢 فتح اليومية — %s · رصيد الفتح %s' % (s.name or '',
                                                                 opening),
                        '%s · %s · opening %s' % (s.config_id.name or '',
                                                  s.user_id.name or '',
                                                  opening),
                        '%s · %s · مبلغ الفتح %s' % (s.config_id.name or '',
                                                     s.user_id.name or '',
                                                     opening),
                        {'type': 'admin_pos_session', 'id': str(s.id),
                         'event': 'opened',
                         'opening_amount': getattr(
                             s, 'cash_register_balance_start', 0.0) or 0.0})
                elif s.state == 'closed':
                    orders = self.env['pos.order'].sudo().search_read(
                        [('session_id', '=', s.id)], ['amount_total'])
                    total = _fmt_amt(
                        sum(o['amount_total'] for o in orders), cur)
                    # v2.2.27 — also report the counted CLOSING drawer balance.
                    closing_val = (
                        getattr(s, 'cash_register_balance_end_real', 0.0)
                        or getattr(s, 'cash_register_balance_end', 0.0) or 0.0)
                    closing = _fmt_amt(closing_val, cur)
                    eng.push_admins(
                        'notify_admin_pos_session',
                        '🔴 POS closed — %s · drawer %s' % (s.name or '',
                                                            closing),
                        '🔴 إغلاق اليومية — %s · رصيد الإغلاق %s' % (
                            s.name or '', closing),
                        'Sales: %s · %d order(s) · closing drawer %s' % (
                            total, len(orders), closing),
                        'المبيعات: %s · %d طلب · مبلغ الإغلاق %s' % (
                            total, len(orders), closing),
                        {'type': 'admin_pos_session', 'id': str(s.id),
                         'event': 'closed',
                         'sales_total': sum(
                             o['amount_total'] for o in orders),
                         'closing_amount': closing_val})
            except Exception:
                _logger.debug('admin pos session push failed', exc_info=True)
        return res
