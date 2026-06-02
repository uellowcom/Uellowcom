"""Cloudflare cache purge — fires when product/blog post is written, so
edits become visible immediately even with the 60s edge cache rule.

Uses a background thread so the user-facing write doesn't block on the
network call to api.cloudflare.com.
"""
import json
import logging
import threading
from urllib import request as urlrequest, error as urlerror

from odoo import api, models

_logger = logging.getLogger(__name__)


def _cf_purge_urls(zone_id, token, urls):
    if not (zone_id and token and urls):
        return False
    payload = json.dumps({'files': list(urls)[:30]}).encode()
    req = urlrequest.Request(
        f'https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache',
        data=payload, method='POST',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        })
    try:
        with urlrequest.urlopen(req, timeout=10) as resp:
            body = resp.read()
            ok = resp.getcode() < 300
            if not ok:
                _logger.warning('[cdn-purge] failed (%s): %s',
                                resp.getcode(), body[:200])
            return ok
    except (urlerror.URLError, urlerror.HTTPError, OSError) as e:
        _logger.warning('[cdn-purge] error: %s', e)
        return False


def _async_purge(urls, zone_id, token):
    def _run():
        try:
            _cf_purge_urls(zone_id, token, urls)
        except Exception:
            _logger.exception('[cdn-purge] thread failed')
    threading.Thread(target=_run, daemon=True).start()


class ProductTemplateCfPurge(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        res = super().write(vals)
        try:
            self._cf_purge_on_change(vals)
        except Exception:
            _logger.exception('[cdn-purge] product write hook failed')
        return res

    def _cf_purge_on_change(self, vals):
        # Only purge on visible-field changes
        watched = {
            'name', 'description_sale', 'website_description', 'list_price',
            'website_meta_title', 'website_meta_description',
            'image_1920', 'website_published', 'is_published',
        }
        if not (set(vals or ()) & watched):
            return
        cfg = self.env['uellow.perf.config'].sudo().get_config()
        if not (cfg.cf_purge_enabled and cfg.cf_zone_id and cfg.cf_api_token):
            return
        base = (self.env['ir.config_parameter'].sudo()
                .get_param('web.base.url') or '').rstrip('/')
        urls = []
        for r in self:
            slug = ''
            try:
                slug = r.website_url or ''
            except Exception:
                pass
            if slug:
                urls.append(f'{base}{slug}')
        if urls:
            _async_purge(urls, cfg.cf_zone_id, cfg.cf_api_token)


class BlogPostCfPurge(models.Model):
    _inherit = 'blog.post'

    def write(self, vals):
        res = super().write(vals)
        try:
            cfg = self.env['uellow.perf.config'].sudo().get_config()
            if not (cfg.cf_purge_enabled and cfg.cf_zone_id and cfg.cf_api_token):
                return res
            base = (self.env['ir.config_parameter'].sudo()
                    .get_param('web.base.url') or '').rstrip('/')
            urls = []
            for r in self:
                try:
                    u = r.website_url
                    if u:
                        urls.append(f'{base}{u}')
                except Exception:
                    pass
            if urls:
                _async_purge(urls, cfg.cf_zone_id, cfg.cf_api_token)
        except Exception:
            _logger.exception('[cdn-purge] blog write hook failed')
        return res
