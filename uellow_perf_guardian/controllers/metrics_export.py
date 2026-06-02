"""External metrics export — JSON + Prometheus text format.

Auth: a static token from settings. Add a header
``X-Perf-Token: <token>`` or ``?token=<token>`` query param.
"""
import json

from odoo import http
from odoo.http import request, Response


def _auth_ok():
    cfg = request.env['uellow.perf.config'].sudo().get_config()
    token = cfg.export_token
    if not token:
        return False
    sent = (request.httprequest.headers.get('X-Perf-Token') or
            request.params.get('token') or '')
    return sent == token


class MetricsExportController(http.Controller):

    @http.route('/perf/metrics', type='http', auth='public', csrf=False,
                methods=['GET'], save_session=False)
    def metrics_json(self, **kw):
        if not _auth_ok():
            return Response('Unauthorized', status=401)
        data = request.env['uellow.perf.dashboard'].sudo().get_summary()
        return Response(json.dumps(data, default=str), status=200,
                        content_type='application/json')

    @http.route('/perf/metrics.prom', type='http', auth='public', csrf=False,
                methods=['GET'], save_session=False)
    def metrics_prometheus(self, **kw):
        if not _auth_ok():
            return Response('Unauthorized', status=401)
        d = request.env['uellow.perf.dashboard'].sudo().get_summary()
        lines = []
        rum = d.get('rum') or {}
        sysd = d.get('system') or {}
        bots = d.get('bots') or {}
        lines += [
            '# HELP uellow_rum_lcp_p75 Largest Contentful Paint p75 (ms)',
            '# TYPE uellow_rum_lcp_p75 gauge',
            f'uellow_rum_lcp_p75 {rum.get("lcp_p75", 0)}',
            '# HELP uellow_rum_cls_p75 Cumulative Layout Shift p75',
            '# TYPE uellow_rum_cls_p75 gauge',
            f'uellow_rum_cls_p75 {rum.get("cls_p75", 0)}',
            '# HELP uellow_rum_inp_p75 INP p75 (ms)',
            '# TYPE uellow_rum_inp_p75 gauge',
            f'uellow_rum_inp_p75 {rum.get("inp_p75", 0)}',
            '# HELP uellow_rum_ttfb_p75 TTFB p75 (ms)',
            '# TYPE uellow_rum_ttfb_p75 gauge',
            f'uellow_rum_ttfb_p75 {rum.get("ttfb_p75", 0)}',
            '# HELP uellow_rum_samples_24h RUM samples last 24h',
            '# TYPE uellow_rum_samples_24h counter',
            f'uellow_rum_samples_24h {rum.get("samples", 0)}',
            '# HELP uellow_cache_hit_pct Cloudflare HIT % (synthetic, 1h)',
            '# TYPE uellow_cache_hit_pct gauge',
            f'uellow_cache_hit_pct {d.get("cache_hit_pct", 0)}',
            '# HELP uellow_system_load_1m Load avg 1 minute',
            '# TYPE uellow_system_load_1m gauge',
            f'uellow_system_load_1m {sysd.get("load_1m", 0)}',
            '# HELP uellow_system_mem_used_pct Memory used %',
            '# TYPE uellow_system_mem_used_pct gauge',
            f'uellow_system_mem_used_pct {sysd.get("mem_used_pct", 0)}',
            '# HELP uellow_system_idle_tx Idle-in-transaction PG connections',
            '# TYPE uellow_system_idle_tx gauge',
            f'uellow_system_idle_tx {sysd.get("idle_tx_count", 0)}',
            '# HELP uellow_bots_over_quota_24h Over-quota events last 24h',
            '# TYPE uellow_bots_over_quota_24h counter',
            f'uellow_bots_over_quota_24h {bots.get("over_quota_24h", 0)}',
            '# HELP uellow_bots_reqs_24h Total bot requests last 24h',
            '# TYPE uellow_bots_reqs_24h counter',
            f'uellow_bots_reqs_24h {bots.get("reqs_24h", 0)}',
        ]
        for b in bots.get('top') or []:
            n = (b['name'] or 'unknown').replace('"', '').replace('\\', '')
            lines += [
                f'uellow_bot_req_today{{bot="{n}"}} {b["req_today"]}',
                f'uellow_bot_bytes_today_mb{{bot="{n}"}} '
                f'{b.get("bytes_today_mb", 0)}',
            ]
        return Response('\n'.join(lines) + '\n', status=200,
                        content_type='text/plain; version=0.0.4')
