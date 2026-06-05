"""Bot quota / throttle middleware + sliding-window rate-limit + 5xx capture.

Hooks on ``ir.http``:
* ``_pre_dispatch`` — bot classify + verify (reverse-DNS) + daily quota +
  sliding-window per-IP burst limit. 429 if exceeded.
* ``_post_dispatch`` — bytes accounting + 5xx error-bucket increment.
"""
import logging
import time

from werkzeug.exceptions import HTTPException

from odoo import models
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

_PASS_THROUGH = (
    '/robots.txt', '/sitemap.xml', '/sitemap', '/perf/rum',
    '/perf/metrics', '/perf/health', '/web/health',
    '/longpolling', '/websocket',
)

# In-memory sliding-window state (per worker process).
# Key: (bot_class_id, ip)  → deque of timestamps in last 60s
_BURST_WINDOW = {}


def _is_pass_through(path):
    if not path:
        return True
    for p in _PASS_THROUGH:
        if path == p or path.startswith(p + '/'):
            return True
    return False


def _client_ip():
    if request is None or not request.httprequest:
        return ''
    h = request.httprequest.headers
    cf = h.get('CF-Connecting-IP')
    if cf:
        return cf
    xff = h.get('X-Forwarded-For') or ''
    if xff:
        return xff.split(',')[0].strip()
    return request.httprequest.remote_addr or ''


def _check_burst(bot_id, ip, limit):
    """Sliding-window rate-limiter. Returns True if OVER limit."""
    if not (limit and ip):
        return False
    now = time.time()
    key = (bot_id, ip)
    win = _BURST_WINDOW.get(key)
    if win is None:
        from collections import deque
        win = deque(maxlen=512)
        _BURST_WINDOW[key] = win
    # Trim entries older than 60s
    while win and (now - win[0]) > 60:
        win.popleft()
    win.append(now)
    # GC the global dict if it grows huge
    if len(_BURST_WINDOW) > 20000:
        cutoff = now - 120
        for k in list(_BURST_WINDOW.keys()):
            d = _BURST_WINDOW[k]
            if not d or d[-1] < cutoff:
                _BURST_WINDOW.pop(k, None)
    return len(win) > limit


