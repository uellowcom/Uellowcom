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
