# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.http import request


class LammaActivity(models.Model):
    _name = 'uellow.lamma.activity'
    _description = 'Lamma Customer Activity'
    _order = 'create_date desc'
    _rec_name = 'display_label'

    session_key = fields.Char('Session', index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', index=True, ondelete='set null')
    action = fields.Selection([
        ('start', 'بدء لمّة'), ('add', 'أضاف منتج'), ('remove', 'أزال منتج'),
        ('type', 'غيّر النوع'), ('checkout', 'أتمّ اللمّة'), ('clear', 'أفرغ اللمّة'),
    ], index=True, required=True)
    product_id = fields.Many2one('product.template', string='Product', ondelete='set null')
    lamma_type = fields.Selection([('normal', 'عادي'), ('installment', 'أقساط')], default='normal')
    items = fields.Integer('Items in bundle')
    subtotal = fields.Float('Subtotal')
    discount = fields.Float('Discount')
    source = fields.Selection([('web', 'الموقع'), ('app', 'التطبيق')], default='web', index=True)
    country_code = fields.Char('Country', index=True)
    display_label = fields.Char(compute='_compute_label', store=True)

    @api.depends('action', 'product_id', 'lamma_type')
    def _compute_label(self):
        amap = dict(self._fields['action'].selection)
        for r in self:
            r.display_label = '%s%s' % (amap.get(r.action, r.action or ''),
                                        (' — %s' % r.product_id.name) if r.product_id else '')

    # ------------------------------------------------------------------
    @api.model
    def log(self, action, product_id=None, summary=None, source='web'):
        """Fire-and-forget activity logging from the controllers."""
        try:
            sess = getattr(request, 'session', None)
            skey = getattr(sess, 'sid', None) if sess else None
            partner = None
            if request and request.env and request.env.user and not request.env.user._is_public():
                partner = request.env.user.partner_id.id
            vals = {
                'action': action,
                'product_id': int(product_id) if product_id else False,
                'session_key': (skey or '')[:64],
                'partner_id': partner,
                'source': source,
            }
            if isinstance(summary, dict):
                vals.update({
                    'lamma_type': summary.get('type') or 'normal',
                    'items': summary.get('n') or 0,
                    'subtotal': summary.get('subtotal') or 0.0,
                    'discount': summary.get('saved') or 0.0,
                    'country_code': summary.get('_country') or '',
                })
            self.sudo().create(vals)
        except Exception:
            pass

    # ------------------------------------------------------------------
    @api.model
    def dashboard_stats(self):
        """KPI snapshot for the dashboard."""
        self.env.cr.execute("""
            SELECT
              count(*) FILTER (WHERE action='add')                         AS adds,
              count(*) FILTER (WHERE action='remove')                      AS removes,
              count(*) FILTER (WHERE action='checkout')                    AS checkouts,
              count(DISTINCT session_key) FILTER (WHERE action IN ('start','add')) AS bundles,
              count(DISTINCT session_key) FILTER (WHERE action='checkout') AS converted,
              COALESCE(sum(discount) FILTER (WHERE action='checkout'),0)   AS discount_sum,
              COALESCE(avg(items)    FILTER (WHERE action='checkout'),0)   AS avg_items,
              count(*) FILTER (WHERE action='checkout' AND lamma_type='installment') AS inst_checkouts
            FROM uellow_lamma_activity
            WHERE create_date >= (now() - interval '30 days')
        """)
        r = self.env.cr.dictfetchone() or {}
        bundles = r.get('bundles') or 0
        conv = r.get('converted') or 0
        return {
            'adds': r.get('adds') or 0,
            'removes': r.get('removes') or 0,
            'checkouts': r.get('checkouts') or 0,
            'bundles': bundles,
            'converted': conv,
            'conversion_rate': round(min(100.0, conv / bundles * 100), 1) if bundles else 0.0,
            'discount_sum': round(r.get('discount_sum') or 0.0, 3),
            'avg_items': round(r.get('avg_items') or 0.0, 1),
            'inst_checkouts': r.get('inst_checkouts') or 0,
        }

    @api.model
    def dashboard_data(self, days=30):
        """Full dataset for the لمّة يلو dashboard."""
        days = int(days) if str(days).isdigit() else 30
        cr = self.env.cr
        kpis = self.dashboard_stats()

        def rows(sql, params=()):
            cr.execute(sql, params)
            return cr.dictfetchall()

        # activity per day (last 14 days) — trend
        trend = rows("""
            SELECT to_char(date_trunc('day', create_date), 'MM-DD') AS d,
                   count(*) FILTER (WHERE action IN ('start','add')) AS adds,
                   count(*) FILTER (WHERE action='checkout')         AS checkouts
              FROM uellow_lamma_activity
             WHERE create_date >= (now() - interval '14 days')
             GROUP BY 1 ORDER BY min(create_date)
        """)
        # source + type splits (period)
        sources = rows("""SELECT COALESCE(source,'web') s, count(*) c FROM uellow_lamma_activity
                          WHERE create_date >= (now() - interval '%s days') GROUP BY 1""" % days)
        types = rows("""SELECT COALESCE(lamma_type,'normal') t, count(*) c FROM uellow_lamma_activity
                        WHERE action='checkout' AND create_date >= (now() - interval '%s days') GROUP BY 1""" % days)

        def top(action):
            cr.execute("""
                SELECT a.product_id, count(*) c FROM uellow_lamma_activity a
                 WHERE a.action=%s AND a.product_id IS NOT NULL
                   AND a.create_date >= (now() - interval '%s days')
                 GROUP BY a.product_id ORDER BY c DESC LIMIT 8""" % ('%s', days), (action,))
            out = []
            for pid, c in cr.fetchall():
                p = self.env['product.template'].browse(pid)
                out.append({'name': (p.name or '#%s' % pid)[:40], 'count': c,
                            'image': '/web/image/product.template/%s/image_128' % pid})
            return out

        # Lamma value (from checkout events) + abandoned + top countries
        val = rows("""SELECT COALESCE(sum(subtotal),0) tot, COALESCE(avg(subtotal),0) avg
                        FROM uellow_lamma_activity
                       WHERE action='checkout' AND create_date >= (now() - interval '%s days')""" % days)
        v = val[0] if val else {'tot': 0, 'avg': 0}
        countries = rows("""SELECT COALESCE(NULLIF(country_code,''),'—') cc, count(*) c
                              FROM uellow_lamma_activity
                             WHERE create_date >= (now() - interval '%s days')
                             GROUP BY 1 ORDER BY c DESC LIMIT 6""" % days)
        abandoned = max(0, (kpis['bundles'] or 0) - (kpis['converted'] or 0))

        recent = self.search([], limit=15)
        amap = dict(self._fields['action'].selection)
        recent_data = [{
            'action': amap.get(a.action, a.action), 'code': a.action,
            'product': a.product_id.name or '', 'items': a.items,
            'discount': round(a.discount, 3), 'source': a.source or 'web',
            'country': a.country_code or '', 'when': str(a.create_date)[11:16],
            'date': str(a.create_date)[:10],
        } for a in recent]

        return {
            'kpis': kpis, 'days': days, 'trend': trend,
            'sources': sources, 'types': types,
            'top_added': top('add'), 'top_removed': top('remove'),
            'top_countries': countries,
            'total_value': round(v['tot'] or 0.0, 3),
            'avg_value': round(v['avg'] or 0.0, 3),
            'abandoned': abandoned,
            'recent': recent_data,
            'currency': (self.env.company.currency_id.symbol
                         or self.env.company.currency_id.name or 'KD'),
        }
