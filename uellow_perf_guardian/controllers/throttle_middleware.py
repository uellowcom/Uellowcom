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
from odoo.addons.uellow_perf_guardian.models.perf_bot import _counter_exec

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


def _is_kuwait():
    """Home-market exemption. Kuwait (KW) visitors — AND any visitor whose
    country Cloudflare did not tag (blank / reserved code, e.g. carrier-NAT
    or geo header disabled) — are NEVER throttled. Only POSITIVELY-identified
    foreign traffic is subject to the guard, so real Kuwaiti shoppers behind
    shared mobile IPs can never be blocked."""
    try:
        if request is None or not request.httprequest:
            return True
        cc = (request.httprequest.headers.get('CF-IPCountry') or '').strip().upper()
        return cc in ('', 'KW', 'XX', 'T1', 'ZZ')
    except Exception:
        return True


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


IOS_APP = 'https://apps.apple.com/app/id6769010765'
ANDROID_APP = 'https://play.google.com/store/apps/details?id=com.uellow.app'
_IOS_BADGE = 'data:image/svg+xml;base64,PHN2ZyBpZD0ibGl2ZXR5cGUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgd2lkdGg9IjExOS42NjQwNyIgaGVpZ2h0PSI0MCIgdmlld0JveD0iMCAwIDExOS42NjQwNyA0MCI+CiAgPHRpdGxlPkRvd25sb2FkX29uX3RoZV9BcHBfU3RvcmVfQmFkZ2VfVVMtVUtfUkdCX2Jsa180U1ZHXzA5MjkxNzwvdGl0bGU+CiAgPGc+CiAgICA8Zz4KICAgICAgPGc+CiAgICAgICAgPHBhdGggZD0iTTExMC4xMzQ3NywwSDkuNTM0NjhjLS4zNjY3LDAtLjcyOSwwLTEuMDk0NzMuMDAyLS4zMDYxNS4wMDItLjYwOTg2LjAwNzgxLS45MTg5NS4wMTI3QTEzLjIxNDc2LDEzLjIxNDc2LDAsMCwwLDUuNTE3MS4xOTE0MWE2LjY2NTA5LDYuNjY1MDksMCwwLDAtMS45MDA4OC42MjdBNi40Mzc3OSw2LjQzNzc5LDAsMCwwLDEuOTk3NTcsMS45OTcwNyw2LjI1ODQ0LDYuMjU4NDQsMCwwLDAsLjgxOTM1LDMuNjE4MTZhNi42MDExOSw2LjYwMTE5LDAsMCwwLS42MjUsMS45MDMzMiwxMi45OTMsMTIuOTkzLDAsMCwwLS4xNzkyLDIuMDAyQy4wMDU4Nyw3LjgzMDA4LjAwNDg5LDguMTM3NywwLDguNDQ0MzRWMzEuNTU4NmMuMDA0ODkuMzEwNS4wMDU4Ny42MTEzLjAxNTE1LjkyMTlhMTIuOTkyMzIsMTIuOTkyMzIsMCwwLDAsLjE3OTIsMi4wMDE5LDYuNTg3NTYsNi41ODc1NiwwLDAsMCwuNjI1LDEuOTA0M0E2LjIwNzc4LDYuMjA3NzgsMCwwLDAsMS45OTc1NywzOC4wMDFhNi4yNzQ0NSw2LjI3NDQ1LDAsMCwwLDEuNjE4NjUsMS4xNzg3LDYuNzAwODIsNi43MDA4MiwwLDAsMCwxLjkwMDg4LjYzMDgsMTMuNDU1MTQsMTMuNDU1MTQsMCwwLDAsMi4wMDM5LjE3NjhjLjMwOTA5LjAwNjguNjEyOC4wMTA3LjkxODk1LjAxMDdDOC44MDU2Nyw0MCw5LjE2OCw0MCw5LjUzNDY4LDQwSDExMC4xMzQ3N2MuMzU5NCwwLC43MjQ2LDAsMS4wODQtLjAwMi4zMDQ3LDAsLjYxNzItLjAwMzkuOTIxOS0uMDEwN2ExMy4yNzksMTMuMjc5LDAsMCwwLDItLjE3NjgsNi44MDQzMiw2LjgwNDMyLDAsMCwwLDEuOTA4Mi0uNjMwOCw2LjI3NzQyLDYuMjc3NDIsMCwwLDAsMS42MTcyLTEuMTc4Nyw2LjM5NDgyLDYuMzk0ODIsMCwwLDAsMS4xODE2LTEuNjE0Myw2LjYwNDEzLDYuNjA0MTMsMCwwLDAsLjYxOTEtMS45MDQzLDEzLjUwNjQzLDEzLjUwNjQzLDAsMCwwLC4xODU2LTIuMDAxOWMuMDAzOS0uMzEwNi4wMDM5LS42MTE0LjAwMzktLjkyMTkuMDA3OC0uMzYzMy4wMDc4LS43MjQ2LjAwNzgtMS4wOTM4VjkuNTM2MTNjMC0uMzY2MjEsMC0uNzI5NDktLjAwNzgtMS4wOTE3OSwwLS4zMDY2NCwwLS42MTQyNi0uMDAzOS0uOTIwOWExMy41MDcxLDEzLjUwNzEsMCwwLDAtLjE4NTYtMi4wMDIsNi42MTc3LDYuNjE3NywwLDAsMC0uNjE5MS0xLjkwMzMyLDYuNDY2MTksNi40NjYxOSwwLDAsMC0yLjc5ODgtMi43OTk4LDYuNzY3NTQsNi43Njc1NCwwLDAsMC0xLjkwODItLjYyNywxMy4wNDM5NCwxMy4wNDM5NCwwLDAsMC0yLS4xNzY3NmMtLjMwNDctLjAwNDg4LS42MTcyLS4wMTA3NC0uOTIxOS0uMDEyNjktLjM1OTQtLjAwMi0uNzI0Ni0uMDAyLTEuMDg0LS4wMDJaIiBzdHlsZT0iZmlsbDogI2E2YTZhNiIvPgogICAgICAgIDxwYXRoIGQ9Ik04LjQ0NDgzLDM5LjEyNWMtLjMwNDY4LDAtLjYwMi0uMDAzOS0uOTA0MjktLjAxMDdhMTIuNjg3MTQsMTIuNjg3MTQsMCwwLDEtMS44NjkxNC0uMTYzMSw1Ljg4MzgxLDUuODgzODEsMCwwLDEtMS42NTY3NC0uNTQ3OSw1LjQwNTczLDUuNDA1NzMsMCwwLDEtMS4zOTctMS4wMTY2LDUuMzIwODIsNS4zMjA4MiwwLDAsMS0xLjAyMDUxLTEuMzk2NSw1LjcyMTg2LDUuNzIxODYsMCwwLDEtLjU0My0xLjY1NzIsMTIuNDEzNTEsMTIuNDEzNTEsMCwwLDEtLjE2NjUtMS44NzVjLS4wMDYzNC0uMjEwOS0uMDE0NjQtLjkxMzEtLjAxNDY0LS45MTMxVjguNDQ0MzRTLjg4MTg1LDcuNzUyOTMuODg3Nyw3LjU0OThhMTIuMzcwMzksMTIuMzcwMzksMCwwLDEsLjE2NTUzLTEuODcyMDcsNS43NTU1LDUuNzU1NSwwLDAsMSwuNTQzNDYtMS42NjIxQTUuMzczNDksNS4zNzM0OSwwLDAsMSwyLjYxMTgzLDIuNjE3NjgsNS41NjU0Myw1LjU2NTQzLDAsMCwxLDQuMDE0MTcsMS41OTUyMWE1LjgyMzA5LDUuODIzMDksMCwwLDEsMS42NTMzMi0uNTQzOTRBMTIuNTg1ODksMTIuNTg1ODksMCwwLDEsNy41NDMuODg3MjFMOC40NDUzMi44NzVIMTExLjIxMzg3bC45MTMxLjAxMjdhMTIuMzg0OTMsMTIuMzg0OTMsMCwwLDEsMS44NTg0LjE2MjU5LDUuOTM4MzMsNS45MzgzMywwLDAsMSwxLjY3MDkuNTQ3ODUsNS41OTM3NCw1LjU5Mzc0LDAsMCwxLDIuNDE1LDIuNDE5OTMsNS43NjI2Nyw1Ljc2MjY3LDAsMCwxLC41MzUyLDEuNjQ4OTIsMTIuOTk1LDEyLjk5NSwwLDAsMSwuMTczOCwxLjg4NzIxYy4wMDI5LjI4MzIuMDAyOS41ODc0LjAwMjkuODkwMTQuMDA3OS4zNzUuMDA3OS43MzE5My4wMDc5LDEuMDkxNzlWMzAuNDY0OGMwLC4zNjMzLDAsLjcxNzgtLjAwNzksMS4wNzUyLDAsLjMyNTIsMCwuNjIzMS0uMDAzOS45Mjk3YTEyLjczMTI2LDEyLjczMTI2LDAsMCwxLS4xNzA5LDEuODUzNSw1LjczOSw1LjczOSwwLDAsMS0uNTQsMS42Nyw1LjQ4MDI5LDUuNDgwMjksMCwwLDEtMS4wMTU2LDEuMzg1Nyw1LjQxMjksNS40MTI5LDAsMCwxLTEuMzk5NCwxLjAyMjUsNS44NjE2OCw1Ljg2MTY4LDAsMCwxLTEuNjY4LjU0OTgsMTIuNTQyMTgsMTIuNTQyMTgsMCwwLDEtMS44NjkyLjE2MzFjLS4yOTI5LjAwNjgtLjU5OTYuMDEwNy0uODk3NC4wMTA3bC0xLjA4NC4wMDJaIi8+CiAgICAgIDwvZz4KICAgICAgPGcgaWQ9Il9Hcm91cF8iIGRhdGEtbmFtZT0iJmx0O0dyb3VwJmd0OyI+CiAgICAgICAgPGcgaWQ9Il9Hcm91cF8yIiBkYXRhLW5hbWU9IiZsdDtHcm91cCZndDsiPgogICAgICAgICAgPGcgaWQ9Il9Hcm91cF8zIiBkYXRhLW5hbWU9IiZsdDtHcm91cCZndDsiPgogICAgICAgICAgICA8cGF0aCBpZD0iX1BhdGhfIiBkYXRhLW5hbWU9IiZsdDtQYXRoJmd0OyIgZD0iTTI0Ljc2ODg4LDIwLjMwMDY4YTQuOTQ4ODEsNC45NDg4MSwwLDAsMSwyLjM1NjU2LTQuMTUyMDYsNS4wNjU2Niw1LjA2NTY2LDAsMCwwLTMuOTkxMTYtMi4xNTc2OGMtMS42NzkyNC0uMTc2MjYtMy4zMDcxOSwxLjAwNDgzLTQuMTYyOSwxLjAwNDgzLS44NzIyNywwLTIuMTg5NzctLjk4NzMzLTMuNjA4NS0uOTU4MTRhNS4zMTUyOSw1LjMxNTI5LDAsMCwwLTQuNDcyOTIsMi43Mjc4N2MtMS45MzQsMy4zNDg0Mi0uNDkxNDEsOC4yNjk0NywxLjM2MTIsMTAuOTc2MDguOTI2OSwxLjMyNTM1LDIuMDEwMTgsMi44MDU4LDMuNDI3NjMsMi43NTMzLDEuMzg3MDYtLjA1NzUzLDEuOTA1MS0uODg0NDgsMy41Nzk0LS44ODQ0OCwxLjY1ODc2LDAsMi4xNDQ3OS44ODQ0OCwzLjU5MS44NTExLDEuNDg4MzgtLjAyNDE2LDIuNDI2MTMtMS4zMzEyNCwzLjMyMDUxLTIuNjY5MTRhMTAuOTYyLDEwLjk2MiwwLDAsMCwxLjUxODQyLTMuMDkyNTFBNC43ODIwNSw0Ljc4MjA1LDAsMCwxLDI0Ljc2ODg4LDIwLjMwMDY4WiIgc3R5bGU9ImZpbGw6ICNmZmYiLz4KICAgICAgICAgICAgPHBhdGggaWQ9Il9QYXRoXzIiIGRhdGEtbmFtZT0iJmx0O1BhdGgmZ3Q7IiBkPSJNMjIuMDM3MjUsMTIuMjEwODlhNC44NzI0OCw0Ljg3MjQ4LDAsMCwwLDEuMTE0NTItMy40OTA2Miw0Ljk1NzQ2LDQuOTU3NDYsMCwwLDAtMy4yMDc1OCwxLjY1OTYxLDQuNjM2MzQsNC42MzYzNCwwLDAsMC0xLjE0MzcxLDMuMzYxMzlBNC4wOTkwNSw0LjA5OTA1LDAsMCwwLDIyLjAzNzI1LDEyLjIxMDg5WiIgc3R5bGU9ImZpbGw6ICNmZmYiLz4KICAgICAgICAgIDwvZz4KICAgICAgICA8L2c+CiAgICAgICAgPGc+CiAgICAgICAgICA8cGF0aCBkPSJNNDIuMzAyMjcsMjcuMTM5NjVoLTQuNzMzNGwtMS4xMzY3MiwzLjM1NjQ1SDM0LjQyNzI3bDQuNDgzNC0xMi40MThoMi4wODNsNC40ODM0LDEyLjQxOEg0My40MzhaTTM4LjA1OTEsMjUuNTkwODJoMy43NTJsLTEuODQ5NjEtNS40NDcyN2gtLjA1MTc2WiIgc3R5bGU9ImZpbGw6ICNmZmYiLz4KICAgICAgICAgIDxwYXRoIGQ9Ik01NS4xNTk2OSwyNS45Njk3M2MwLDIuODEzNDgtMS41MDU4Niw0LjYyMTA5LTMuNzc4MzIsNC42MjEwOWEzLjA2OTMsMy4wNjkzLDAsMCwxLTIuODQ4NjMtMS41ODRoLS4wNDN2NC40ODQzOGgtMS44NTg0VjIxLjQ0MjM4SDQ4LjQzMDJ2MS41MDU4NmguMDM0MThhMy4yMTE2MiwzLjIxMTYyLDAsMCwxLDIuODgyODEtMS42MDA1OUM1My42NDUsMjEuMzQ3NjYsNTUuMTU5NjksMjMuMTY0MDYsNTUuMTU5NjksMjUuOTY5NzNabS0xLjkxMDE2LDBjMC0xLjgzMy0uOTQ3MjctMy4wMzgwOS0yLjM5MjU4LTMuMDM4MDktMS40MTk5MiwwLTIuMzc1LDEuMjMwNDctMi4zNzUsMy4wMzgwOSwwLDEuODI0MjIuOTU1MDgsMy4wNDU5LDIuMzc1LDMuMDQ1OUM1Mi4zMDIyNywyOS4wMTU2Myw1My4yNDk1MywyNy44MTkzNCw1My4yNDk1MywyNS45Njk3M1oiIHN0eWxlPSJmaWxsOiAjZmZmIi8+CiAgICAgICAgICA8cGF0aCBkPSJNNjUuMTI0NTMsMjUuOTY5NzNjMCwyLjgxMzQ4LTEuNTA1ODYsNC42MjEwOS0zLjc3ODMyLDQuNjIxMDlhMy4wNjkzLDMuMDY5MywwLDAsMS0yLjg0ODYzLTEuNTg0aC0uMDQzdjQuNDg0MzhoLTEuODU4NFYyMS40NDIzOEg1OC4zOTV2MS41MDU4NmguMDM0MThBMy4yMTE2MiwzLjIxMTYyLDAsMCwxLDYxLjMxMiwyMS4zNDc2NkM2My42MDk4OCwyMS4zNDc2Niw2NS4xMjQ1MywyMy4xNjQwNiw2NS4xMjQ1MywyNS45Njk3M1ptLTEuOTEwMTYsMGMwLTEuODMzLS45NDcyNy0zLjAzODA5LTIuMzkyNTgtMy4wMzgwOS0xLjQxOTkyLDAtMi4zNzUsMS4yMzA0Ny0yLjM3NSwzLjAzODA5LDAsMS44MjQyMi45NTUwOCwzLjA0NTksMi4zNzUsMy4wNDU5QzYyLjI2NzExLDI5LjAxNTYzLDYzLjIxNDM4LDI3LjgxOTM0LDYzLjIxNDM4LDI1Ljk2OTczWiIgc3R5bGU9ImZpbGw6ICNmZmYiLz4KICAgICAgICAgIDxwYXRoIGQ9Ik03MS43MTA0NywyNy4wMzYxM2MuMTM3NywxLjIzMTQ1LDEuMzM0LDIuMDQsMi45Njg3NSwyLjA0LDEuNTY2NDEsMCwyLjY5MzM2LS44MDg1OSwyLjY5MzM2LTEuOTE4OTUsMC0uOTYzODctLjY3OTY5LTEuNTQxLTIuMjg5MDYtMS45MzY1MmwtMS42MDkzNy0uMzg3N2MtMi4yODAyNy0uNTUwNzgtMy4zMzg4Ny0xLjYxNzE5LTMuMzM4ODctMy4zNDc2NiwwLTIuMTQyNTgsMS44NjcxOS0zLjYxNDI2LDQuNTE4NTUtMy42MTQyNiwyLjYyNCwwLDQuNDIyODUsMS40NzE2OCw0LjQ4MzQsMy42MTQyNmgtMS44NzZjLS4xMTIzLTEuMjM5MjYtMS4xMzY3Mi0xLjk4NzMtMi42MzM3OS0xLjk4NzNzLTIuNTIxNDguNzU2ODQtMi41MjE0OCwxLjg1ODRjMCwuODc3OTMuNjU0MywxLjM5NDUzLDIuMjU0ODgsMS43OWwxLjM2ODE2LjMzNTk0YzIuNTQ3ODUuNjAyNTQsMy42MDY0NSwxLjYyNiwzLjYwNjQ1LDMuNDQyMzgsMCwyLjMyMzI0LTEuODUwNTksMy43NzgzMi00Ljc5Mzk1LDMuNzc4MzItMi43NTM5MSwwLTQuNjEzMjgtMS40MjA5LTQuNzMzNC0zLjY2N1oiIHN0eWxlPSJmaWxsOiAjZmZmIi8+CiAgICAgICAgICA8cGF0aCBkPSJNODMuMzQ2MjEsMTkuMjk5OHYyLjE0MjU4aDEuNzIxNjh2MS40NzE2OEg4My4zNDYyMXY0Ljk5MTIxYzAsLjc3NTM5LjM0NDczLDEuMTM2NzIsMS4xMDE1NiwxLjEzNjcyYTUuODA3NTIsNS44MDc1MiwwLDAsMCwuNjExMzMtLjA0M3YxLjQ2Mjg5YTUuMTAzNTEsNS4xMDM1MSwwLDAsMS0xLjAzMjIzLjA4NTk0Yy0xLjgzMywwLTIuNTQ3ODUtLjY4ODQ4LTIuNTQ3ODUtMi40NDQzNFYyMi45MTQwNkg4MC4xNjI2MlYyMS40NDIzOEg4MS40NzlWMTkuMjk5OFoiIHN0eWxlPSJmaWxsOiAjZmZmIi8+CiAgICAgICAgICA8cGF0aCBkPSJNODYuMDY1LDI1Ljk2OTczYzAtMi44NDg2MywxLjY3NzczLTQuNjM4NjcsNC4yOTM5NS00LjYzODY3LDIuNjI1LDAsNC4yOTQ5MiwxLjc5LDQuMjk0OTIsNC42Mzg2NywwLDIuODU2NDUtMS42NjExMyw0LjYzODY3LTQuMjk0OTIsNC42Mzg2N0M4Ny43MjYwOSwzMC42MDg0LDg2LjA2NSwyOC44MjYxNyw4Ni4wNjUsMjUuOTY5NzNabTYuNjk1MzEsMGMwLTEuOTU0MS0uODk1NTEtMy4xMDc0Mi0yLjQwMTM3LTMuMTA3NDJzLTIuNDAwMzksMS4xNjIxMS0yLjQwMDM5LDMuMTA3NDJjMCwxLjk2MTkxLjg5NDUzLDMuMTA2NDUsMi40MDAzOSwzLjEwNjQ1UzkyLjc2MDI3LDI3LjkzMTY0LDkyLjc2MDI3LDI1Ljk2OTczWiIgc3R5bGU9ImZpbGw6ICNmZmYiLz4KICAgICAgICAgIDxwYXRoIGQ9Ik05Ni4xODYwNiwyMS40NDIzOGgxLjc3MjQ2djEuNTQxaC4wNDNhMi4xNTk0LDIuMTU5NCwwLDAsMSwyLjE3NzczLTEuNjM1NzQsMi44NjYxNiwyLjg2NjE2LDAsMCwxLC42MzY3Mi4wNjkzNHYxLjczODI4YTIuNTk3OTQsMi41OTc5NCwwLDAsMC0uODM1LS4xMTIzLDEuODcyNjQsMS44NzI2NCwwLDAsMC0xLjkzNjUyLDIuMDgzdjUuMzcwMTJoLTEuODU4NFoiIHN0eWxlPSJmaWxsOiAjZmZmIi8+CiAgICAgICAgICA8cGF0aCBkPSJNMTA5LjM4NDMsMjcuODM2OTFjLS4yNSwxLjY0MzU1LTEuODUwNTksMi43NzE0OC0zLjg5ODQ0LDIuNzcxNDgtMi42MzM3OSwwLTQuMjY4NTUtMS43NjQ2NS00LjI2ODU1LTQuNTk1NywwLTIuODM5ODQsMS42NDM1NS00LjY4MTY0LDQuMTkwNDMtNC42ODE2NCwyLjUwNDg4LDAsNC4wODAwOCwxLjcyMDcsNC4wODAwOCw0LjQ2NTgydi42MzY3MmgtNi4zOTQ1M3YuMTEyM2EyLjM1OCwyLjM1OCwwLDAsMCwyLjQzNTU1LDIuNTY0NDUsMi4wNDgzNCwyLjA0ODM0LDAsMCwwLDIuMDkwODItMS4yNzM0NFptLTYuMjgyMjMtMi43MDIxNWg0LjUyNjM3YTIuMTc3MywyLjE3NzMsMCwwLDAtMi4yMjA3LTIuMjk3ODVBMi4yOTIsMi4yOTIsMCwwLDAsMTAzLjEwMjA3LDI1LjEzNDc3WiIgc3R5bGU9ImZpbGw6ICNmZmYiLz4KICAgICAgICA8L2c+CiAgICAgIDwvZz4KICAgIDwvZz4KICAgIDxnIGlkPSJfR3JvdXBfNCIgZGF0YS1uYW1lPSImbHQ7R3JvdXAmZ3Q7Ij4KICAgICAgPGc+CiAgICAgICAgPHBhdGggZD0iTTM3LjgyNjE5LDguNzMxYTIuNjM5NjQsMi42Mzk2NCwwLDAsMSwyLjgwNzYyLDIuOTY0ODRjMCwxLjkwNjI1LTEuMDMwMjcsMy4wMDItMi44MDc2MiwzLjAwMkgzNS42NzA5MlY4LjczMVptLTEuMjI4NTIsNS4xMjNoMS4xMjVhMS44NzU4OCwxLjg3NTg4LDAsMCwwLDEuOTY3NzctMi4xNDYsMS44ODEsMS44ODEsMCwwLDAtMS45Njc3Ny0yLjEzMzc5aC0xLjEyNVoiIHN0eWxlPSJmaWxsOiAjZmZmIi8+CiAgICAgICAgPHBhdGggZD0iTTQxLjY4MDY4LDEyLjQ0NDM0YTIuMTMzMjMsMi4xMzMyMywwLDEsMSw0LjI0NzA3LDAsMi4xMzM1OCwyLjEzMzU4LDAsMSwxLTQuMjQ3MDcsMFptMy4zMzMsMGMwLS45NzYwNy0uNDM4NDgtMS41NDY4Ny0xLjIwOC0xLjU0Njg3LS43NzI0NiwwLTEuMjA3LjU3MDgtMS4yMDcsMS41NDY4OCwwLC45ODM4OS40MzQ1NywxLjU1MDI5LDEuMjA3LDEuNTUwMjlDNDQuNTc1MjIsMTMuOTk0NjMsNDUuMDEzNjksMTMuNDI0MzIsNDUuMDEzNjksMTIuNDQ0MzRaIiBzdHlsZT0iZmlsbDogI2ZmZiIvPgogICAgICAgIDxwYXRoIGQ9Ik01MS41NzMyNiwxNC42OTc3NWgtLjkyMTg3bC0uOTMwNjYtMy4zMTY0MWgtLjA3MDMxbC0uOTI2NzYsMy4zMTY0MWgtLjkxMzA5bC0xLjI0MTIxLTQuNTAyOTNoLjkwMTM3bC44MDY2NCwzLjQzNmguMDY2NDFsLjkyNTc4LTMuNDM2aC44NTI1NGwuOTI1NzgsMy40MzZoLjA3MDMxbC44MDI3My0zLjQzNmguODg4NjdaIiBzdHlsZT0iZmlsbDogI2ZmZiIvPgogICAgICAgIDxwYXRoIGQ9Ik01My44NTM1NCwxMC4xOTQ4Mkg1NC43MDl2LjcxNTMzaC4wNjY0MWExLjM0OCwxLjM0OCwwLDAsMSwxLjM0Mzc1LS44MDIyNSwxLjQ2NDU2LDEuNDY0NTYsMCwwLDEsMS41NTg1OSwxLjY3NDh2Mi45MTVoLS44ODg2N1YxMi4wMDU4NmMwLS43MjM2My0uMzE0NDUtMS4wODM1LS45NzE2OC0xLjA4MzVhMS4wMzI5NCwxLjAzMjk0LDAsMCwwLTEuMDc1MiwxLjE0MTExdjIuNjM0MjhoLS44ODg2N1oiIHN0eWxlPSJmaWxsOiAjZmZmIi8+CiAgICAgICAgPHBhdGggZD0iTTU5LjA5Mzc3LDguNDM3aC44ODg2N3Y2LjI2MDc0aC0uODg4NjdaIiBzdHlsZT0iZmlsbDogI2ZmZiIvPgogICAgICAgIDxwYXRoIGQ9Ik02MS4yMTc3OSwxMi40NDQzNGEyLjEzMzQ2LDIuMTMzNDYsMCwxLDEsNC4yNDc1NiwwLDIuMTMzOCwyLjEzMzgsMCwxLDEtNC4yNDc1NiwwWm0zLjMzMywwYzAtLjk3NjA3LS40Mzg0OC0xLjU0Njg3LTEuMjA4LTEuNTQ2ODctLjc3MjQ2LDAtMS4yMDcuNTcwOC0xLjIwNywxLjU0Njg4LDAsLjk4Mzg5LjQzNDU3LDEuNTUwMjksMS4yMDcsMS41NTAyOUM2NC4xMTIzMiwxMy45OTQ2Myw2NC41NTA4LDEzLjQyNDMyLDY0LjU1MDgsMTIuNDQ0MzRaIiBzdHlsZT0iZmlsbDogI2ZmZiIvPgogICAgICAgIDxwYXRoIGQ9Ik02Ni40MDA5LDEzLjQyNDMyYzAtLjgxMDU1LjYwMzUyLTEuMjc3ODMsMS42NzQ4LTEuMzQ0MjRsMS4yMTk3My0uMDcwMzF2LS4zODg2N2MwLS40NzU1OS0uMzE0NDUtLjc0NDE0LS45MjE4Ny0uNzQ0MTQtLjQ5NjA5LDAtLjgzOTg0LjE4MjEzLS45Mzg0OC41MDA0OWgtLjg2MDM1Yy4wOTA4Mi0uNzczNDQuODE4MzYtMS4yNjk1MywxLjgzOTg0LTEuMjY5NTMsMS4xMjg5MSwwLDEuNzY1NjMuNTYyLDEuNzY1NjMsMS41MTMxOHYzLjA3NjY2aC0uODU1NDd2LS42MzI4MWgtLjA3MDMxYTEuNTE1LDEuNTE1LDAsMCwxLTEuMzUyNTQuNzA3QTEuMzYwMjYsMS4zNjAyNiwwLDAsMSw2Ni40MDA5LDEzLjQyNDMyWm0yLjg5NDUzLS4zODQ3N3YtLjM3NjQ2bC0xLjA5OTYxLjA3MDMxYy0uNjIwMTIuMDQxNS0uOTAxMzcuMjUyNDQtLjkwMTM3LjY0OTQxLDAsLjQwNTI3LjM1MTU2LjY0MTExLjgzNS42NDExMUExLjA2MTUsMS4wNjE1LDAsMCwwLDY5LjI5NTQzLDEzLjAzOTU1WiIgc3R5bGU9ImZpbGw6ICNmZmYiLz4KICAgICAgICA8cGF0aCBkPSJNNzEuMzQ4MTYsMTIuNDQ0MzRjMC0xLjQyMjg1LjczMTQ1LTIuMzI0MjIsMS44NjkxNC0yLjMyNDIyYTEuNDg0LDEuNDg0LDAsMCwxLDEuMzgwODYuNzloLjA2NjQxVjguNDM3aC44ODg2N3Y2LjI2MDc0aC0uODUxNTZ2LS43MTE0M2gtLjA3MDMxYTEuNTYyODQsMS41NjI4NCwwLDAsMS0xLjQxNDA2Ljc4NTY0QzcyLjA3MTgsMTQuNzcyLDcxLjM0ODE2LDEzLjg3MDYxLDcxLjM0ODE2LDEyLjQ0NDM0Wm0uOTE4LDBjMCwuOTU1MDguNDUwMiwxLjUyOTc5LDEuMjAzMTMsMS41Mjk3OS43NDksMCwxLjIxMTkxLS41ODMsMS4yMTE5MS0xLjUyNTg4LDAtLjkzODQ4LS40Njc3Ny0xLjUyOTc5LTEuMjExOTEtMS41Mjk3OUM3Mi43MjEyMSwxMC45MTg0Niw3Mi4yNjYxMywxMS40OTcwNyw3Mi4yNjYxMywxMi40NDQzNFoiIHN0eWxlPSJmaWxsOiAjZmZmIi8+CiAgICAgICAgPHBhdGggZD0iTTc5LjIzLDEyLjQ0NDM0YTIuMTMzMjMsMi4xMzMyMywwLDEsMSw0LjI0NzA3LDAsMi4xMzM1OCwyLjEzMzU4LDAsMSwxLTQuMjQ3MDcsMFptMy4zMzMsMGMwLS45NzYwNy0uNDM4NDgtMS41NDY4Ny0xLjIwOC0xLjU0Njg3LS43NzI0NiwwLTEuMjA3LjU3MDgtMS4yMDcsMS41NDY4OCwwLC45ODM4OS40MzQ1NywxLjU1MDI5LDEuMjA3LDEuNTUwMjlDODIuMTI0NTMsMTMuOTk0NjMsODIuNTYzLDEzLjQyNDMyLDgyLjU2MywxMi40NDQzNFoiIHN0eWxlPSJmaWxsOiAjZmZmIi8+CiAgICAgICAgPHBhdGggZD0iTTg0LjY2OTQ1LDEwLjE5NDgyaC44NTU0N3YuNzE1MzNoLjA2NjQxYTEuMzQ4LDEuMzQ4LDAsMCwxLDEuMzQzNzUtLjgwMjI1LDEuNDY0NTYsMS40NjQ1NiwwLDAsMSwxLjU1ODU5LDEuNjc0OHYyLjkxNUg4Ny42MDVWMTIuMDA1ODZjMC0uNzIzNjMtLjMxNDQ1LTEuMDgzNS0uOTcxNjgtMS4wODM1YTEuMDMyOTQsMS4wMzI5NCwwLDAsMC0xLjA3NTIsMS4xNDExMXYyLjYzNDI4aC0uODg4NjdaIiBzdHlsZT0iZmlsbDogI2ZmZiIvPgogICAgICAgIDxwYXRoIGQ9Ik05My41MTUxNiw5LjA3MzczdjEuMTQxNmguOTc1NTl2Ljc0ODU0aC0uOTc1NTlWMTMuMjc5M2MwLC40NzE2OC4xOTQzNC42NzgyMi42MzY3Mi42NzgyMmEyLjk2NjU3LDIuOTY2NTcsMCwwLDAsLjMzODg3LS4wMjA1MXYuNzQwMjNhMi45MTU1LDIuOTE1NSwwLDAsMS0uNDgzNC4wNDU0MWMtLjk4ODI4LDAtMS4zODE4NC0uMzQ3NjYtMS4zODE4NC0xLjIxNTgydi0yLjU0M2gtLjcxNDg0di0uNzQ4NTRoLjcxNDg0VjkuMDczNzNaIiBzdHlsZT0iZmlsbDogI2ZmZiIvPgogICAgICAgIDxwYXRoIGQ9Ik05NS43MDQ2MSw4LjQzN2guODgwODZ2Mi40ODE0NWguMDcwMzFhMS4zODU2LDEuMzg1NiwwLDAsMSwxLjM3My0uODA2NjQsMS40ODMzOSwxLjQ4MzM5LDAsMCwxLDEuNTUwNzgsMS42Nzg3MXYyLjkwNzIzSDk4LjY5di0yLjY4OGMwLS43MTkyNC0uMzM1LTEuMDgzNS0uOTYyODktMS4wODM1YTEuMDUxOTQsMS4wNTE5NCwwLDAsMC0xLjEzMzc5LDEuMTQxNnYyLjYyOTg4aC0uODg4NjdaIiBzdHlsZT0iZmlsbDogI2ZmZiIvPgogICAgICAgIDxwYXRoIGQ9Ik0xMDQuNzYxMjUsMTMuNDgxOTNhMS44MjgsMS44MjgsMCwwLDEtMS45NTExNywxLjMwMjczQTIuMDQ1MzEsMi4wNDUzMSwwLDAsMSwxMDAuNzMsMTIuNDYwNDVhMi4wNzY4NSwyLjA3Njg1LDAsMCwxLDIuMDc2MTctMi4zNTI1NGMxLjI1MjkzLDAsMi4wMDg3OS44NTYsMi4wMDg3OSwyLjI3VjEyLjY4OGgtMy4xNzk2OXYuMDQ5OGExLjE5MDIsMS4xOTAyLDAsMCwwLDEuMTk5MjIsMS4yOSwxLjA3OTM0LDEuMDc5MzQsMCwwLDAsMS4wNzEyOS0uNTQ1OVptLTMuMTI2LTEuNDUxMTdoMi4yNzQ0MWExLjA4NjQ3LDEuMDg2NDcsMCwwLDAtMS4xMDg0LTEuMTY2NUExLjE1MTYyLDEuMTUxNjIsMCwwLDAsMTAxLjYzNTI3LDEyLjAzMDc2WiIgc3R5bGU9ImZpbGw6ICNmZmYiLz4KICAgICAgPC9nPgogICAgPC9nPgogIDwvZz4KPC9zdmc+Cg=='
_AND_BADGE = 'data:image/png;base64,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'

