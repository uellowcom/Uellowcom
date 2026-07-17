import logging
import re
import socket
import time
from datetime import timedelta

import odoo.sql_db
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _counter_exec(dbname, query, params):
    """Run a hot per-minute counter write on a short, dedicated
    READ COMMITTED connection.

    Bot/error telemetry hammers a single row per (class, minute) or
    (status, minute). Under the web request's default REPEATABLE READ
    isolation, concurrent writers collide with 40001 "could not serialize
    access due to concurrent update", which odoo.sql_db logs at ERROR on
    every clash (the request itself is unaffected -- the callers already
    swallow it in a savepoint -- but the log flood is relentless: >1000/h
    under crawl load). At READ COMMITTED the concurrent writers simply
    block on the row lock and proceed, so no serialization error is ever
    raised. Telemetry only -- any failure is dropped silently.
    """
    try:
        cr = odoo.sql_db.db_connect(dbname).cursor()
        try:
            cr.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            cr.execute(query, params)
            cr.commit()
        finally:
            cr.close()
    except Exception:
        pass

# Allowed reverse-DNS suffixes for "real" search-engine bots
_VERIFIED_DOMAINS = {
    'Googlebot':  ('.googlebot.com', '.google.com'),
    'Bingbot':    ('.search.msn.com',),
    'Applebot':   ('.applebot.apple.com', '.apple.com'),
    'DuckDuckBot':('.duckduckgo.com',),
    'YandexBot':  ('.yandex.com', '.yandex.ru', '.yandex.net'),
}


class PerfBotClass(models.Model):
    """One row per known bot family (Googlebot, Bingbot, GPTBot, …)."""
    _name = 'uellow.perf.bot.class'
    _description = 'Uellow Performance — bot class'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    ua_pattern = fields.Char(string='User-Agent contains', required=True)
    is_search_engine = fields.Boolean(string='Search engine (allow generously)',
        default=False)
    is_blocked = fields.Boolean(default=False)
    require_verified = fields.Boolean(
        string='Require reverse-DNS verification',
        help='Only honor this class for IPs whose reverse-DNS matches a '
             'known suffix (Googlebot only counts if PTR ends with '
             'googlebot.com). Unverified IPs get the strict generic budget.',
        default=False)

    daily_req_budget = fields.Integer(string='Requests/day', default=5000)
    daily_bytes_budget_mb = fields.Integer(string='Bandwidth/day (MB)',
        default=500)
    per_ip_req_budget = fields.Integer(string='Requests/day per IP',
        default=0,
        help='Hard cap per single IP within this class. 0 = no per-IP cap.')

    req_today = fields.Integer(readonly=True, default=0)
    bytes_today_mb = fields.Float(readonly=True, default=0.0)
    last_seen = fields.Datetime(readonly=True)
    over_quota = fields.Boolean(readonly=True, compute='_compute_over_quota',
        store=False)

    @api.depends('req_today', 'daily_req_budget', 'bytes_today_mb',
                 'daily_bytes_budget_mb')
    def _compute_over_quota(self):
        for r in self:
            r.over_quota = bool(
                (r.daily_req_budget and r.req_today >= r.daily_req_budget) or
                (r.daily_bytes_budget_mb and
                 r.bytes_today_mb >= r.daily_bytes_budget_mb))

    @api.model
    def classify(self, user_agent):
        if not user_agent:
            return False
        cache = getattr(self.env.registry, '_perf_bot_cache', None)
        if cache is None:
            cache = []
            for c in self.sudo().search([], order='sequence, id'):
                try:
                    pat = re.compile(re.escape(c.ua_pattern), re.IGNORECASE)
                except re.error:
                    continue
                cache.append((pat, c.id))
            self.env.registry._perf_bot_cache = cache
        for pat, cid in cache:
            if pat.search(user_agent):
                return self.sudo().browse(cid)
        return False

    @api.model
    def invalidate_cache(self):
        if hasattr(self.env.registry, '_perf_bot_cache'):
            delattr(self.env.registry, '_perf_bot_cache')

    @api.model_create_multi
    def create(self, vals_list):
        rec = super().create(vals_list)
        self.invalidate_cache()
        return rec

    def write(self, vals):
        rec = super().write(vals)
        self.invalidate_cache()
        return rec

    def unlink(self):
        rec = super().unlink()
        self.invalidate_cache()
        return rec

    def action_reset_today(self):
        for r in self:
            r.req_today = 0
            r.bytes_today_mb = 0.0
        return True

    @api.model
    def verify_ip(self, bot_name, ip):
        """Reverse-DNS verification with a tiny in-memory TTL cache.

        Returns True if the IP's PTR points to one of the known suffixes
        for this bot family. Cached per (bot_name, ip) for 6 hours.
        """
        if not ip or not bot_name:
            return True
        # Match by name keyword (e.g. "Googlebot")
        suffixes = None
        for key, suf in _VERIFIED_DOMAINS.items():
            if key.lower() in bot_name.lower():
                suffixes = suf
                break
        if not suffixes:
            return True  # Class has no known suffix — accept

        cache = getattr(self.env.registry, '_perf_bot_dns_cache', None)
        if cache is None:
            cache = {}
            self.env.registry._perf_bot_dns_cache = cache
        # Positive results are cheap to trust for 6h. Negative results MUST
        # expire fast: a single transient reverse-DNS hiccup on a real
        # Googlebot IP would otherwise black-hole that IP for 6h (downgraded
        # to the tiny generic budget → hard 429), which cascades into Google
        # cutting its crawl rate. Re-verify a failed IP after 5 minutes.
        ttl_pos = 6 * 3600   # 6 hours
        ttl_neg = 300        # 5 minutes
        now = time.time()
        key = (bot_name, ip)
        cached = cache.get(key)
        if cached:
            age = now - cached[0]
            if cached[1] and age < ttl_pos:
                return True
            if (not cached[1]) and age < ttl_neg:
                return False

        verified = False
        try:
            ptr = socket.gethostbyaddr(ip)[0].lower()
            verified = any(ptr.endswith(s) for s in suffixes)
            if verified:
                # Forward-confirm to defeat PTR spoofing
                try:
                    forward = socket.gethostbyname(ptr)
                    verified = (forward == ip)
                except Exception:
                    verified = False
        except Exception:
            verified = False

        cache[key] = (now, verified)
        # Drop oldest entries if cache grows too large
        if len(cache) > 5000:
            oldest = sorted(cache.items(), key=lambda kv: kv[1][0])[:1000]
            for k, _ in oldest:
                cache.pop(k, None)
        return verified


