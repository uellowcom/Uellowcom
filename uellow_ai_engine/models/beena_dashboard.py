# -*- coding: utf-8 -*-
"""Beena Dashboard: a single-record model exposing KPI metrics as computed fields."""

from odoo import models, fields, api
from odoo.tools import html_escape
from datetime import datetime, timedelta


class BeenaDashboard(models.Model):
    _name = 'beena.dashboard'
    _description = 'Beena Dashboard'

    name = fields.Char(default='Beena Dashboard', readonly=True)

    # Cost KPIs (USD)
    cost_today = fields.Float(string='Cost Today', compute='_compute_kpis', digits=(12, 4))
    cost_month = fields.Float(string='Cost This Month', compute='_compute_kpis', digits=(12, 4))
    cost_total = fields.Float(string='Total Cost', compute='_compute_kpis', digits=(12, 4))

    # Volume KPIs
    conversations_total = fields.Integer(string='Total Conversations', compute='_compute_kpis')
    conversations_today = fields.Integer(string='Conversations Today', compute='_compute_kpis')
    messages_total = fields.Integer(string='Total Messages', compute='_compute_kpis')

    # Efficiency KPIs
    claude_calls = fields.Integer(string='Claude Calls', compute='_compute_kpis')
    cache_hits = fields.Integer(string='Cache Hits', compute='_compute_kpis')
    cache_hit_rate = fields.Float(string='Cache Hit Rate (%)', compute='_compute_kpis', digits=(5, 1))

    # Tokens
    tokens_total = fields.Integer(string='Total Tokens', compute='_compute_kpis')

    # Orders via Beena
    beena_orders = fields.Integer(string='Orders via Beena', compute='_compute_kpis')
    beena_orders_value = fields.Float(string='Beena Orders Value', compute='_compute_kpis', digits=(12, 3))

    # Top lists (summary text)
    top_products = fields.Html(string='Top Products by Conversations', compute='_compute_kpis', sanitize=False)
    top_questions = fields.Html(string='Most Frequent Questions', compute='_compute_kpis', sanitize=False)

    # Sentiment (from session last_state)
    sentiment_summary = fields.Html(string='Sentiment Breakdown', compute='_compute_kpis', sanitize=False)

    def _compute_kpis(self):
        Msg = self.env['beena.message'].sudo()
        Conv = self.env['beena.conversation'].sudo()

        now = fields.Datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def _msum(field, domain=None):
            g = Msg.read_group(domain or [], [field + ':sum'], [])
            return (g[0].get(field) or 0) if g else 0

        for rec in self:
            rec.cost_total = _msum('cost')
            rec.cost_today = _msum('cost', [('create_date', '>=', today_start)])
            rec.cost_month = _msum('cost', [('create_date', '>=', month_start)])

            rec.conversations_total = Conv.search_count([])
            rec.conversations_today = Conv.search_count([('create_date', '>=', today_start)])
            rec.messages_total = Msg.search_count([])

            claude = Msg.search_count([('role', '=', 'assistant'), ('source', '=', 'claude')])
            cache = Msg.search_count([('role', '=', 'assistant'), ('source', '=', 'cache')])
            rec.claude_calls = claude
            rec.cache_hits = cache
            total_replies = claude + cache
            rec.cache_hit_rate = round((cache / total_replies) * 100, 1) if total_replies else 0.0

            rec.tokens_total = int(_msum('input_tokens') + _msum('output_tokens'))

            # ── Orders via Beena (tagged origin='Beena AI') ──
            Order = self.env['sale.order'].sudo()
            beena_orders = Order.search(['|', ('origin', 'like', 'Beena'), ('is_beena_order', '=', True)])
            rec.beena_orders = len(beena_orders)
            rec.beena_orders_value = sum(beena_orders.mapped('amount_total'))

            # ── Top products by conversation count ──
            prod_counts = {}
            for c in Conv.search([('product_id', '!=', False)]):
                pid = c.product_id
                prod_counts[pid] = prod_counts.get(pid, 0) + 1
            top_prod = sorted(prod_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
            if top_prod:
                rows = ''.join(
                    '<tr><td style="padding:4px 12px 4px 0">%s</td>'
                    '<td style="text-align:right;font-weight:500">%d</td></tr>' % (html_escape(p.name or ''), n)
                    for p, n in top_prod
                )
                rec.top_products = '<table style="width:100%%">%s</table>' % rows
            else:
                rec.top_products = '<span style="color:#888">No data yet</span>'

            # ── Most frequent questions (from answer cache) ──
            Cache = self.env['beena.qa.cache'].sudo()
            top_q = Cache.search([('hit_count', '>', 0)], order='hit_count desc', limit=8)
            if top_q:
                rows = ''.join(
                    '<tr><td style="padding:4px 12px 4px 0">%s</td>'
                    '<td style="text-align:right;font-weight:500">%d</td></tr>' % (html_escape(q.question or ''), q.hit_count)
                    for q in top_q
                )
                rec.top_questions = '<table style="width:100%%">%s</table>' % rows
            else:
                rec.top_questions = '<span style="color:#888">No repeated questions yet</span>'

            # ── Sentiment breakdown (from session last_state) ──
            Sess = self.env['ai.chat.session'].sudo()
            sess_all = Sess.search([])
            state_labels = {
                'happy': ('Happy', '#2BA574'),
                'excited': ('Excited', '#EF9F27'),
                'talking': ('Neutral', '#378ADD'),
                'thinking': ('Thinking', '#888888'),
                'sad': ('Unhappy', '#E24B4A'),
            }
            counts = {}
            for s in sess_all:
                st = s.last_state or 'talking'
                counts[st] = counts.get(st, 0) + 1
            total_s = sum(counts.values()) or 1
            rows = ''
            for st, (label, color) in state_labels.items():
                n = counts.get(st, 0)
                if n:
                    pct = round((n / total_s) * 100, 1)
                    rows += (
                        '<div style="margin:4px 0">'
                        '<span style="display:inline-block;width:90px">%s</span>'
                        '<span style="display:inline-block;width:200px;background:#eee;border-radius:4px;vertical-align:middle">'
                        '<span style="display:inline-block;height:14px;border-radius:4px;background:%s;width:%d%%"></span></span>'
                        '<span style="margin-left:8px;font-weight:500">%s%% (%d)</span>'
                        '</div>' % (label, color, int(pct), pct, n)
                    )
            known = set(state_labels.keys())
            other_count = sum(n for st, n in counts.items() if st not in known)
            if other_count:
                pct = round((other_count / total_s) * 100, 1)
                rows += (
                    '<div style="margin:4px 0">'
                    '<span style="display:inline-block;width:90px">Other</span>'
                    '<span style="display:inline-block;width:200px;background:#eee;border-radius:4px;vertical-align:middle">'
                    '<span style="display:inline-block;height:14px;border-radius:4px;background:#B4B2A9;width:%d%%"></span></span>'
                    '<span style="margin-left:8px;font-weight:500">%s%% (%d)</span>'
                    '</div>' % (int(pct), pct, other_count)
                )
            rec.sentiment_summary = rows or '<span style="color:#888">No data yet</span>' 

    @api.model
    def open_dashboard(self):
        """Return (creating if needed) the singleton dashboard record."""
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dashboard',
            'res_model': 'beena.dashboard',
            'view_mode': 'form',
            'res_id': rec.id,
            'target': 'current',
        }