class IrHttpInherit(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _pre_dispatch(cls, rule, arguments):
        try:
            cls._perf_guardian_throttle()
        except HTTPException:
            # v2.1.70 — THE enforcement bug: the 429/403 response is
            # raised as an HTTPException, but the catch-all below was
            # swallowing it ("throttle skipped") — so over-quota bots
            # sailed through and rendered full pages (~70k junk
            # requests/day saturating both CPUs). Re-raise: this
            # exception IS the intended throttle response.
            raise
        except Exception as e:
            _logger.warning('[perf-guardian] throttle skipped: %s', e)
        return super()._pre_dispatch(rule, arguments)

    @classmethod
    def _handle_error(cls, exception):
        # v2.1.70 — serve throttle responses AS-IS. Without this,
        # http_routing's frontend handler caught the 429, found no
        # 'http_routing.429' template, fell back to 418 and rendered a
        # FULL themed error page (~200KB) — burning the same CPU the
        # throttle was meant to save.
        resp = getattr(exception, 'response', None)
        try:
            if resp is not None and \
                    resp.headers.get('X-Perf-Guardian') == 'throttled':
                return resp
        except Exception:
            pass
        return super()._handle_error(exception)

    @classmethod
    def _post_dispatch(cls, response):
        try:
            cls._perf_guardian_record_bytes(response)
        except Exception as e:
            _logger.warning('[perf-guardian] bytes record skipped: %s', e)
        try:
            cls._perf_guardian_record_errors(response)
        except Exception as e:
            _logger.warning('[perf-guardian] error record skipped: %s', e)
        return super()._post_dispatch(response)

    # ────────────────────────── pre-dispatch ─────────────────────────
    @classmethod
    def _perf_guardian_throttle(cls):
        if request is None or not request.httprequest:
            return
        path = request.httprequest.path or ''
        if _is_pass_through(path):
            return

        env = request.env
        cfg = env['uellow.perf.config'].sudo().get_config()
        if not cfg.bot_quota_enabled and not cfg.bot_quota_soft:
            return

        ua = request.httprequest.headers.get('User-Agent') or ''
        bot = env['uellow.perf.bot.class'].sudo().classify(ua)
        if not bot:
            return
        request._perf_bot = bot

        if bot.is_blocked:
            cls._perf_emit_429(403, bot.name, blocked=True)
            return

        ip = _client_ip()

        if (bot.is_search_engine or bot.require_verified) and ip:
            if not env['uellow.perf.bot.class'].sudo().verify_ip(bot.name, ip):
                fake = env['uellow.perf.bot.class'].sudo().classify('bot')
                if fake and fake.id != bot.id:
                    bot = fake
                    request._perf_bot = bot

        over_class = bool(
            (bot.daily_req_budget and bot.req_today >= bot.daily_req_budget) or
            (bot.daily_bytes_budget_mb and
             bot.bytes_today_mb >= bot.daily_bytes_budget_mb))

        over_ip = False
        if bot.per_ip_req_budget and ip:
            current = env['uellow.perf.bot.ip'].sudo().increment(bot.id, ip, 0)
            if current >= bot.per_ip_req_budget:
                over_ip = True

        # Sliding-window per-IP burst check (in-memory, very fast)
        burst_limit = cfg.burst_per_ip_per_min or 0
        over_burst = _check_burst(bot.id, ip, burst_limit)

        # Wrap the counter UPDATE in a savepoint so a concurrent-update
        # serialization conflict (common when many bots hit at once)
        # doesn't abort the whole HTTP transaction — losing a few
        # increments is fine; killing the page request is not.
        try:
            with env.cr.savepoint():
                env.cr.execute("""
                    UPDATE uellow_perf_bot_class
                       SET req_today = req_today + 1,
                           last_seen = NOW() AT TIME ZONE 'UTC'
                     WHERE id = %s
                """, [bot.id])
        except Exception:
            pass

        try:
            with env.cr.savepoint():
                env['uellow.perf.bot.hit'].sudo().record(
                    bot, 0, over_class or over_ip or over_burst, path)
        except Exception:
            pass

        if (over_class or over_ip or over_burst) and cfg.bot_quota_enabled \
                and not cfg.bot_quota_soft:
            tag = ('BURST' if over_burst else
                   ('IP' if over_ip else 'CLASS'))
            _logger.info('[perf-guardian] OVER-QUOTA-%s bot=%s ip=%s path=%s',
                         tag, bot.name, ip[:32], path[:120])
            cls._perf_emit_429(429, bot.name,
                               retry_after=cfg.bot_429_retry_after
                                            if not over_burst else 60)

    @classmethod
    def _perf_emit_429(cls, status, bot_name, blocked=False, retry_after=86400):
        msg = (f'<html><head><title>Rate limited</title></head>'
               f'<body><h1>{"Forbidden" if blocked else "Rate limited"}</h1>'
               f'<p>Crawler <b>{bot_name}</b> '
               f'{"is blocked" if blocked else "exceeded its budget"}.</p>'
               f'</body></html>')
        resp = Response(msg, status=status,
                        content_type='text/html; charset=utf-8')
        if not blocked:
            resp.headers['Retry-After'] = str(int(retry_after))
        resp.headers['X-Perf-Guardian'] = 'throttled'
        from werkzeug.exceptions import HTTPException
        exc = HTTPException(description=msg, response=resp)
        exc.code = status
        raise exc

    # ───────────────────────── post-dispatch ─────────────────────────
    @classmethod
    def _perf_guardian_record_bytes(cls, response):
        if request is None or not request.httprequest:
            return
        bot = getattr(request, '_perf_bot', None)
        if not bot:
            return
        if response is None or not hasattr(response, 'headers'):
            return
        try:
            size = int(response.headers.get('Content-Length') or 0)
        except (TypeError, ValueError):
            size = 0
        if size <= 0:
            return
        env = request.env
        mb = size / (1024 * 1024)
        # Same savepoint protection as the request counter.
        try:
            with env.cr.savepoint():
                env.cr.execute("""
                    UPDATE uellow_perf_bot_class
                       SET bytes_today_mb = bytes_today_mb + %s
                     WHERE id = %s
                """, [mb, bot.id])
        except Exception:
            pass
        try:
            with env.cr.savepoint():
                env['uellow.perf.bot.hit'].sudo().record(
                    bot, size, False, request.httprequest.path)
        except Exception:
            pass

    @classmethod
    def _perf_guardian_record_errors(cls, response):
        if request is None or not request.httprequest:
            return
        if response is None or not hasattr(response, 'status_code'):
            return
        code = response.status_code or 0
        if code < 500:
            return
        try:
            request.env['uellow.perf.error.bucket'].sudo().record(
                code, request.httprequest.path)
        except Exception:
            pass
