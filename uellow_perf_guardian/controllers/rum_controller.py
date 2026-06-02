import json
import logging
import time
from collections import deque

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# In-memory rate-limit state per IP for /perf/rum
_RUM_WINDOW = {}


def _device_class(ua):
    if not ua:
        return 'other'
    ua = ua.lower()
    if 'mobi' in ua or 'iphone' in ua:
        return 'mobile'
    if 'ipad' in ua or 'tablet' in ua:
        return 'tablet'
    return 'desktop'


def _client_ip():
    h = request.httprequest.headers
    return (h.get('CF-Connecting-IP') or
            (h.get('X-Forwarded-For') or '').split(',')[0].strip() or
            request.httprequest.remote_addr or '')


def _rate_limited(ip, per_min):
    if not (ip and per_min):
        return False
    now = time.time()
    win = _RUM_WINDOW.get(ip)
    if win is None:
        win = deque(maxlen=128)
        _RUM_WINDOW[ip] = win
    while win and (now - win[0]) > 60:
        win.popleft()
    win.append(now)
    if len(_RUM_WINDOW) > 50000:
        cutoff = now - 120
        for k in list(_RUM_WINDOW.keys()):
            d = _RUM_WINDOW[k]
            if not d or d[-1] < cutoff:
                _RUM_WINDOW.pop(k, None)
    return len(win) > per_min


class PerfRumController(http.Controller):

    @http.route('/perf/rum', type='http', auth='public', methods=['POST'],
                csrf=False, save_session=False)
    def rum_beacon(self, **kw):
        cfg = request.env['uellow.perf.config'].sudo().get_config()
        if not cfg.rum_enabled:
            return http.Response(status=204)
        ip = _client_ip()
        if _rate_limited(ip, cfg.rum_beacon_per_ip_per_min or 30):
            return http.Response(status=429)
        try:
            raw = request.httprequest.get_data(as_text=True) or '{}'
            data = json.loads(raw)
        except (ValueError, TypeError):
            return http.Response(status=400)
        try:
            page = (data.get('page') or '/')[:255]
            request.env['uellow.perf.metric'].sudo().create({
                'page': page,
                'country': (request.httprequest.headers.get(
                    'CF-IPCountry') or '')[:8],
                'device': _device_class(
                    request.httprequest.headers.get('User-Agent')),
                'connection': (data.get('conn') or '')[:32],
                'lcp_ms':  float(data.get('lcp')  or 0),
                'cls':     float(data.get('cls')  or 0),
                'inp_ms':  float(data.get('inp')  or 0),
                'fcp_ms':  float(data.get('fcp')  or 0),
                'ttfb_ms': float(data.get('ttfb') or 0),
                'dom_ms':  float(data.get('dom')  or 0),
                'load_ms': float(data.get('load') or 0),
                'lcp_element': (data.get('lcp_el') or '')[:255],
                'inp_target':  (data.get('inp_el') or '')[:255],
            })
            request.env.cr.commit()
        except Exception as e:
            _logger.exception('[perf-rum] beacon failed: %s', e)
            return http.Response(status=500)
        return http.Response(status=204)
