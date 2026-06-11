# -*- coding: utf-8 -*-
"""
POS reporting helpers (v2.2.41)
===============================
- pos.order: a one-line "Payment Type" summary (Cash / KNet / card …) so the
  payment used is visible directly in every POS operation list/form.
- pos.session: a close-day summary (order count, cash total, card total, …)
  shown at the TOP of the session record so closing reads at a glance.
"""
from odoo import api, fields, models


class PosOrderPaymentType(models.Model):
    _inherit = 'pos.order'

    uellow_payment_type = fields.Char(
        string='Payment Type', compute='_compute_uellow_payment_type',
        help='Payment method(s) used on this order (Cash / KNet / card …).')

    @api.depends('payment_ids', 'payment_ids.payment_method_id',
                 'payment_ids.amount')
    def _compute_uellow_payment_type(self):
        for order in self:
            names = []
            for p in order.payment_ids:
                nm = p.payment_method_id.name or ''
                if nm and nm not in names:
                    names.append(nm)
            order.uellow_payment_type = ' + '.join(names)


class PosSessionCloseReport(models.Model):
    _inherit = 'pos.session'

    uellow_order_count = fields.Integer(
        string='Orders', compute='_compute_uellow_summary')
    uellow_total_sales = fields.Monetary(
        string='Total Sales', compute='_compute_uellow_summary',
        currency_field='currency_id')
    uellow_total_cash = fields.Monetary(
        string='Cash Collected', compute='_compute_uellow_summary',
        currency_field='currency_id')
    uellow_total_card = fields.Monetary(
        string='Card / Online', compute='_compute_uellow_summary',
        currency_field='currency_id')
    uellow_avg_basket = fields.Monetary(
        string='Avg. Basket', compute='_compute_uellow_summary',
        currency_field='currency_id')
    uellow_refund_total = fields.Monetary(
        string='Refunds', compute='_compute_uellow_summary',
        currency_field='currency_id')
    uellow_payment_breakdown = fields.Text(
        string='Payment Breakdown', compute='_compute_uellow_summary')

    @api.depends('order_ids', 'order_ids.amount_total',
                 'order_ids.payment_ids.amount',
                 'order_ids.payment_ids.payment_method_id')
    def _compute_uellow_summary(self):
        for s in self:
            orders = s.order_ids
            cash = card = refunds = 0.0
            by_method = {}
            for o in orders:
                if (o.amount_total or 0.0) < 0:
                    refunds += o.amount_total
                for p in o.payment_ids:
                    pm = p.payment_method_id
                    by_method.setdefault(pm.name or '—', 0.0)
                    by_method[pm.name or '—'] += p.amount
                    if pm.is_cash_count:
                        cash += p.amount
                    else:
                        card += p.amount
            total = sum(orders.mapped('amount_total'))
            n = len(orders)
            s.uellow_order_count = n
            s.uellow_total_sales = total
            s.uellow_total_cash = cash
            s.uellow_total_card = card
            s.uellow_refund_total = refunds
            s.uellow_avg_basket = (total / n) if n else 0.0
            s.uellow_payment_breakdown = '\n'.join(
                '• %s: %.3f' % (k, v) for k, v in sorted(
                    by_method.items(), key=lambda kv: -kv[1])) or '—'
