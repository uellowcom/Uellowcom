# -*- coding: utf-8 -*-
"""Cross-country hreflang cluster.

The 8 storefront country sites (www/us/sa/eg/qa/ae/kw/om) serve the same
catalogue. Odoo's core only emits per-site LANGUAGE hreflang (ar/en) within the
current domain, so Google saw the country subdomains as duplicates and indexed
only one version per product ("Crawled - currently not indexed" on the rest).

This emits a full reciprocal hreflang cluster on every canonical storefront
page: en-XX / ar-XX for each country site + generic en/ar + x-default -> www,
so Google indexes each regional version for its own market.
"""
import re
from odoo import models
from odoo.http import request

# storefront country subdomains -> ISO country code. www = international default.
_COUNTRY_SUBS = {'us', 'sa', 'eg', 'qa', 'ae', 'kw', 'om'}
_SUB_RE = re.compile(r'^https?://([a-z]+)\.uellow\.com', re.I)


class Website(models.Model):
    _inherit = 'website'

    def _uellow_is_store_site(self):
        """True when the CURRENT website is one of the indexable storefront
        country sites (not the app/world/B2B subdomains)."""
        m = _SUB_RE.match((self.domain or '').strip())
        if not m:
            return False
        sub = m.group(1).lower()
        return sub == 'www' or sub in _COUNTRY_SUBS

    def _uellow_neutral_path(self):
        """Current request path stripped of its language prefix (the default,
        English, has no prefix; others like /ar keep theirs)."""
        path = (request.httprequest.path or '/') if request and request.httprequest else '/'
        codes = {(l.url_code or '') for l in self.env['res.lang'].sudo().search(
            [('active', '=', True)]) if l.url_code}
        seg = path.split('/')
        if len(seg) > 1 and seg[1] in codes:
            path = '/' + '/'.join(seg[2:])
        return path if path.startswith('/') else '/' + path

    def _uellow_country_hreflangs(self):
        """Full reciprocal hreflang list for the current page across all
        storefront country sites. Returns [] on non-store sites."""
        if not (request and request.httprequest) or not self._uellow_is_store_site():
            return []
        neutral = self._uellow_neutral_path()
        out = []
        sites = self.env['website'].sudo().search([('domain', '!=', False)])
        for w in sites.sorted('id'):
            m = _SUB_RE.match((w.domain or '').strip())
            if not m:
                continue
            sub = m.group(1).lower()
            dom = (w.domain or '').rstrip('/')
            if sub == 'www':
                out.append({'hreflang': 'en', 'href': dom + neutral})
                out.append({'hreflang': 'ar', 'href': dom + '/ar' + neutral})
            elif sub in _COUNTRY_SUBS:
                cc = sub.upper()
                out.append({'hreflang': 'en-' + cc, 'href': dom + neutral})
                out.append({'hreflang': 'ar-' + cc, 'href': dom + '/ar' + neutral})
        # x-default -> the international (www) English page
        www = sites.filtered(lambda s: (s.domain or '').lower().startswith('https://www.'))[:1]
        if www:
            out.append({'hreflang': 'x-default',
                        'href': (www.domain or '').rstrip('/') + neutral})
        return out
