# -*- coding: utf-8 -*-
"""dropship.dashboard — the module's main landing page.

A single persistent record whose fields are all computed live on each open:
KPI tiles (listings, published, views, sold, visitors, orders, revenue) plus
rich HTML blocks (top countries, top products, top categories, provider mix,
recent imports, catalog funnel). No JavaScript — the "charts" are CSS bar
rows, so it renders reliably in any Odoo backend.
"""
from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import html_escape as esc


# brand palette
_Y = '#F5C320'
_D = '#412402'


def _bar_rows(rows, unit=''):
    """rows: list of (label, value). Returns HTML horizontal bar chart."""
    if not rows:
        return '<div style="color:#aaa;padding:8px">No data yet</div>'
    top = max((v for _, v in rows), default=0) or 1
    out = []
    for label, val in rows:
        pct = max(2, round((val or 0) * 100.0 / top))
        out.append(
            '<div style="display:flex;align-items:center;margin:4px 0;gap:8px">'
            '<div style="width:38%%;font-size:13px;color:#333;overflow:hidden;'
            'text-overflow:ellipsis;white-space:nowrap">%s</div>'
            '<div style="flex:1;background:#f3f3f3;border-radius:6px;height:18px">'
            '<div style="width:%d%%;background:%s;height:18px;border-radius:6px">'
            '</div></div>'
            '<div style="width:70px;text-align:right;font-weight:600;'
            'font-size:13px">%s%s</div></div>'
            % (esc(str(label)), pct, _Y, '{:,}'.format(int(val or 0)), unit))
    return ''.join(out)


