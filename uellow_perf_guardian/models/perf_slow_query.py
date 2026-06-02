import logging
import re

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PerfSlowQuery(models.Model):
    """One row per slow-query sample lifted from Postgres pg_stat_statements."""
    _name = 'uellow.perf.slow.query'
    _description = 'Uellow Performance — slow query sample'
    _order = 'mean_ms desc'

    digest = fields.Char(string='SQL digest (first 200 chars)',
        index=True, required=True)
    calls = fields.Integer()
    total_ms = fields.Float()
    mean_ms = fields.Float(index=True)
    max_ms = fields.Float()
    rows = fields.Integer()
    last_seen = fields.Datetime()

    _sql_constraints = [
        ('digest_unique', 'unique(digest)',
         'A digest is only stored once — its stats are updated.'),
    ]

    @api.model
    def cron_collect(self):
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        if not cfg.slowq_enabled:
            return 0
        threshold = max(50, int(cfg.slowq_threshold_ms or 500))
        # pg_stat_statements may not be installed — be defensive
        try:
            self.env.cr.execute("""
                SELECT
                    LEFT(query, 200) AS digest,
                    calls,
                    total_exec_time AS total_ms,
                    mean_exec_time AS mean_ms,
                    max_exec_time AS max_ms,
                    rows
                FROM pg_stat_statements
                WHERE mean_exec_time >= %s
                  AND query NOT ILIKE '%%pg_stat_statements%%'
                ORDER BY mean_exec_time DESC
                LIMIT 50
            """, [threshold])
        except Exception as e:
            _logger.info('[perf-guardian] pg_stat_statements unavailable: %s', e)
            return 0
        rows = self.env.cr.dictfetchall()
        now = fields.Datetime.now()
        for r in rows:
            digest = re.sub(r'\s+', ' ', r['digest']).strip()[:200]
            existing = self.search([('digest', '=', digest)], limit=1)
            vals = {
                'digest': digest, 'calls': r['calls'],
                'total_ms': r['total_ms'], 'mean_ms': r['mean_ms'],
                'max_ms': r['max_ms'], 'rows': r['rows'], 'last_seen': now,
            }
            if existing:
                existing.write(vals)
            else:
                self.create(vals)
        return len(rows)