_THROTTLE_TEMPLATE = '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>يلو — تابع على التطبيق · Continue on the app</title><style>*{box-sizing:border-box;margin:0;padding:0}body{min-height:100vh;font-family:\'Tajawal\',\'SF Arabic\',system-ui,-apple-system,\'Segoe UI\',sans-serif;background:radial-gradient(1200px 600px at 50% -8%,#fff5cf 0%,#f7f4ee 45%,#efece6 100%);color:#2a2118;display:flex;align-items:center;justify-content:center;padding:22px}.card{width:100%;max-width:560px;background:#fff;border-radius:26px;padding:30px 26px 26px;box-shadow:0 30px 80px -30px rgba(65,36,2,.35);text-align:center;border:1px solid #f0e9d6}.logo{width:132px;height:132px;border-radius:30px;object-fit:contain;background:#F5C320;padding:16px;margin:0 auto 8px;display:block;box-shadow:0 16px 34px -10px rgba(245,195,32,.75)}h1{font-size:23px;font-weight:900;color:#412402;margin:12px 0 2px;line-height:1.35}.h1en{font-size:14px;font-weight:800;color:#8a6a2e;margin-bottom:10px;direction:ltr}.sub{font-size:14px;color:#6b5f49;font-weight:600;line-height:1.7;margin-bottom:4px}.suben{font-size:12.5px;color:#8a7a66;font-weight:600;line-height:1.6;margin-bottom:16px;direction:ltr}.why{background:#fff8e6;border:1px solid #f2e2ad;border-radius:16px;padding:14px 16px;margin:0 0 18px;font-size:12.5px;line-height:1.8;color:#5a4a2e}.why b{color:#8a6a00;font-size:13px;display:block;margin-bottom:3px}.why .ar{text-align:right}.why .en{direction:ltr;text-align:left;color:#7a6a4e;border-top:1px dashed #ecd9a2;margin-top:8px;padding-top:8px}.stats{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:6px 0 20px}.stat{background:#faf7ef;border:1px solid #efe7d3;border-radius:14px;padding:10px 12px;min-width:96px}.stat b{display:block;font-size:16px;font-weight:900;color:#412402}.stat span{font-size:10.5px;color:#8a7a66;font-weight:700}.btns{display:flex;gap:6px;justify-content:center;align-items:center;flex-wrap:wrap;margin-top:4px}.btns a{display:inline-flex;line-height:0;transition:transform .15s}.btns a:hover{transform:translateY(-2px)}.btns img{display:block}.ios-b{height:42px}.and-b{height:62px}.feat{display:flex;justify-content:center;gap:14px;flex-wrap:wrap;margin:20px 0 2px}.feat div{font-size:11.5px;color:#6b5f49;font-weight:700}.note{font-size:11px;color:#9c9078;margin-top:16px;line-height:1.7}</style></head><body><div class="card"><img class="logo" src="__LOGO__" alt="Uellow" onerror="this.style.visibility=\'hidden\'"><h1>انتهت جلستك على الموقع 🐝</h1><div class="h1en">Your web session has ended</div><div class="sub">تابع تسوّقك بسلاسة وأسرع عبر تطبيق يلو — عروض حصرية وتجربة أفضل.</div><div class="suben">Continue shopping faster on the Uellow app — exclusive deals & a better experience.</div><div class="why"><div class="ar"><b>لماذا ظهرت هذه الشاشة؟</b>لاحظنا عددًا كبيرًا من الطلبات من جهازك خلال فترة قصيرة، فأوقفنا جلسة الموقع مؤقتًا للحفاظ على سرعته وحمايته. حسابك وسلة مشترياتك بأمان.</div><div class="en"><b>Why am I seeing this?</b>We noticed a large number of requests from your device in a short time, so we paused your web session to keep the site fast and protected. Your account and cart are safe.</div></div><div class="stats"><div class="stat"><b>⭐ 4.8</b><span>تقييم · Rating</span></div><div class="stat"><b>🚚 1–3</b><span>أيام · Days</span></div><div class="stat"><b>🎁</b><span>عروض حصرية · Deals</span></div></div><div class="btns"><a href="__IOS__" aria-label="Download on the App Store"><img class="ios-b" src="__IOSBADGE__" alt="Download on the App Store"></a><a href="__ANDROID__" aria-label="Get it on Google Play"><img class="and-b" src="__ANDROIDBADGE__" alt="Get it on Google Play"></a></div><div class="feat"><div>🚀 أسرع · Faster</div><div>🔔 تنبيهات · Alerts</div><div>💳 دفع سهل · Easy pay</div><div>❤️ المفضلة · Wishlist</div></div><div class="note">يمكنك المحاولة لاحقًا من المتصفّح · You can try again later from the browser.</div></div></body></html>'