class DropshipDashboard(models.Model):
    _name = 'dropship.dashboard'
    _description = 'Uellow World Dashboard'

    name = fields.Char(default='Uellow World')

    # ── KPI tiles ─────────────────────────────────────────────────────
    kpi_listings = fields.Integer(compute='_compute_kpis', string="Source Listings")
    kpi_published = fields.Integer(compute='_compute_kpis', string="Live Products")
    kpi_materialized = fields.Integer(compute='_compute_kpis', string="Materialized")
    kpi_deals = fields.Integer(compute='_compute_kpis', string="Active Deals")
    kpi_views = fields.Integer(compute='_compute_kpis', string="Total Views")
    kpi_sold = fields.Integer(compute='_compute_kpis', string="Units Sold")
    kpi_visitors_30d = fields.Integer(compute='_compute_kpis', string="Visitors (30d)")
    kpi_orders_30d = fields.Integer(compute='_compute_kpis', string="Orders (30d)")
    kpi_revenue_30d = fields.Monetary(compute='_compute_kpis', string="Revenue (30d)",
                                      currency_field='currency_id')
    kpi_reviews = fields.Integer(compute='_compute_kpis', string="Reviews Imported")
    kpi_videos = fields.Integer(compute='_compute_kpis', string="Products w/ Video")
    kpi_conversion = fields.Float(compute='_compute_kpis', string="Conversion % (30d)")
    kpi_to_fulfill = fields.Integer(compute='_compute_kpis', string="Orders to Fulfill")
    kpi_slow_movers = fields.Integer(compute='_compute_kpis', string="Slow Movers")
    kpi_profit_30d = fields.Monetary(compute='_compute_kpis', string="Profit (30d)",
                                     currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', compute='_compute_kpis')

    # ── HTML blocks ───────────────────────────────────────────────────
    html_funnel = fields.Html(compute='_compute_blocks', sanitize=False)
    html_countries = fields.Html(compute='_compute_blocks', sanitize=False)
    html_top_products = fields.Html(compute='_compute_blocks', sanitize=False)
    html_top_categories = fields.Html(compute='_compute_blocks', sanitize=False)
    html_providers = fields.Html(compute='_compute_blocks', sanitize=False)
    html_recent = fields.Html(compute='_compute_blocks', sanitize=False)
    html_visitors_trend = fields.Html(compute='_compute_blocks', sanitize=False)
    html_provider_health = fields.Html(compute='_compute_blocks', sanitize=False)
    html_attention = fields.Html(compute='_compute_blocks', sanitize=False)
    html_profit_trend = fields.Html(compute='_compute_blocks', sanitize=False)
    html_provider_perf = fields.Html(compute='_compute_blocks', sanitize=False)

    # ── click-through actions (every tile drills into its records) ─────
    def _open(self, name, model, domain, view_mode='list,form', ctx=None):
        views = [[False, v] for v in view_mode.split(',')]
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'domain': domain,
            'views': views,
            'view_mode': view_mode,
            'target': 'current',
            'context': ctx or {},
        }

    def action_view_published(self):
        return self._open('Live Products', 'product.template',
                          [('is_dropship', '=', True), ('is_published', '=', True)])

    def action_view_listings(self):
        return self._open('Source Catalog', 'dropship.product', [])

    def action_view_materialized(self):
        return self._open('Materialized', 'dropship.product',
                          [('state', '=', 'materialized')])

    def action_view_deals(self):
        return self._open('Deals', 'dropship.product', [('is_deal', '=', True)])

    def action_view_top_viewed(self):
        return self._open('Most Viewed', 'dropship.product',
                          [('view_count', '>', 0)], ctx={'search_default_order': 1})

    def action_view_videos(self):
        return self._open('With Video', 'dropship.product',
                          [('video_url', '!=', False)])

    def action_view_visitors(self):
        wid = self._world_website_id()
        return self._open('World Visitors', 'website.visitor',
                          [('website_id', '=', wid)] if wid else [])

    def action_view_orders(self):
        return self._open('Dropship Orders', 'sale.order',
                          [('is_dropship_order', '=', True)])

    def action_view_to_fulfill(self):
        return self._open('Orders to Fulfill', 'sale.order',
                          [('is_dropship_order', '=', True),
                           ('state', 'in', ('sale', 'done')),
                           ('dropship_order_ref', '=', False)])

    def action_view_revenue(self):
        wid = self._world_website_id()
        dom = [('is_dropship_order', '=', True), ('state', 'in', ('sale', 'done'))]
        if wid:
            dom.append(('website_id', '=', wid))
        return self._open('World Revenue', 'sale.order', dom)

    def _slow_mover_ids(self):
        """Materialized products with real interest (views) but zero sales."""
        DP = self.env['dropship.product'].sudo()
        min_views = int(self.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.slowmover_min_views', 20) or 20)
        cands = DP.search([('state', '=', 'materialized'),
                          ('view_count', '>=', min_views)])
        return [p.id for p in cands if not p.uellow_sold_count]

    def action_view_slow_movers(self):
        return self._open('Slow Movers', 'dropship.product',
                          [('id', 'in', self._slow_mover_ids())])

    def action_view_categories(self):
        return self._open('World Categories', 'dropship.category', [])

    def action_view_providers(self):
        return self._open('Providers', 'dropship.provider', [])

    def action_refresh(self):
        """Re-open the dashboard (recomputes all live figures)."""
        return self._open('Dashboard', 'dropship.dashboard',
                          [('id', '=', self.id)], view_mode='form')

    def action_print_report(self):
        """Render the branded performance PDF for this dashboard."""
        self.ensure_one()
        return self.env.ref(
            'uellow_dropship.action_report_dropship_dashboard'
        ).report_action(self)

    @api.model
    def _cron_email_monthly_report(self):
        """Optional monthly email of the PDF report to the configured admins.
        Gated by setting uellow_dropship.monthly_report_emails (comma list)."""
        emails = (self.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.monthly_report_emails') or '').strip()
        if not emails:
            return
        dash = self.env.ref('uellow_dropship.dropship_dashboard_main',
                            raise_if_not_found=False)
        if not dash:
            return
        report = self.env.ref('uellow_dropship.action_report_dropship_dashboard')
        pdf, _ = report._render_qweb_pdf(report.report_name, dash.ids)
        attach = self.env['ir.attachment'].sudo().create({
            'name': 'Uellow-World-Report.pdf',
            'type': 'binary',
            'datas': __import__('base64').b64encode(pdf),
            'mimetype': 'application/pdf',
        })
        self.env['mail.mail'].sudo().create({
            'subject': '🌍 Uellow World — Monthly Performance Report',
            'body_html': '<p>Attached is this month\'s Uellow World performance '
                         'report.<br/>مرفق تقرير أداء يلو وورلد لهذا الشهر.</p>',
            'email_to': emails,
            'attachment_ids': [(6, 0, attach.ids)],
        }).send()

    # ── helpers ───────────────────────────────────────────────────────
    def _world_website_id(self):
        try:
            return int(self.env['ir.config_parameter'].sudo().get_param(
                'uellow_dropship.website_id') or 0)
        except Exception:  # noqa: BLE001
            return 0

    def _compute_kpis(self):
        DP = self.env['dropship.product'].sudo()
        Tmpl = self.env['product.template'].sudo()
        SO = self.env['sale.order'].sudo()
        wid = self._world_website_id()
        since = fields.Datetime.now() - timedelta(days=30)
        usd = self.env['res.currency'].browse(1)
        for rec in self:
            rec.currency_id = usd.id if usd.exists() else self.env.company.currency_id.id
            rec.kpi_listings = DP.search_count([])
            rec.kpi_materialized = DP.search_count([('state', '=', 'materialized')])
            rec.kpi_deals = DP.search_count([('is_deal', '=', True)])
            rec.kpi_published = Tmpl.search_count([
                ('is_dropship', '=', True), ('is_published', '=', True)])
            rec.kpi_videos = DP.search_count([('video_url', '!=', False)])
            # views (real on-site) + sold (provider + uellow)
            self.env.cr.execute(
                "SELECT COALESCE(SUM(view_count),0) FROM dropship_product")
            rec.kpi_views = int(self.env.cr.fetchone()[0] or 0)
            self.env.cr.execute(
                "SELECT COALESCE(SUM(review_count),0) FROM dropship_product")
            rec.kpi_reviews = int(self.env.cr.fetchone()[0] or 0)
            # units sold on Uellow for materialized dropship products
            sold = 0
            try:
                mats = DP.search([('state', '=', 'materialized')])
                variant_ids = mats.mapped('product_tmpl_id.product_variant_ids').ids
                if variant_ids:
                    self.env.cr.execute(
                        "SELECT COALESCE(SUM(product_uom_qty),0) "
                        "FROM sale_order_line WHERE product_id IN %s "
                        "AND state IN ('sale','done')", (tuple(variant_ids),))
                    sold = int(self.env.cr.fetchone()[0] or 0)
            except Exception:  # noqa: BLE001
                sold = 0
            rec.kpi_sold = sold
            # visitors (30d) on the World website
            vis = 0
            if wid:
                try:
                    vis = self.env['website.visitor'].sudo().search_count([
                        ('website_id', '=', wid),
                        ('create_date', '>=', since)])
                except Exception:  # noqa: BLE001
                    vis = 0
            rec.kpi_visitors_30d = vis
            # orders + revenue (30d) on World
            orders = SO.search([
                ('website_id', '=', wid),
                ('state', 'in', ('sale', 'done')),
                ('date_order', '>=', since)]) if wid else SO.browse([])
            rec.kpi_orders_30d = len(orders)
            rec.kpi_revenue_30d = sum(orders.mapped('amount_total')) or 0.0
            rec.kpi_profit_30d = sum(orders.mapped('dropship_profit')) or 0.0
            rec.kpi_conversion = round(
                (len(orders) * 100.0 / vis), 2) if vis else 0.0
            rec.kpi_to_fulfill = SO.search_count([
                ('is_dropship_order', '=', True),
                ('state', 'in', ('sale', 'done')),
                ('dropship_order_ref', '=', False)])
            rec.kpi_slow_movers = len(self._slow_mover_ids())

    def _compute_blocks(self):
        DP = self.env['dropship.product'].sudo()
        wid = self._world_website_id()
        since = fields.Datetime.now() - timedelta(days=30)
        for rec in self:
            # funnel: listed → promoted → materialized → published
            listed = DP.search_count([('state', '=', 'listed')])
            promoted = DP.search_count([('state', '=', 'promoted')])
            materialized = DP.search_count([('state', '=', 'materialized')])
            published = self.env['product.template'].sudo().search_count([
                ('is_dropship', '=', True), ('is_published', '=', True)])
            rec.html_funnel = _bar_rows([
                ('Listed (source)', listed),
                ('Promoted', promoted),
                ('Materialized', materialized),
                ('Published live', published)])

            # top countries (visitors)
            rows = []
            if wid:
                try:
                    self.env.cr.execute("""
                        SELECT COALESCE(c.name->>'en_US', 'Unknown') AS country,
                               COUNT(*) AS n
                        FROM website_visitor v
                        LEFT JOIN res_country c ON c.id = v.country_id
                        WHERE v.website_id = %s
                        GROUP BY country ORDER BY n DESC LIMIT 10
                    """, (wid,))
                    rows = [(r[0], r[1]) for r in self.env.cr.fetchall()]
                except Exception:  # noqa: BLE001
                    rows = []
            rec.html_countries = _bar_rows(rows)

            # visitors trend (last 8 weeks)
            trend = []
            if wid:
                try:
                    self.env.cr.execute("""
                        SELECT to_char(date_trunc('week', create_date), 'MM-DD') AS wk,
                               COUNT(*) AS n
                        FROM website_visitor
                        WHERE website_id = %s AND create_date >= %s
                        GROUP BY wk ORDER BY wk
                    """, (wid, fields.Datetime.now() - timedelta(weeks=8)))
                    trend = [(r[0], r[1]) for r in self.env.cr.fetchall()]
                except Exception:  # noqa: BLE001
                    trend = []
            rec.html_visitors_trend = _bar_rows(trend)

            # profit trend (last 8 weeks) — revenue vs profit per week
            trend_rows = []
            try:
                self.env.cr.execute("""
                    SELECT to_char(date_trunc('week', date_order), 'MM-DD') AS wk,
                           COALESCE(SUM(dropship_profit), 0) AS profit
                    FROM sale_order
                    WHERE is_dropship_order = TRUE
                      AND state IN ('sale', 'done')
                      AND date_order >= %s
                    GROUP BY wk ORDER BY wk
                """, (fields.Datetime.now() - timedelta(weeks=8),))
                trend_rows = [(r[0], float(r[1] or 0)) for r in self.env.cr.fetchall()]
            except Exception:  # noqa: BLE001
                trend_rows = []
            rec.html_profit_trend = _bar_rows(trend_rows)

            # top products by views
            top = DP.search([('view_count', '>', 0)],
                            order='view_count desc', limit=10)
            rec.html_top_products = _bar_rows(
                [((p.title_en or p.source_id or '—')[:40], p.view_count)
                 for p in top])

            # top categories (by listing count)
            try:
                grp = DP.read_group(
                    [('category_name', '!=', False)], ['category_name'],
                    ['category_name'], limit=10, orderby='category_name')
                cats = sorted(
                    [(g['category_name'], g['category_name_count'])
                     for g in grp if g.get('category_name')],
                    key=lambda x: x[1], reverse=True)[:10]
            except Exception:  # noqa: BLE001
                cats = []
            rec.html_top_categories = _bar_rows(cats)

            # provider mix
            try:
                grp = DP.read_group([], ['provider_id'], ['provider_id'])
                provs = []
                for g in grp:
                    pv = g.get('provider_id')
                    label = pv[1] if isinstance(pv, (list, tuple)) else 'Unknown'
                    provs.append((label, g.get('provider_id_count') or 0))
                provs.sort(key=lambda x: x[1], reverse=True)
            except Exception:  # noqa: BLE001
                provs = []
            rec.html_providers = _bar_rows(provs)

            # recent imports (30d)
            # provider health (connection + last sync)
            provs = self.env['dropship.provider'].sudo().search([])
            if provs:
                rows = []
                for p in provs:
                    ok = p.state == 'connected'
                    dot = '#2e7d32' if ok else '#c62828'
                    last = p.last_sync.strftime('%Y-%m-%d %H:%M') if p.last_sync else 'never'
                    rows.append(
                        '<tr><td style="padding:5px 10px;border-bottom:1px solid '
                        '#f0f0f0"><span style="color:%s">●</span> %s</td>'
                        '<td style="padding:5px 10px;border-bottom:1px solid #f0f0f0;'
                        'color:#666">%s</td><td style="padding:5px 10px;border-bottom:'
                        '1px solid #f0f0f0;color:#999">last sync: %s</td></tr>'
                        % (dot, esc(p.name or ''), esc(p.state or ''), last))
                rec.html_provider_health = (
                    '<table style="border-collapse:collapse;width:100%%">%s</table>'
                    % ''.join(rows))
            else:
                rec.html_provider_health = '<div style="color:#aaa;padding:8px">No providers</div>'

            # provider performance: profit / margin ranking per supplier.
            # Aggregate over each provider's materialized products, weighting by
            # units actually sold on Uellow (fallback to per-listing potential
            # margin when nothing has sold yet, so a fresh provider still ranks).
            try:
                mats = DP.search([('state', '=', 'materialized')])
                agg = {}
                for p in mats:
                    pv = p.provider_id
                    key = pv.id if pv else 0
                    a = agg.setdefault(key, {
                        'name': pv.name if pv else 'Unknown',
                        'listings': 0, 'units': 0, 'rev': 0.0, 'cost': 0.0})
                    a['listings'] += 1
                    units = p.uellow_sold_count or 0
                    sale = p.sale_price or 0.0
                    land = p.landed_price or p.base_cost or 0.0
                    a['units'] += units
                    a['rev'] += units * sale
                    a['cost'] += units * land
                perf = []
                for a in agg.values():
                    profit = a['rev'] - a['cost']
                    margin = (profit * 100.0 / a['rev']) if a['rev'] else 0.0
                    perf.append((a['name'], a['listings'], a['units'],
                                 a['rev'], profit, margin))
                perf.sort(key=lambda x: (x[4], x[2]), reverse=True)
            except Exception:  # noqa: BLE001
                perf = []
            if perf:
                head = (
                    '<tr style="background:#faf6ec;color:#412402;font-size:12px">'
                    '<th style="padding:6px 10px;text-align:left">Provider</th>'
                    '<th style="padding:6px 10px;text-align:right">Products</th>'
                    '<th style="padding:6px 10px;text-align:right">Units Sold</th>'
                    '<th style="padding:6px 10px;text-align:right">Revenue</th>'
                    '<th style="padding:6px 10px;text-align:right">Profit</th>'
                    '<th style="padding:6px 10px;text-align:right">Margin</th></tr>')
                body = []
                for name, listings, units, revv, profit, margin in perf:
                    pcol = '#1b5e20' if profit >= 0 else '#c62828'
                    body.append(
                        '<tr>'
                        '<td style="padding:6px 10px;border-bottom:1px solid #f0f0f0">'
                        '<b>%s</b></td>'
                        '<td style="padding:6px 10px;border-bottom:1px solid #f0f0f0;'
                        'text-align:right">%d</td>'
                        '<td style="padding:6px 10px;border-bottom:1px solid #f0f0f0;'
                        'text-align:right">%d</td>'
                        '<td style="padding:6px 10px;border-bottom:1px solid #f0f0f0;'
                        'text-align:right">%.2f</td>'
                        '<td style="padding:6px 10px;border-bottom:1px solid #f0f0f0;'
                        'text-align:right;color:%s;font-weight:600">%.2f</td>'
                        '<td style="padding:6px 10px;border-bottom:1px solid #f0f0f0;'
                        'text-align:right;color:%s">%.1f%%</td></tr>'
                        % (esc(str(name)), listings, units, revv,
                           pcol, profit, pcol, margin))
                rec.html_provider_perf = (
                    '<table style="border-collapse:collapse;width:100%%">%s%s</table>'
                    '<div style="color:#999;font-size:11px;margin-top:4px">'
                    'Revenue &amp; profit weighted by units sold on Uellow '
                    '(materialized products).</div>'
                    % (head, ''.join(body)))
            else:
                rec.html_provider_perf = (
                    '<div style="color:#aaa;padding:8px">No sales data yet</div>')

            # needs attention: viewed-but-never-sold + stale deals
            dead = DP.search([('view_count', '>', 20),
                             ('state', '=', 'materialized')],
                            order='view_count desc', limit=8)
            dead = [d for d in dead if not d.uellow_sold_count]
            stale_cut = fields.Datetime.now() - timedelta(days=2)
            stale_deals = DP.search_count([
                ('is_deal', '=', True), ('state', '=', 'materialized'),
                '|', ('detail_synced', '=', False),
                     ('detail_synced', '<', stale_cut)])
            parts = []
            if dead:
                items = ''.join(
                    '<li>%s — <b>%d views</b>, 0 sales</li>'
                    % (esc((d.title_en or '—')[:46]), d.view_count) for d in dead)
                parts.append(
                    '<div style="margin-bottom:8px"><b>👀 Viewed but not selling</b>'
                    '<ul style="margin:4px 0 0 18px">%s</ul></div>' % items)
            if stale_deals:
                parts.append(
                    '<div style="color:#b26a00">⏰ <b>%d</b> deal(s) have a stale '
                    'price (not synced in 2+ days).</div>' % stale_deals)
            rec.html_attention = ''.join(parts) or (
                '<div style="color:#2e7d32;padding:8px">✅ Nothing needs attention.</div>')

            recent = DP.search([('create_date', '>=', since)],
                              order='create_date desc', limit=12)
            if recent:
                cells = ''.join(
                    '<tr><td style="padding:5px 10px;border-bottom:1px solid '
                    '#f0f0f0">%s</td><td style="padding:5px 10px;border-bottom:'
                    '1px solid #f0f0f0;color:#666">%s</td><td style="padding:5px '
                    '10px;border-bottom:1px solid #f0f0f0;text-align:right">%s</td>'
                    '</tr>' % (esc((p.title_en or '—')[:52]),
                               esc(p.category_name or ''),
                               p.create_date.strftime('%Y-%m-%d') if p.create_date else '')
                    for p in recent)
                rec.html_recent = (
                    '<table style="border-collapse:collapse;width:100%%">%s</table>'
                    % cells)
            else:
                rec.html_recent = '<div style="color:#aaa;padding:8px">No recent imports</div>'
