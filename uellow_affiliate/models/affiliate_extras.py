# -*- coding: utf-8 -*-
"""Affiliate 2.0 extras: bonus campaigns, partner news, click analytics.

• uellow.affiliate.campaign — period BOOST: extra commission percentage
  points on top of the resolved rate, optionally scoped to a category
  or a single product, optionally to specific tiers.
• uellow.affiliate.news — announcements shown in the partner panel/app.
• uellow.affiliate.click — per-open log behind /aff/<code> so the panel
  and app can chart clicks per day (the old single counter stays).
"""
from datetime import datetime, timedelta

from odoo import api, fields, models


class UellowAffiliateCampaign(models.Model):
    _name = 'uellow.affiliate.campaign'
    _description = 'Affiliate bonus campaign'
    _order = 'date_from desc'

    name = fields.Char(required=True)
    name_ar = fields.Char(string='Name (AR)')
    active = fields.Boolean(default=True)
    boost_pct = fields.Float(
        string='Extra commission (+% points)', default=2.0, required=True,
        help='Added ON TOP of the resolved commission % during the '
             'campaign window. 2.0 means a 5% product pays 7%.')
    date_from = fields.Datetime(required=True,
                                default=fields.Datetime.now)
    date_to = fields.Datetime(required=True)
    categ_id = fields.Many2one('product.public.category',
                               string='Only this category (+children)')
    product_tmpl_id = fields.Many2one('product.template',
                                      string='Only this product')
    tiers = fields.Selection([
        ('all', 'All tiers'),
        ('bronze_silver', 'Bronze + Silver only'),
        ('gold_platinum', 'Gold + Platinum only'),
    ], default='all', required=True, string='Eligible tiers')
    note = fields.Char(string='Banner line (EN)')
    note_ar = fields.Char(string='Banner line (AR)')

    @api.model
    def active_now(self):
        now = fields.Datetime.now()
        return self.sudo().search([
            ('active', '=', True),
            ('date_from', '<=', now), ('date_to', '>=', now)])

    def applies_to(self, affiliate, product_tmpl):
        self.ensure_one()
        if self.tiers == 'bronze_silver' and \
                affiliate.tier not in ('bronze', 'silver'):
            return False
        if self.tiers == 'gold_platinum' and \
                affiliate.tier not in ('gold', 'platinum'):
            return False
        if self.product_tmpl_id:
            return self.product_tmpl_id.id == product_tmpl.id
        if self.categ_id:
            node_ids = set()
            for c in product_tmpl.public_categ_ids:
                node = c
                while node:
                    node_ids.add(node.id)
                    node = node.parent_id
            return self.categ_id.id in node_ids
        return True

    def to_public_dict(self):
        self.ensure_one()
        return {
            'id': self.id,
            'name': {'en': self.name or '',
                     'ar': self.name_ar or self.name or ''},
            'note': {'en': self.note or '',
                     'ar': self.note_ar or self.note or ''},
            'boost_pct': self.boost_pct,
            'ends_at': self.date_to.isoformat() if self.date_to else None,
            'scope': self.product_tmpl_id.display_name
                     if self.product_tmpl_id
                     else (self.categ_id.display_name
                           if self.categ_id else ''),
        }


class UellowAffiliateNews(models.Model):
    _name = 'uellow.affiliate.news'
    _description = 'Affiliate partner news / announcement'
    _order = 'create_date desc'

    title = fields.Char(required=True)
    title_ar = fields.Char(string='Title (AR)')
    body = fields.Text()
    body_ar = fields.Text(string='Body (AR)')
    emoji = fields.Char(default='📣', size=8)
    active = fields.Boolean(default=True)

    def to_public_dict(self):
        self.ensure_one()
        return {
            'id': self.id,
            'emoji': self.emoji or '📣',
            'title': {'en': self.title or '',
                      'ar': self.title_ar or self.title or ''},
            'body': {'en': self.body or '',
                     'ar': self.body_ar or self.body or ''},
            'date': self.create_date.isoformat()
                    if self.create_date else None,
        }


class UellowAffiliateClick(models.Model):
    _name = 'uellow.affiliate.click'
    _description = 'Affiliate referral link open'
    _order = 'create_date desc'

    affiliate_id = fields.Many2one('uellow.affiliate', required=True,
                                   ondelete='cascade', index=True)
    product_tmpl_id = fields.Many2one('product.template',
                                      ondelete='set null')

    @api.model
    def series_for(self, affiliate, days=14):
        """[{date, clicks}] for the last N days."""
        start = (datetime.utcnow() - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0)
        self.env.cr.execute("""
            SELECT date_trunc('day', create_date)::date AS d, COUNT(*)
            FROM uellow_affiliate_click
            WHERE affiliate_id = %s AND create_date >= %s
            GROUP BY 1
        """, (affiliate.id, start))
        got = {r[0].isoformat(): r[1] for r in self.env.cr.fetchall()}
        out = []
        for i in range(days):
            d = (start + timedelta(days=i)).date().isoformat()
            out.append({'date': d, 'clicks': got.get(d, 0)})
        return out


class UellowAffiliateCampaignEngine(models.Model):
    _inherit = 'uellow.affiliate'

    def commission_pct_for(self, product_tmpl):
        """Base resolution + ACTIVE CAMPAIGN boosts."""
        pct = super().commission_pct_for(product_tmpl)
        try:
            for camp in self.env['uellow.affiliate.campaign'].active_now():
                if camp.applies_to(self, product_tmpl):
                    pct += camp.boost_pct
        except Exception:
            pass
        return pct

    def activity_feed(self, limit=20):
        """Recent events: commissions, payouts, submitted-order moves."""
        self.ensure_one()
        events = []
        for c in self.commission_ids[:30]:
            events.append({
                'when': c.create_date,
                'icon': '💰' if c.state != 'cancelled' else '❌',
                'text': {
                    'en': 'Commission %.3f — %s (%s)' % (
                        c.amount, c.sale_order_id.name or '—',
                        dict(c._fields['state'].selection).get(c.state)),
                    'ar': 'عمولة %.3f — %s' % (
                        c.amount, c.sale_order_id.name or '—'),
                },
                'state': c.state,
            })
        for p in self.payout_ids[:10]:
            events.append({
                'when': p.create_date,
                'icon': '💸',
                'text': {'en': 'Payout %s — %.3f (%s)'
                               % (p.name, p.amount, p.state),
                         'ar': 'سحب %s — %.3f' % (p.name, p.amount)},
                'state': p.state,
            })
        for o in self.submitted_order_ids[:10]:
            events.append({
                'when': o.create_date,
                'icon': '📝',
                'text': {'en': 'Order %s — %s' % (o.name, o.state),
                         'ar': 'طلب %s — %s' % (o.name, o.state)},
                'state': o.state,
            })
        events.sort(key=lambda e: e['when'] or fields.Datetime.now(),
                    reverse=True)
        for e in events:
            e['when'] = e['when'].isoformat() if e['when'] else None
        return events[:limit]

    def earnings_series(self, days=14):
        """[{date, amount}] confirmed+paid commission per day."""
        self.ensure_one()
        start = (datetime.utcnow() - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0)
        out = {}
        for c in self.commission_ids:
            if c.state in ('confirmed', 'paid') and c.create_date \
                    and c.create_date >= start:
                k = c.create_date.date().isoformat()
                out[k] = out.get(k, 0.0) + c.amount
        series = []
        for i in range(days):
            d = (start + timedelta(days=i)).date().isoformat()
            series.append({'date': d, 'amount': round(out.get(d, 0), 3)})
        return series
