# -*- coding: utf-8 -*-
# Copyright (c) 2019-Present Droggol Infotech Private Limited. (<https://www.droggol.com/>)

from odoo import models
from odoo.http import request
from werkzeug.exceptions import HTTPException, abort
from werkzeug.utils import redirect as _wredir

# Auto-translated "junk" locales to REMOVE from Google's index (kept HTTP 200,
# NOT robots-blocked, so Googlebot crawls them, SEES the noindex, and DROPS
# them). Keep 'ar'/'en' + the unprefixed default indexable.
_NOINDEX_LOCALES = frozenset({
    'bn_IN', 'sq', 'et', 'fr', 'de', 'hi', 'it', 'fa', 'es', 'sv', 'tr',
})


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _pre_dispatch(cls, rule, arguments):
        # Canonical host: 301 the bare apex (uellow.com) to www — the site
        # must not be served on two hosts (duplicate content). www + country
        # subdomains (sa/eg/om/...) are untouched. Raised so it is actually
        # served (_post_dispatch return value is ignored by core).
        try:
            _hr = request and request.httprequest
            _host = ((_hr and _hr.host) or '').split(':')[0].lower()
            if _host == 'uellow.com':
                _p = _hr.full_path or '/'
                if _p.endswith('?'):
                    _p = _p[:-1]
                abort(_wredir('https://www.uellow.com' + _p, code=301))
        except HTTPException:
            raise
        except Exception:
            pass
        return super()._pre_dispatch(rule, arguments)

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super(IrHttp, cls)._get_translation_frontend_modules_name()
        return mods + ['uellow_theme_common', 'uellow_theme']

    @classmethod
    def _post_dispatch(cls, response):
        try:
            hr = request and request.httprequest
            path = (hr and hr.path) or ''
            host = (hr and (hr.host or '')) or ''
            sub = host.split(':')[0].split('.')[0].lower()
            noindex = (
                # raw image endpoints + thin review pages
                path.startswith('/web/image/')
                or path.endswith('/reviews')
                or '/reviews/page/' in path
                # mobile-app / world API subdomains — not for the search index
                or sub == 'app' or sub == 'world' or sub.endswith('app')
            )
            if not noindex:
                # auto-translated junk-locale pages
                seg = path.split('/', 2)
                first = seg[1] if len(seg) > 1 else ''
                if first in _NOINDEX_LOCALES:
                    noindex = True
            if noindex and response is not None and hasattr(response, 'headers'):
                response.headers['X-Robots-Tag'] = 'noindex'
        except Exception:
            pass
        try:
            if response is not None and hasattr(response, 'headers'):
                response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')
        except Exception:
            pass
        return super()._post_dispatch(response)