class PerfBotHit(models.Model):
    """Rolling log — one row per ~1 minute aggregation per bot class."""
    _name = 'uellow.perf.bot.hit'
    _description = 'Uellow Performance — bot hit aggregate'
    _order = 'bucket_at desc'
    _rec_name = 'bot_class_id'

    bot_class_id = fields.Many2one('uellow.perf.bot.class', ondelete='cascade',
        required=True, index=True)
    bucket_at = fields.Datetime(required=True, index=True)
    req_count = fields.Integer(default=0)
    bytes_total = fields.Integer(default=0)
    over_quota_count = fields.Integer(default=0)
    sample_path = fields.Char()

    @api.model
    def record(self, bot_class, byte_count, over_quota, path):
        now = fields.Datetime.now().replace(second=0, microsecond=0)
        _counter_exec(self.env.cr.dbname, """
            INSERT INTO uellow_perf_bot_hit
                (bot_class_id, bucket_at, req_count, bytes_total,
                 over_quota_count, sample_path, create_uid, create_date,
                 write_uid, write_date)
            VALUES (%s, %s, 1, %s, %s, %s, 1, NOW() AT TIME ZONE 'UTC',
                    1, NOW() AT TIME ZONE 'UTC')
            ON CONFLICT (bot_class_id, bucket_at)
            DO UPDATE SET
                req_count = uellow_perf_bot_hit.req_count + 1,
                bytes_total = uellow_perf_bot_hit.bytes_total
                              + EXCLUDED.bytes_total,
                over_quota_count = uellow_perf_bot_hit.over_quota_count
                                   + EXCLUDED.over_quota_count,
                write_date = NOW() AT TIME ZONE 'UTC'
        """, [bot_class.id, now, byte_count or 0,
              1 if over_quota else 0, (path or '')[:255]])

    def init(self):
        self.env.cr.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uellow_perf_bot_hit_unique
            ON uellow_perf_bot_hit (bot_class_id, bucket_at)
        """)

    @api.model
    def cron_rollover_daily(self):
        cls_model = self.env['uellow.perf.bot.class'].sudo()
        cls_model.search([]).write({'req_today': 0, 'bytes_today_mb': 0.0})
        self.env['uellow.perf.bot.ip'].sudo().search([]).unlink()
        cutoff = fields.Datetime.now() - timedelta(days=14)
        self.env.cr.execute(
            "DELETE FROM uellow_perf_bot_hit WHERE bucket_at < %s", [cutoff])
        _logger.info('[perf-guardian] daily rollover complete')
        return True


class PerfBotIp(models.Model):
    """Per-IP daily counter within a bot class — for per-IP quota."""
    _name = 'uellow.perf.bot.ip'
    _description = 'Uellow Performance — per-IP daily counter'

    bot_class_id = fields.Many2one('uellow.perf.bot.class', ondelete='cascade',
        required=True, index=True)
    ip = fields.Char(required=True, index=True, size=64)
    req_today = fields.Integer(default=0)
    bytes_today = fields.Integer(default=0)
    last_seen = fields.Datetime()

    _sql_constraints = [
        ('class_ip_unique', 'unique(bot_class_id, ip)',
         'One row per (bot_class, ip).'),
    ]

    @api.model
    def increment(self, bot_class_id, ip, byte_count):
        if not ip:
            return 0
        cr = self.env.cr
        cr.execute("""
            INSERT INTO uellow_perf_bot_ip
                (bot_class_id, ip, req_today, bytes_today, last_seen,
                 create_uid, create_date, write_uid, write_date)
            VALUES (%s, %s, 1, %s, NOW() AT TIME ZONE 'UTC',
                    1, NOW() AT TIME ZONE 'UTC',
                    1, NOW() AT TIME ZONE 'UTC')
            ON CONFLICT (bot_class_id, ip) DO UPDATE
              SET req_today = uellow_perf_bot_ip.req_today + 1,
                  bytes_today = uellow_perf_bot_ip.bytes_today + EXCLUDED.bytes_today,
                  last_seen = NOW() AT TIME ZONE 'UTC'
            RETURNING req_today
        """, [bot_class_id, ip[:64], byte_count or 0])
        row = cr.fetchone()
        return row[0] if row else 0
