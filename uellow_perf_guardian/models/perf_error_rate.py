"""HTTP 5xx error rate tracking. Counters are upserted per-minute via
the post-dispatch hook; a cron then evaluates the rate and fires alerts.
"""
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PerfErrorBucket(models.Model):
    """One row per minute per status code. Aggregated 5xx visible separately."""
    _name = 'uellow.perf.error.bucket'
    _description = 'Uellow Performance — error rate bucket'
    _order = 'bucket_at desc'

    bucket_at = fields.Datetime(required=True, index=True)
    status_code = fields.Integer(required=True, index=True)
    count = fields.Integer(default=0)
    sample_path = fields.Char()

    _sql_constraints = [
        ('bucket_status_unique', 'unique(bucket_at, status_code)',
         'One row per minute per status code.'),
    ]

    @api.model
    def record(self, status_code, path):
        if status_code < 400:
            return
        now = fields.Datetime.now().replace(second=0, microsecond=0)
        self.env.cr.execute("""
            INSERT INTO uellow_perf_error_bucket
                (bucket_at, status_code, count, sample_path,
                 create_uid, create_date, write_uid, write_date)
            VALUES (%s, %s, 1, %s, 1, NOW() AT TIME ZONE 'UTC',
                    1, NOW() AT TIME ZONE 'UTC')
            ON CONFLICT (bucket_at, status_code)
            DO UPDATE SET count = uellow_perf_error_bucket.count + 1,
                          write_date = NOW() AT TIME ZONE 'UTC'
        """, [now, status_code, (path or '')[:255]])

    @api.model
    def cron_evaluate(self):
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        if not cfg.error_rate_enabled:
            return 0
        since = fields.Datetime.now() - timedelta(minutes=1)
        self.env.cr.execute("""
            SELECT COALESCE(SUM(count), 0) AS errs
            FROM uellow_perf_error_bucket
            WHERE bucket_at >= %s AND status_code >= 500
        """, [since])
        errs = (self.env.cr.dictfetchone() or {}).get('errs', 0)
        Alert = self.env['uellow.perf.alert'].sudo()
        Inc = self.env['uellow.perf.incident'].sudo()
        if errs >= (cfg.error_rate_crit_per_min or 20):
            a = Alert.fire('system', 'critical',
                f'{errs} HTTP 5xx errors in the last minute')
            Inc.open_incident('error', f'5xx burst: {errs}/min', alert=a)
        elif errs >= (cfg.error_rate_warn_per_min or 5):
            Alert.fire('system', 'warning',
                f'{errs} HTTP 5xx errors in the last minute')
        else:
            Inc.close_open('error')
        return errs

    @api.model
    def cron_prune(self):
        cutoff = fields.Datetime.now() - timedelta(days=7)
        self.env.cr.execute(
            "DELETE FROM uellow_perf_error_bucket WHERE bucket_at < %s",
            [cutoff])


class PerfBundleSize(models.Model):
    """Tracks /web/assets/* bundle sizes over time."""
    _name = 'uellow.perf.bundle.size'
    _description = 'Uellow Performance — bundle size sample'
    _order = 'create_date desc'

    url = fields.Char(required=True, index=True)
    size_bytes = fields.Integer()
    size_kb = fields.Integer(compute='_compute_kb', store=True)
    encoding = fields.Char()
    status_code = fields.Integer()

    @api.depends('size_bytes')
    def _compute_kb(self):
        for r in self:
            r.size_kb = (r.size_bytes or 0) // 1024

    @api.model
    def cron_collect(self):
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        if not cfg.bundle_monitor_enabled:
            return 0
        from urllib import request as urlreq, error as urlerr
        base = 'http://localhost:8069'
        urls = [u.strip() for u in (cfg.bundle_urls or '').splitlines()
                if u.strip()]
        n = 0
        for u in urls:
            full = u if u.startswith('http') else base + u
            try:
                req = urlreq.Request(full, method='HEAD',
                    headers={'Accept-Encoding': 'gzip, br',
                             'User-Agent': 'UellowPerfBundle/1.0'})
                with urlreq.urlopen(req, timeout=8) as resp:
                    size = int(resp.headers.get('Content-Length') or 0)
                    enc = resp.headers.get('Content-Encoding') or ''
                    self.create({
                        'url': u, 'size_bytes': size,
                        'encoding': enc, 'status_code': resp.getcode(),
                    })
                    n += 1
            except (urlerr.URLError, urlerr.HTTPError, OSError) as e:
                _logger.info('bundle probe %s failed: %s', u, e)
        return n

    @api.model
    def cron_prune(self):
        cutoff = fields.Datetime.now() - timedelta(days=90)
        self.env.cr.execute(
            "DELETE FROM uellow_perf_bundle_size WHERE create_date < %s",
            [cutoff])
