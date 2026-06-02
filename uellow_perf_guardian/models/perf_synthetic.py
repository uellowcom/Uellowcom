import logging
import time
from urllib import request, error

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

_DEFAULT_BASE = 'http://localhost:8069'


class PerfSyntheticResult(models.Model):
    """One row per synthetic check."""
    _name = 'uellow.perf.synthetic'
    _description = 'Uellow Performance — synthetic probe'
    _order = 'create_date desc'

    url = fields.Char(required=True, index=True)
    status_code = fields.Integer()
    ttfb_ms = fields.Float(string='TTFB (ms)')
    total_ms = fields.Float(string='Total (ms)')
    size_bytes = fields.Integer()
    ok = fields.Boolean(index=True)
    error = fields.Char()
    cf_cache_status = fields.Char(string='cf-cache-status', index=True,
        help='Cloudflare cache verdict: HIT, MISS, DYNAMIC, EXPIRED, …')
    edge_age_seconds = fields.Integer(string='Edge age (s)',
        help='How long the response has been cached at the edge.')

    @api.model
    def cron_run_synthetic(self):
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        if not cfg.synthetic_enabled:
            return 0
        urls = [u.strip() for u in (cfg.synthetic_urls or '').splitlines()
                if u.strip()]
        warn = cfg.synthetic_lcp_warn_ms or 2500
        crit = cfg.synthetic_lcp_crit_ms or 4000
        n = 0
        for path in urls:
            full = path if path.startswith('http') else _DEFAULT_BASE + path
            t0 = time.time()
            try:
                req = request.Request(full, headers={
                    'User-Agent': 'UellowPerfGuardian/1.0 (synthetic)',
                    'Cookie': '',
                })
                with request.urlopen(req, timeout=15) as resp:
                    body = resp.read(64 * 1024)
                    elapsed = (time.time() - t0) * 1000
                    cf_status = (resp.headers.get('cf-cache-status') or '').upper()
                    try:
                        age = int(resp.headers.get('age') or 0)
                    except (TypeError, ValueError):
                        age = 0
                    self.create({
                        'url': path,
                        'status_code': resp.getcode(),
                        'ttfb_ms': elapsed,
                        'total_ms': elapsed,
                        'size_bytes': len(body),
                        'ok': resp.getcode() < 400,
                        'cf_cache_status': cf_status or False,
                        'edge_age_seconds': age,
                    })
                    if elapsed >= crit:
                        self.env['uellow.perf.alert'].sudo().fire(
                            'synthetic', 'critical',
                            f'Synthetic {path} = {int(elapsed)} ms (>= {crit})')
                    elif elapsed >= warn:
                        self.env['uellow.perf.alert'].sudo().fire(
                            'synthetic', 'warning',
                            f'Synthetic {path} = {int(elapsed)} ms (>= {warn})')
                    n += 1
            except (error.URLError, error.HTTPError, OSError) as e:
                self.create({
                    'url': path, 'ok': False, 'error': str(e)[:200],
                    'total_ms': (time.time() - t0) * 1000,
                })
                self.env['uellow.perf.alert'].sudo().fire(
                    'synthetic', 'critical',
                    f'Synthetic {path} FAILED: {str(e)[:100]}')
        # After collection, evaluate cache health
        try:
            self._evaluate_cache_health()
        except Exception:
            _logger.exception('[perf-guardian] cache health eval failed')
        return n

    @api.model
    def _evaluate_cache_health(self):
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        target = max(0, int(cfg.cache_health_target_pct or 75))
        self.env.cr.execute("""
            SELECT
                COUNT(*) FILTER (WHERE cf_cache_status = 'HIT') AS hits,
                COUNT(*) AS total
            FROM uellow_perf_synthetic
            WHERE create_date >= NOW() - INTERVAL '1 hour'
              AND cf_cache_status IS NOT NULL
              AND cf_cache_status != ''
        """)
        row = self.env.cr.dictfetchone() or {}
        total = row.get('total') or 0
        if total < 5:
            return  # not enough data
        pct = round(100 * (row.get('hits') or 0) / total)
        if pct < target * 0.5:
            self.env['uellow.perf.alert'].sudo().fire(
                'cache', 'critical',
                f'CF HIT ratio = {pct}% (target {target}%) — cache rule may be off')
        elif pct < target:
            self.env['uellow.perf.alert'].sudo().fire(
                'cache', 'warning',
                f'CF HIT ratio = {pct}% (target {target}%)')
