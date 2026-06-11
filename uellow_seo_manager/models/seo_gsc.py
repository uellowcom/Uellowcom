# -*- coding: utf-8 -*-
"""Phase 4 — Google Search Console integration.

Pulls Search Analytics rows (query, page, clicks, impressions, ctr,
position) via the Search Console API and stores them in
`uellow.seo.gsc.row`. The dashboard then shows top queries, top pages,
and a CTR breakdown.

Auth: service account JSON pasted into uellow.seo.config (Phase 4
field `gsc_service_account_json`). Property URL is the site root.

Calls are conservative — daily cron pulls the last 7 days. Free Google
quota is 1,200 req/min, more than enough.
"""
import json
import logging
from datetime import date, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SEOConfigGSC(models.Model):
    _inherit = 'uellow.seo.config'

    gsc_property_url = fields.Char(string='GSC property URL',
        help='e.g. https://uellow.com/ — must match exactly what is in GSC.')
    gsc_service_account_json = fields.Text(string='GSC service-account JSON',
        groups='base.group_system',
        help='Paste the entire JSON key file. The service account email '
             'must be added as a USER on the GSC property.')
    gsc_last_sync_at = fields.Datetime(readonly=True)
    gsc_last_sync_rows = fields.Integer(readonly=True)


class SEOGSCRow(models.Model):
    _name = 'uellow.seo.gsc.row'
    _description = 'Search Console query/page row'
    _order = 'date desc, clicks desc'

    date = fields.Date(required=True, index=True)
    query = fields.Char(index=True)
    page = fields.Char(index=True)
    country = fields.Char(size=3)
    device = fields.Selection([
        ('DESKTOP','Desktop'),('MOBILE','Mobile'),('TABLET','Tablet'),
    ])
    clicks = fields.Integer()
    impressions = fields.Integer()
    ctr = fields.Float(string='CTR %', digits=(6, 3))
    position = fields.Float(digits=(6, 2))

    _sql_constraints = [
        ('uniq_row',
         'unique(date, query, page, country, device)',
         'Duplicate GSC row'),
    ]

    @api.model
    def action_sync_recent(self, days=7):
        """Pull last `days` days of search analytics into local table."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError:
            _logger.warning('google-api-python-client not installed — skipping GSC sync')
            return 0

        cfg = self.env['uellow.seo.config'].sudo().get_config()
        if not cfg.gsc_service_account_json or not cfg.gsc_property_url:
            _logger.info('GSC not configured — skipping sync')
            return 0
        try:
            sa_info = json.loads(cfg.gsc_service_account_json)
        except Exception:
            _logger.warning('Invalid service-account JSON')
            return 0

        creds = service_account.Credentials.from_service_account_info(
            sa_info, scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
        svc = build('searchconsole', 'v1', credentials=creds)

        end = date.today()
        start = end - timedelta(days=days)
        request = {
            'startDate': start.isoformat(),
            'endDate':   end.isoformat(),
            'dimensions': ['date', 'query', 'page', 'country', 'device'],
            'rowLimit': 25000,
        }
        try:
            resp = svc.searchanalytics().query(
                siteUrl=cfg.gsc_property_url, body=request).execute()
        except Exception as e:
            _logger.warning('GSC API call failed: %s', e)
            return 0

        rows = resp.get('rows', [])
        # Clear stale window so we don't accumulate duplicates
        self.search([('date', '>=', start)]).unlink()
        out = []
        for r in rows:
            keys = r.get('keys') or []
            if len(keys) < 5: continue
            out.append({
                'date': keys[0], 'query': keys[1], 'page': keys[2],
                'country': keys[3], 'device': keys[4],
                'clicks': r.get('clicks', 0),
                'impressions': r.get('impressions', 0),
                'ctr': (r.get('ctr', 0) or 0) * 100,
                'position': r.get('position', 0),
            })
        if out:
            self.create(out)
        cfg.write({
            'gsc_last_sync_at': fields.Datetime.now(),
            'gsc_last_sync_rows': len(out),
        })
        return len(out)


# ─────────────────────────────────────────────────────────────────────────
# Phase 8 — Indexing coverage: read errors via the URL Inspection API and
# auto-fix what Odoo controls, then re-submit the sitemap so Google re-crawls.
# ─────────────────────────────────────────────────────────────────────────
class SEOIndexingIssue(models.Model):
    _name = 'uellow.seo.indexing.issue'
    _description = 'Search Console indexing coverage / issue'
    _order = 'severity desc, last_checked desc'

    url = fields.Char(required=True, index=True)
    verdict = fields.Selection([
        ('PASS', 'Indexed ✓'), ('PARTIAL', 'Partial'),
        ('FAIL', 'Not indexed'), ('NEUTRAL', 'Neutral'),
    ], index=True)
    coverage_state = fields.Char(string='Coverage')
    robots_state = fields.Char(string='robots.txt')
    indexing_state = fields.Char(string='Indexing')
    fetch_state = fields.Char(string='Page fetch')
    google_canonical = fields.Char()
    user_canonical = fields.Char()
    last_crawl = fields.Char(string='Last crawl')
    severity = fields.Selection([
        ('0', 'OK'), ('1', 'Info'), ('2', 'Warning'), ('3', 'Error'),
    ], default='1', index=True)
    issue_text = fields.Char(string='Issue')
    suggested_fix = fields.Char()
    auto_fixed = fields.Boolean(readonly=True)
    fix_note = fields.Char(readonly=True)
    res_model = fields.Char()
    res_id = fields.Integer()
    last_checked = fields.Datetime(readonly=True)

    # ── helpers ─────────────────────────────────────────────────────────
    @api.model
    def _gsc_service(self, cfg):
        """Build the Search Console API client, or None when unavailable."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError:
            _logger.warning('google-api-python-client not installed')
            return None
        if not cfg.gsc_service_account_json or not cfg.gsc_property_url:
            return None
        try:
            sa = json.loads(cfg.gsc_service_account_json)
        except Exception:
            _logger.warning('Invalid GSC service-account JSON')
            return None
        creds = service_account.Credentials.from_service_account_info(
            sa, scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
        return build('searchconsole', 'v1', credentials=creds)

    def _candidate_urls(self, cfg, limit=180):
        """Top URLs worth inspecting: most-impressed pages from GSC analytics
        first (where indexing problems actually cost traffic), then published
        products, then key static pages."""
        base = (cfg.gsc_property_url or '').rstrip('/')
        urls, seen = [], set()

        def add(u):
            if u and u not in seen:
                seen.add(u)
                urls.append(u)

        # 1) pages Google already shows impressions for
        Row = self.env['uellow.seo.gsc.row'].sudo()
        for r in Row.search([('page', '!=', False)], order='impressions desc',
                            limit=limit):
            add(r.page)
        # 2) published products
        if len(urls) < limit:
            Tmpl = self.env['product.template'].sudo()
            for p in Tmpl.search([('is_published', '=', True),
                                  ('website_published', '=', True)],
                                 order='write_date desc', limit=limit):
                try:
                    add(base + p.website_url)
                except Exception:
                    continue
        # 3) home + shop
        add(base + '/'); add(base + '/shop')
        return urls[:limit]

    @api.model
    def action_inspect_urls(self, limit=120):
        """Inspect candidate URLs via the URL Inspection API and record any
        coverage problems. Safe to run with no creds (no-op). Returns count
        of issues recorded."""
        cfg = self.env['uellow.seo.config'].sudo().get_config()
        svc = self._gsc_service(cfg)
        if svc is None:
            _logger.info('GSC indexing inspect skipped — not configured')
            return 0
        site = cfg.gsc_property_url
        now = fields.Datetime.now()
        recorded = 0
        for url in self._candidate_urls(cfg, limit=limit):
            try:
                resp = svc.urlInspection().index().inspect(body={
                    'inspectionUrl': url, 'siteUrl': site,
                }).execute()
            except Exception as e:
                _logger.debug('inspect failed for %s: %s', url, e)
                continue
            idx = (resp.get('inspectionResult') or {}).get(
                'indexStatusResult') or {}
            verdict = idx.get('verdict', 'NEUTRAL')
            coverage = idx.get('coverageState', '')
            sev, issue, fix = self._classify(idx)
            vals = {
                'url': url, 'verdict': verdict, 'coverage_state': coverage,
                'robots_state': idx.get('robotsTxtState', ''),
                'indexing_state': idx.get('indexingState', ''),
                'fetch_state': idx.get('pageFetchState', ''),
                'google_canonical': idx.get('googleCanonical', ''),
                'user_canonical': idx.get('userCanonical', ''),
                'last_crawl': idx.get('lastCrawlTime', ''),
                'severity': sev, 'issue_text': issue, 'suggested_fix': fix,
                'last_checked': now, 'auto_fixed': False, 'fix_note': False,
            }
            self._link_odoo_record(vals, cfg)
            existing = self.search([('url', '=', url)], limit=1)
            if existing:
                existing.write(vals)
            else:
                self.create(vals)
            if sev in ('2', '3'):
                recorded += 1
        return recorded

    @staticmethod
    def _classify(idx):
        """Map a URL Inspection result → (severity, issue, suggested fix)."""
        verdict = idx.get('verdict', 'NEUTRAL')
        coverage = (idx.get('coverageState') or '')
        indexing = (idx.get('indexingState') or '')
        robots = (idx.get('robotsTxtState') or '')
        fetch = (idx.get('pageFetchState') or '')
        gcanon = idx.get('googleCanonical', '')
        ucanon = idx.get('userCanonical', '')
        if verdict == 'PASS' and 'Indexed' in coverage:
            return '0', 'Indexed', ''
        if indexing == 'BLOCKED_BY_META_TAG':
            return '3', 'Blocked by noindex meta tag', \
                'Remove the noindex tag / publish the page.'
        if robots == 'DISALLOWED':
            return '3', 'Blocked by robots.txt', \
                'Allow this path in robots.txt.'
        if fetch and fetch not in ('SUCCESSFUL',):
            return '3', 'Page fetch failed (%s)' % fetch, \
                'Fix the server/page error then request indexing.'
        if gcanon and ucanon and gcanon != ucanon:
            return '2', 'Canonical mismatch (Google picked a different URL)', \
                'Set the canonical to the preferred URL.'
        if 'not indexed' in coverage.lower() or verdict == 'FAIL':
            return '2', coverage or 'Not indexed', \
                'Ensure it is in the sitemap + request indexing.'
        if verdict == 'PARTIAL':
            return '1', coverage or 'Partial', 'Review enhancements.'
        return '1', coverage or verdict, ''

    def _link_odoo_record(self, vals, cfg):
        """Best-effort: link the URL back to its product so auto-fix can act."""
        try:
            base = (cfg.gsc_property_url or '').rstrip('/')
            path = (vals['url'] or '').replace(base, '') or vals['url']
            Tmpl = self.env['product.template'].sudo()
            prod = Tmpl.search([('website_url', '=', path)], limit=1)
            if prod:
                vals['res_model'] = 'product.template'
                vals['res_id'] = prod.id
        except Exception:
            pass

    def action_autofix(self):
        """Apply the fixes Odoo actually controls (publish-state for products
        that GSC reports as noindex/blocked but should be live), then re-submit
        the sitemap so Google re-crawls. Google still owns final indexing."""
        fixed = 0
        for issue in self:
            note = ''
            try:
                if issue.res_model == 'product.template' and issue.res_id:
                    prod = self.env['product.template'].sudo().browse(
                        issue.res_id).exists()
                    if prod and issue.indexing_state == 'BLOCKED_BY_META_TAG':
                        # ensure it is actually published (a common cause)
                        if not prod.website_published:
                            prod.website_published = True
                            note = 'Re-published the product.'
                if note:
                    issue.write({'auto_fixed': True, 'fix_note': note})
                    fixed += 1
            except Exception as e:
                _logger.debug('autofix failed for %s: %s', issue.url, e)
        # always re-submit the sitemap so Google re-crawls the fixed URLs
        self.env['uellow.seo.indexing.issue'].sudo().action_resubmit_sitemap()
        return fixed

    @api.model
    def action_resubmit_sitemap(self):
        """Ping Google to re-fetch our sitemap (a genuine 'please re-crawl')."""
        cfg = self.env['uellow.seo.config'].sudo().get_config()
        svc = self._gsc_service(cfg)
        if svc is None:
            return False
        base = (cfg.gsc_property_url or '').rstrip('/')
        sitemap = base + '/sitemap.xml'
        try:
            svc.sitemaps().submit(siteUrl=cfg.gsc_property_url,
                                  feedpath=sitemap).execute()
            _logger.info('Re-submitted sitemap %s', sitemap)
            return True
        except Exception as e:
            _logger.warning('Sitemap submit failed: %s', e)
            return False

    @api.model
    def cron_inspect_and_fix(self):
        """Daily: read indexing coverage, then auto-fix + re-submit sitemap."""
        self.action_inspect_urls(limit=120)
        problems = self.search([('severity', 'in', ('2', '3')),
                                ('auto_fixed', '=', False)])
        if problems:
            problems.action_autofix()
        return True