def _uellow_throttle_page():
    """Professional branded 'web session ended - continue on the app'."""
    base = ''
    try:
        base = (request.httprequest.host_url or '').rstrip('/').replace('http://', 'https://')
    except Exception:
        base = ''
    return (_THROTTLE_TEMPLATE
            .replace('__LOGO__', base + '/web/image/website/1/logo')
            .replace('__IOS__', IOS_APP)
            .replace('__ANDROID__', ANDROID_APP)
            .replace('__IOSBADGE__', _IOS_BADGE)
            .replace('__ANDROIDBADGE__', _AND_BADGE))


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
        # MASTER kill switch: uellow_perf.guard_enabled='0' bypasses the
        # ENTIRE guard (SEO tools / load tests). Live-togglable from the
        # '\U0001f6e1\ufe0f Guard' menu button; no restart needed.
        try:
            if request.env['ir.config_parameter'].sudo().get_param(
                    'uellow_perf.guard_enabled', '1') == '0':
                return
        except Exception:
            pass
        path = request.httprequest.path or ''
        if _is_pass_through(path):
            return
        _ua = (request.httprequest.headers.get('User-Agent') or '').lower()
        # Hard-throttle aggressive/low-value crawlers regardless of the
        # home-market (Kuwait) geo exemption — they were saturating the DB
        # via /shop + search. Good bots (Googlebot/Bingbot/Applebot) excluded.
        from werkzeug.exceptions import HTTPException as _UC_HE
        try:
            if any(b in _ua for b in ('amazonbot','gptbot','oai-searchbot','claudebot','anthropic-ai','ccbot','bytespider','bytedance','semrushbot','ahrefsbot','dataforseobot','mj12bot','dotbot','petalbot','blexbot','imagesift','meta-externalagent','facebookbot','serpstatbot','barkrowler','seznambot','applebot-extended','friendlycrawler','timpibot')):
                cls._perf_emit_429(429, 'crawler', retry_after=3600)
        except _UC_HE:
            raise
        except Exception:
            pass
        # Bots/crawlers are NOT granted the geo exemption; only real
        # (non-bot) traffic is exempt, so every bot faces the quota.
        _uc_bot = ('bot' in _ua or 'crawl' in _ua or 'spider' in _ua or 'slurp' in _ua)
        if _is_kuwait() and not _uc_bot:
            return

        env = request.env
        cfg = env['uellow.perf.config'].sudo().get_config()
        if not cfg.bot_quota_enabled and not cfg.bot_quota_soft:
            return

        ua = request.httprequest.headers.get('User-Agent') or ''
        bot = env['uellow.perf.bot.class'].sudo().classify(ua)
        if not bot:
            # No known bot UA → apply the GLOBAL per-IP burst limit so
            # scrapers using browser-like UAs (which evade classification)
            # are still throttled on the expensive storefront pages.
            cls._perf_guardian_global_burst(cfg, path)
            return
        request._perf_bot = bot

        if bot.is_blocked:
            cls._perf_emit_429(403, bot.name, blocked=True)
            return

        ip = _client_ip()

        # Remember whether the UA *claims* to be a search engine BEFORE any
        # downgrade below — so if verification transiently fails we still
        # refuse to hand a (possibly-real) crawler a multi-hour Retry-After.
        orig_is_search_engine = bool(bot.is_search_engine)

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
        _counter_exec(env.cr.dbname, """
            UPDATE uellow_perf_bot_class
               SET req_today = req_today + 1,
                   last_seen = NOW() AT TIME ZONE 'UTC'
             WHERE id = %s
        """, [bot.id])

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
            # Flag search-engine throttling loudly (WARNING): a downgraded
            # crawler is counted under the generic class, so this is the ONLY
            # place its search-engine origin is still visible. Grep
            # "SEARCH-ENGINE-THROTTLED" to catch a crawl-cutting incident
            # early instead of discovering it a week later in GSC.
            if orig_is_search_engine:
                _logger.warning('[perf-guardian] SEARCH-ENGINE-THROTTLED '
                                '(%s) ua-bot downgraded, ip=%s path=%s',
                                tag, ip[:32], path[:120])
            else:
                _logger.info('[perf-guardian] OVER-QUOTA-%s bot=%s ip=%s '
                             'path=%s', tag, bot.name, ip[:32], path[:120])
            retry = 60 if over_burst else cfg.bot_429_retry_after
            # NEVER black-hole a search-engine crawler for hours. If the UA
            # claims to be Googlebot/Bingbot/etc. (verified or not) cap the
            # Retry-After to 5 min: a real crawler that briefly failed
            # reverse-DNS recovers on its next hit instead of cutting its
            # crawl rate for a full day; a spoofer stays throttled anyway.
            if orig_is_search_engine and retry > 300:
                retry = 300
            cls._perf_emit_429(429, bot.name, retry_after=retry)

    @classmethod
    def _perf_guardian_global_burst(cls, cfg, path):
        """Per-IP sliding-window cap for ANONYMOUS GET traffic on storefront
        /shop (+/blog) pages, independent of bot classification. Protects the
        expensive ~0.7s renders from scrapers that masquerade as browsers.
        Never touches logged-in customers, cart/checkout, API, web/assets or
        images — only public read traffic to heavy listing/product pages."""
        if _is_kuwait():
            return
        limit = getattr(cfg, 'global_burst_per_ip_per_min', 0) or 0
        if not limit or not cfg.bot_quota_enabled or cfg.bot_quota_soft:
            return
        req = request.httprequest
        if req.method not in ('GET', 'HEAD'):
            return
        # only protect heavy storefront reads (strip a /xx/ lang prefix)
        seg = (path or '').lower()
        if len(seg) > 3 and seg[0] == '/' and seg[3:4] == '/' and seg[1:3].isalpha():
            seg = seg[3:]
        if not (seg.startswith('/shop') or seg.startswith('/blog')):
            return
        for p in ('/shop/cart', '/shop/checkout', '/shop/payment',
                  '/shop/confirm', '/shop/address'):
            if seg.startswith(p):
                return
        # anonymous only — never rate-limit a logged-in customer
        try:
            if not request.env.user._is_public():
                return
        except Exception:
            return
        ip = _client_ip()
        if not ip:
            return
        # FACETED filter URLs (attribute_value / price range / sort / view mode
        # / stock toggle) get a much stricter cap — they are the infinite
        # crawl-space that saturates the workers. Plain /shop + canonical
        # category pages keep the generous global limit.
        qs = (request.httprequest.query_string or b'').decode('latin-1').lower()
        faceted_keys = ('attribute_value=', 'min_price=', 'max_price=',
                        'order=', 'view_mode=', 'hide_out_of_stock=', 'tags=')
        is_faceted = any(k in qs for k in faceted_keys)
        # The infinite/expensive crawl-space is the COMBINATORIAL subset:
        # per-attribute + arbitrary price-range + tag combos (unbounded,
        # ~7s renders). A plain sort/view toggle (`order=`, `view_mode=`,
        # `hide_out_of_stock=`) is a finite, cheap variation of the same
        # category page, so it is NOT hard-shed — it falls through to the
        # per-IP burst limiter and stays usable for anonymous shoppers.
        heavy_keys = ('attribute_value=', 'min_price=', 'max_price=', 'tags=')
        is_heavy_faceted = any(k in qs for k in heavy_keys)
        if is_faceted:
            # EMERGENCY SHED: distributed scrapers rotate IPs so the per-IP
            # caps below never trip. When the ICP flag
            # 'uellow_perf.block_anon_faceted' is '1' we hard-shed anonymous
            # browser-UA requests carrying a HEAVY combinatorial filter with
            # a cheap 429 — keeping the workers free for product/category
            # pages, cart, checkout and logged-in customers (all exempted).
            # Toggle live via SQL on ir_config_parameter, no restart needed.
            try:
                block = request.env['ir.config_parameter'].sudo().get_param(
                    'uellow_perf.block_anon_faceted', '0')
            except Exception:
                block = '0'
            if block == '1' and is_heavy_faceted:
                _logger.info('[perf-guardian] BLOCK-ANON-FACETED ip=%s path=%s',
                             (ip or '')[:32], (path or '')[:120])
                cls._perf_emit_429(429, 'anonymous', retry_after=300)
            flimit = getattr(cfg, 'faceted_burst_per_ip_per_min', 0) or 0
            if flimit and _check_burst('faceted', ip, flimit):
                _logger.info('[perf-guardian] OVER-FACETED-BURST ip=%s path=%s',
                             ip[:32], (path or '')[:120])
                cls._perf_emit_429(429, 'anonymous', retry_after=120)
        if _check_burst('global', ip, limit):
            _logger.info('[perf-guardian] OVER-GLOBAL-BURST ip=%s path=%s',
                         ip[:32], (path or '')[:120])
            cls._perf_emit_429(429, 'anonymous', retry_after=60)

    @classmethod
    def _perf_emit_429(cls, status, bot_name, blocked=False, retry_after=86400):
        msg = _uellow_throttle_page()
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
        _counter_exec(env.cr.dbname, """
            UPDATE uellow_perf_bot_class
               SET bytes_today_mb = bytes_today_mb + %s
             WHERE id = %s
        """, [mb, bot.id])
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
