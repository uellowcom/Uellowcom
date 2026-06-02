import json
import logging
from datetime import timedelta
from urllib import request as urlreq, error as urlerr

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PerfMetric(models.Model):
    """Real-User Monitoring sample — one row per beacon from a browser."""
    _name = 'uellow.perf.metric'
    _description = 'Uellow Performance — RUM sample'
    _order = 'create_date desc'

    page = fields.Char(index=True, required=True)
    country = fields.Char(index=True)
    device = fields.Selection([
        ('desktop', 'Desktop'),
        ('mobile', 'Mobile'),
        ('tablet', 'Tablet'),
        ('other', 'Other'),
    ], index=True)
    connection = fields.Char()

    lcp_ms = fields.Float(string='LCP (ms)', index=True)
    cls = fields.Float(string='CLS', digits=(8, 4))
    inp_ms = fields.Float(string='INP (ms)')
    fcp_ms = fields.Float(string='FCP (ms)')
    ttfb_ms = fields.Float(string='TTFB (ms)')
    dom_ms = fields.Float(string='DOMContentLoaded (ms)')
    load_ms = fields.Float(string='load (ms)')

    # Attribution
    lcp_element = fields.Char(string='LCP element',
        help='CSS selector of the largest element that defined LCP.')
    inp_target = fields.Char(string='INP target',
        help='CSS selector of the slowest interaction target.')

    grade = fields.Selection([
        ('good', 'Good'),
        ('ni', 'Needs improvement'),
        ('poor', 'Poor'),
    ], compute='_compute_grade', store=True, index=True)

    @api.depends('lcp_ms', 'cls', 'inp_ms')
    def _compute_grade(self):
        for r in self:
            poor = ((r.lcp_ms or 0) > 4000 or (r.cls or 0) > 0.25 or
                    (r.inp_ms or 0) > 500)
            ni = ((r.lcp_ms or 0) > 2500 or (r.cls or 0) > 0.10 or
                  (r.inp_ms or 0) > 200)
            r.grade = 'poor' if poor else ('ni' if ni else 'good')

    @api.model
    def cron_prune_old(self):
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        days = max(1, int(cfg.rum_retention_days or 30))
        cutoff = fields.Datetime.now() - timedelta(days=days)
        self.env.cr.execute(
            "DELETE FROM uellow_perf_metric WHERE create_date < %s", [cutoff])


class PerfCruxSample(models.Model):
    """Chrome UX Report — daily field data from Google."""
    _name = 'uellow.perf.crux.sample'
    _description = 'Uellow Performance — CrUX sample'
    _order = 'create_date desc'

    url = fields.Char(required=True, index=True)
    form_factor = fields.Selection([
        ('PHONE', 'Mobile'),
        ('DESKTOP', 'Desktop'),
        ('TABLET', 'Tablet'),
    ])
    lcp_p75 = fields.Float(string='LCP p75 (ms)')
    cls_p75 = fields.Float(string='CLS p75')
    inp_p75 = fields.Float(string='INP p75 (ms)')
    fcp_p75 = fields.Float(string='FCP p75 (ms)')
    ttfb_p75 = fields.Float(string='TTFB p75 (ms)')

    @api.model
    def cron_fetch(self):
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        if not (cfg.crux_enabled and cfg.crux_api_key):
            return 0
        urls = [u.strip() for u in (cfg.synthetic_urls or '').splitlines()
                if u.strip()]
        base = 'https://www.uellow.com'
        n = 0
        for path in urls:
            full = path if path.startswith('http') else base + path
            for ff in ('PHONE', 'DESKTOP'):
                try:
                    payload = json.dumps({
                        'url': full, 'formFactor': ff,
                        'metrics': ['largest_contentful_paint',
                                    'cumulative_layout_shift',
                                    'interaction_to_next_paint',
                                    'first_contentful_paint',
                                    'experimental_time_to_first_byte'],
                    }).encode()
                    api_url = ('https://chromeuxreport.googleapis.com/v1/'
                               'records:queryRecord?key=' + cfg.crux_api_key)
                    req = urlreq.Request(api_url, data=payload,
                        headers={'Content-Type': 'application/json'},
                        method='POST')
                    with urlreq.urlopen(req, timeout=10) as resp:
                        d = json.loads(resp.read())
                    metrics = (d.get('record') or {}).get('metrics') or {}
                    self.create({
                        'url': full, 'form_factor': ff,
                        'lcp_p75': (metrics.get('largest_contentful_paint') or
                                    {}).get('percentiles', {}).get('p75'),
                        'cls_p75': float((metrics.get('cumulative_layout_shift')
                                          or {}).get('percentiles', {}).get('p75')
                                         or 0),
                        'inp_p75': (metrics.get('interaction_to_next_paint') or
                                    {}).get('percentiles', {}).get('p75'),
                        'fcp_p75': (metrics.get('first_contentful_paint') or
                                    {}).get('percentiles', {}).get('p75'),
                        'ttfb_p75': (
                            metrics.get('experimental_time_to_first_byte') or
                            {}).get('percentiles', {}).get('p75'),
                    })
                    n += 1
                except (urlerr.URLError, urlerr.HTTPError, OSError) as e:
                    _logger.info('[crux] %s %s: %s', full, ff, e)
                except Exception as e:
                    _logger.warning('[crux] %s parse: %s', full, e)
        return n
