from datetime import timedelta

from odoo import api, fields, models


class PerfDashboard(models.TransientModel):
    """A transient row whose computed fields render the live dashboard."""
    _name = 'uellow.perf.dashboard'
    _description = 'Uellow Performance — dashboard'

    name = fields.Char(default='Perf Dashboard', readonly=True)
    html_summary = fields.Html(string='Summary', readonly=True,
                               compute='_compute_html', sanitize=False)
    rendered_at = fields.Datetime(default=fields.Datetime.now, readonly=True)

    @api.depends('rendered_at')
    def _compute_html(self):
        for r in self:
            r.html_summary = self._render_html()

    # ───────────────────────────── data ──────────────────────────────
    @api.model
    def get_summary(self):
        """JSON-safe summary used by the dashboard + the JSON-export endpoint."""
        Metric = self.env['uellow.perf.metric'].sudo()
        Bot = self.env['uellow.perf.bot.class'].sudo()
        Synth = self.env['uellow.perf.synthetic'].sudo()
        Alert = self.env['uellow.perf.alert'].sudo()
        SlowQ = self.env['uellow.perf.slow.query'].sudo()
        SysMetric = self.env['uellow.perf.system.metric'].sudo()

        now = fields.Datetime.now()
        since_24h = now - timedelta(hours=24)
        since_1h = now - timedelta(hours=1)

        # ─── RUM — p75 instead of avg (Google CWV convention) ─────
        self.env.cr.execute("""
            SELECT
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY lcp_ms)  AS lcp,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY cls)      AS cls,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY inp_ms)   AS inp,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY ttfb_ms)  AS ttfb,
                COUNT(*) AS n,
                COUNT(*) FILTER (WHERE grade = 'good') AS good,
                COUNT(*) FILTER (WHERE grade = 'ni')   AS ni,
                COUNT(*) FILTER (WHERE grade = 'poor') AS poor
            FROM uellow_perf_metric
            WHERE create_date >= %s
        """, [since_24h])
        rum = self.env.cr.dictfetchone() or {}

        # ─── RUM per country ──────────────────────────────────────
        self.env.cr.execute("""
            SELECT country,
                   PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY lcp_ms) AS lcp,
                   COUNT(*) AS n
            FROM uellow_perf_metric
            WHERE create_date >= %s AND country IS NOT NULL AND country != ''
            GROUP BY country
            ORDER BY n DESC
            LIMIT 10
        """, [since_24h])
        by_country = self.env.cr.dictfetchall()

        # ─── Bots ─────────────────────────────────────────────────
        top_bots = Bot.search([], order='req_today desc', limit=8).read([
            'name', 'req_today', 'daily_req_budget',
            'bytes_today_mb', 'daily_bytes_budget_mb', 'over_quota',
        ])
        self.env.cr.execute("""
            SELECT COALESCE(SUM(over_quota_count), 0) AS over_quota_24h,
                   COALESCE(SUM(req_count), 0) AS reqs_24h,
                   COALESCE(SUM(bytes_total), 0) AS bytes_24h
            FROM uellow_perf_bot_hit WHERE bucket_at >= %s
        """, [since_24h])
        bot_summary = self.env.cr.dictfetchone() or {}

        # ─── Synthetic + cache health ─────────────────────────────
        recent = Synth.search([('create_date', '>=', since_1h)],
                              order='create_date desc')
        synth_summary = []
        cache_hits = 0
        cache_total = 0
        for url in {r.url for r in recent}:
            rows = [r for r in recent if r.url == url]
            avg_ms = sum(r.total_ms or 0 for r in rows) / max(1, len(rows))
            hits = sum(1 for r in rows if r.cf_cache_status == 'HIT')
            synth_summary.append({
                'url': url, 'avg_ms': round(avg_ms),
                'last_ok': rows[0].ok if rows else False,
                'samples': len(rows),
                'cache_hit_pct': round(100 * hits / max(1, len(rows))),
            })
            cache_hits += hits
            cache_total += len(rows)
        synth_summary.sort(key=lambda x: -x['avg_ms'])
        cache_hit_pct = round(100 * cache_hits / cache_total) if cache_total else 0

        # ─── Alerts ───────────────────────────────────────────────
        alerts_24h = Alert.search_count([('create_date', '>=', since_24h)])
        alerts_critical = Alert.search_count([
            ('create_date', '>=', since_24h),
            ('severity', '=', 'critical')])

        # ─── Slow queries ─────────────────────────────────────────
        slowq_top = SlowQ.search([], order='mean_ms desc', limit=5).read(
            ['digest', 'mean_ms', 'calls'])

        # ─── System ───────────────────────────────────────────────
        sys_latest = SysMetric.search([], order='create_date desc', limit=1)
        sys_data = {}
        if sys_latest:
            sys_data = {
                'load_1m':    sys_latest.load_1m,
                'load_5m':    sys_latest.load_5m,
                'mem_used_pct':  sys_latest.mem_used_pct,
                'swap_used_mb':  sys_latest.swap_used_mb,
                'disk_used_pct': sys_latest.disk_used_pct,
                'cpu_count':  sys_latest.cpu_count,
                'idle_tx_count': sys_latest.idle_tx_count,
            }

        return {
            'rum': {
                'lcp_p75':  round(rum.get('lcp')  or 0),
                'cls_p75':  round(rum.get('cls')  or 0, 3),
                'inp_p75':  round(rum.get('inp')  or 0),
                'ttfb_p75': round(rum.get('ttfb') or 0),
                'samples':  rum.get('n') or 0,
                'good':     rum.get('good') or 0,
                'ni':       rum.get('ni')   or 0,
                'poor':     rum.get('poor') or 0,
                'by_country': by_country,
            },
            'bots': {
                'top':            top_bots,
                'over_quota_24h': bot_summary.get('over_quota_24h') or 0,
                'reqs_24h':       bot_summary.get('reqs_24h') or 0,
                'bytes_24h':      bot_summary.get('bytes_24h') or 0,
            },
            'synthetic': synth_summary,
            'cache_hit_pct': cache_hit_pct,
            'alerts': {
                'total_24h':    alerts_24h,
                'critical_24h': alerts_critical,
            },
            'slow_queries': slowq_top,
            'system': sys_data,
        }

    # ────────────────────────── rendering ────────────────────────────
    def _render_html(self):
        d = self.get_summary()
        rum = d['rum']; bots = d['bots']; synth = d['synthetic']
        sysd = d.get('system') or {}
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        refresh_s = max(0, int(cfg.dashboard_auto_refresh_seconds or 0))
        refresh_js = ''
        if refresh_s:
            refresh_js = (
                f'<script>(function(){{var s={refresh_s*1000};'
                f'setTimeout(function(){{location.reload()}},s)}})()</script>'
                f'<div style="font-size:11px;color:#888;margin:6px 0 12px">'
                f'Auto-refreshes every {refresh_s}s</div>')

        def card(title, value, sub='', tone='good'):
            colors = {
                'good': ('#2cb67d', '#e6f7ef'),
                'warn': ('#b8860b', '#fff4cc'),
                'bad':  ('#c92a2a', '#fde2e4'),
                'neutral': ('#412402', '#fff'),
            }
            border, bg = colors.get(tone, colors['neutral'])
            return (
                f'<div style="flex:1 1 200px;min-width:200px;padding:14px 16px;'
                f'border-radius:12px;background:{bg};'
                f'border-left:6px solid {border};box-shadow:0 1px 4px rgba(0,0,0,.06)">'
                f'<div style="font-size:11px;color:#666;text-transform:uppercase;'
                f'letter-spacing:.5px">{title}</div>'
                f'<div style="font-size:24px;font-weight:600;color:#412402;margin-top:4px">{value}</div>'
                f'<div style="font-size:11px;color:#888;margin-top:2px">{sub}</div>'
                f'</div>')

        def lcp_tone(v):
            return 'good' if v < 2500 else ('warn' if v < 4000 else 'bad')

        def cls_tone(v):
            return 'good' if v < 0.10 else ('warn' if v < 0.25 else 'bad')

        def inp_tone(v):
            return 'good' if v < 200 else ('warn' if v < 500 else 'bad')

        def cache_tone(v):
            return 'good' if v >= 75 else ('warn' if v >= 50 else 'bad')

        def load_tone(v):
            cpu = sysd.get('cpu_count') or 2
            return 'good' if v < cpu * 0.7 else ('warn' if v < cpu * 1.5 else 'bad')

        def mem_tone(v):
            return 'good' if v < 75 else ('warn' if v < 90 else 'bad')

        html = ['<div style="font-family:Inter,system-ui,sans-serif">']
        if refresh_js:
            html.append(refresh_js)

        html.append('<h3 style="color:#412402;margin:8px 0 12px">Core Web Vitals (p75, last 24h)</h3>')
        html.append('<div style="display:flex;flex-wrap:wrap;gap:12px">')
        html.append(card('LCP', f"{rum['lcp_p75']} ms",
                         f"{rum['samples']} samples", lcp_tone(rum['lcp_p75'])))
        html.append(card('CLS', f"{rum['cls_p75']:.3f}", '', cls_tone(rum['cls_p75'])))
        html.append(card('INP', f"{rum['inp_p75']} ms", '', inp_tone(rum['inp_p75'])))
        html.append(card('TTFB', f"{rum['ttfb_p75']} ms", '',
                         lcp_tone(rum['ttfb_p75'] * 2)))
        html.append(card('Good visits',
                         f"{rum['good']}",
                         f"poor: {rum['poor']} · ni: {rum['ni']}",
                         'good' if rum['good'] >= rum['poor'] else 'warn'))
        html.append('</div>')

        html.append('<h3 style="color:#412402;margin:18px 0 12px">Edge cache (Cloudflare)</h3>')
        html.append('<div style="display:flex;flex-wrap:wrap;gap:12px">')
        html.append(card('HIT %', f"{d['cache_hit_pct']}%",
                         'last hour synthetic probes', cache_tone(d['cache_hit_pct'])))
        html.append('</div>')

        html.append('<h3 style="color:#412402;margin:18px 0 12px">System</h3>')
        html.append('<div style="display:flex;flex-wrap:wrap;gap:12px">')
        if sysd:
            html.append(card('Load 1m', f"{sysd.get('load_1m', 0):.2f}",
                             f"{sysd.get('cpu_count')} CPU",
                             load_tone(sysd.get('load_1m', 0))))
            html.append(card('Memory used',
                             f"{sysd.get('mem_used_pct', 0):.0f}%",
                             '', mem_tone(sysd.get('mem_used_pct', 0))))
            html.append(card('Swap used',
                             f"{int(sysd.get('swap_used_mb', 0))} MB",
                             '',
                             'good' if sysd.get('swap_used_mb', 0) < 100 else 'warn'))
            html.append(card('Idle tx', f"{sysd.get('idle_tx_count', 0)}",
                             'pg connections idle in transaction',
                             'good' if sysd.get('idle_tx_count', 0) < 5 else 'warn'))
        else:
            html.append('<i style="color:#888">No system metric collected yet — '
                        'wait for the first cron tick.</i>')
        html.append('</div>')

        html.append('<h3 style="color:#412402;margin:18px 0 12px">Bots — top 8 today</h3>')
        html.append('<table style="width:100%;background:#fff;border-radius:12px;'
                    'overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.06)">')
        html.append('<thead><tr style="background:#fafafa;color:#666">'
                    '<th style="padding:10px 14px;text-align:left">Bot</th>'
                    '<th style="padding:10px 14px;text-align:right">Requests today</th>'
                    '<th style="padding:10px 14px;text-align:right">Budget</th>'
                    '<th style="padding:10px 14px;text-align:right">% used</th>'
                    '<th style="padding:10px 14px;text-align:left">Status</th>'
                    '</tr></thead><tbody>')
        for b in bots['top']:
            pct = round(100 * b['req_today'] / b['daily_req_budget']) \
                if b['daily_req_budget'] else 0
            tone = 'bad' if b['over_quota'] else ('warn' if pct >= 80 else 'good')
            badge_color = {'good': '#2cb67d', 'warn': '#b8860b', 'bad': '#c92a2a'}[tone]
            badge_bg = {'good': '#e6f7ef', 'warn': '#fff4cc', 'bad': '#fde2e4'}[tone]
            status = ('OVER QUOTA' if b['over_quota']
                      else ('Near limit' if pct >= 80 else 'OK'))
            html.append(f'<tr><td style="padding:10px 14px">{b["name"]}</td>'
                        f'<td style="padding:10px 14px;text-align:right">{b["req_today"]}</td>'
                        f'<td style="padding:10px 14px;text-align:right">{b["daily_req_budget"] or "∞"}</td>'
                        f'<td style="padding:10px 14px;text-align:right">{pct}%</td>'
                        f'<td style="padding:10px 14px">'
                        f'<span style="background:{badge_bg};color:{badge_color};'
                        f'padding:2px 8px;border-radius:10px;font-size:11px;'
                        f'font-weight:600">{status}</span></td></tr>')
        html.append('</tbody></table>')
        html.append(f'<div style="font-size:12px;color:#888;margin-top:6px">'
                    f'Over-quota events in 24h: {bots["over_quota_24h"]} · '
                    f'Total bot requests: {bots["reqs_24h"]}</div>')

        if rum['by_country']:
            html.append('<h3 style="color:#412402;margin:18px 0 12px">Top 10 countries</h3>')
            html.append('<table style="width:100%;background:#fff;border-radius:12px;overflow:hidden;'
                        'box-shadow:0 1px 4px rgba(0,0,0,.06)">')
            html.append('<thead><tr style="background:#fafafa;color:#666">'
                        '<th style="padding:10px 14px;text-align:left">Country</th>'
                        '<th style="padding:10px 14px;text-align:right">LCP p75 (ms)</th>'
                        '<th style="padding:10px 14px;text-align:right">Samples</th>'
                        '</tr></thead><tbody>')
            for c in rum['by_country']:
                tone = lcp_tone(c['lcp'] or 0)
                color = {'good': '#2cb67d', 'warn': '#b8860b', 'bad': '#c92a2a'}[tone]
                html.append(f'<tr><td style="padding:10px 14px">{c["country"]}</td>'
                            f'<td style="padding:10px 14px;text-align:right;color:{color};font-weight:600">'
                            f'{int(c["lcp"] or 0)}</td>'
                            f'<td style="padding:10px 14px;text-align:right">{c["n"]}</td></tr>')
            html.append('</tbody></table>')

        if synth:
            html.append('<h3 style="color:#412402;margin:18px 0 12px">Synthetic probes (last hour)</h3>')
            html.append('<table style="width:100%;background:#fff;border-radius:12px;overflow:hidden;'
                        'box-shadow:0 1px 4px rgba(0,0,0,.06)">')
            html.append('<thead><tr style="background:#fafafa;color:#666">'
                        '<th style="padding:10px 14px;text-align:left">URL</th>'
                        '<th style="padding:10px 14px;text-align:right">Avg ms</th>'
                        '<th style="padding:10px 14px;text-align:right">CF HIT %</th>'
                        '<th style="padding:10px 14px;text-align:right">Samples</th>'
                        '</tr></thead><tbody>')
            for s in synth:
                tone = lcp_tone(s['avg_ms'])
                color = {'good': '#2cb67d', 'warn': '#b8860b', 'bad': '#c92a2a'}[tone]
                html.append(f'<tr><td style="padding:10px 14px"><code>{s["url"]}</code></td>'
                            f'<td style="padding:10px 14px;text-align:right;color:{color};font-weight:600">'
                            f'{s["avg_ms"]}</td>'
                            f'<td style="padding:10px 14px;text-align:right">{s["cache_hit_pct"]}%</td>'
                            f'<td style="padding:10px 14px;text-align:right">{s["samples"]}</td></tr>')
            html.append('</tbody></table>')

        html.append('</div>')
        return ''.join(html)

    @api.model
    def open_dashboard(self):
        rec = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'uellow.perf.dashboard',
            'view_mode': 'form',
            'res_id': rec.id,
            'target': 'current',
        }
