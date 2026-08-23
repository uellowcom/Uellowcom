# -*- coding: utf-8 -*-
"""Keeps the mobile-home API cache warm across all HTTP workers (each worker
has its OWN in-process page cache, so a low-traffic period leaves some cold →
a visitor's block fetch would pay the ~1.5–9s cold rebuild). A tiny cron pings
the endpoint a few times per language to keep every worker warm."""
import urllib.request

from odoo import models, api


class MobilePageWarm(models.Model):
    _inherit = 'mobile.page'

    @api.model
    def _uc_warm_home(self):
        # Force ONE fresh resolve per language (?_refresh=1, loopback-only)
        # so the cross-worker shared on-disk cache never expires under real
        # traffic — every worker then serves it in ~ms with zero cold builds.
        for lang in ('ar', 'en'):
            try:
                req = urllib.request.Request(
                    'http://localhost:8069/api/mobile/v2/pages/home?_refresh=1',
                    headers={'X-Lang': lang})
                urllib.request.urlopen(req, timeout=40).read()
            except Exception:
                pass
