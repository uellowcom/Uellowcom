# -*- coding: utf-8 -*-
"""Inject Organization, WebSite, BreadcrumbList JSON-LD globally + Product
JSON-LD on product detail pages. Plus fix the homepage title.

Also wires a helper used by the Qweb template to detect the current
product/page and emit the right schema.
"""
import json

from odoo import models, fields, _
from odoo.http import request


class WebsiteSEOManager(models.Model):
    _inherit = 'website'

    def seo_get_organization_jsonld(self):
        """Build Organization JSON-LD for site-wide injection."""
        self.ensure_one()
        Param = self.env['ir.config_parameter'].sudo()
        base = (Param.get_param('web.base.url') or '').rstrip('/')
        # Pull SEO config if present
        cfg = self.env.get('uellow.seo.config')
        social = []
        if cfg is not None:
            c = cfg.sudo().get_config() if hasattr(cfg, 'get_config') else cfg.sudo().search([], limit=1)
            if c:
                for fld in ('twitter_url', 'instagram_url', 'facebook_url',
                            'youtube_url', 'tiktok_url'):
                    val = getattr(c, fld, None)
                    if val: social.append(val)
        data = {
            '@context': 'https://schema.org/',
            '@type': 'Organization',
            'name': self.name or 'Uellow',
            'url': base or 'https://uellow.com',
            'logo': f'{base}/web/image/website/{self.id}/logo' if self.id else '',
        }
        if social:
            data['sameAs'] = social
        return data

    def seo_get_website_jsonld(self):
        """WebSite + SearchAction JSON-LD — enables Google sitelinks
        search box on SERPs."""
        self.ensure_one()
        Param = self.env['ir.config_parameter'].sudo()
        base = (Param.get_param('web.base.url') or '').rstrip('/')
        return {
            '@context': 'https://schema.org/',
            '@type': 'WebSite',
            'name': self.name or 'Uellow',
            'url': base,
            'potentialAction': {
                '@type': 'SearchAction',
                'target': {
                    '@type': 'EntryPoint',
                    'urlTemplate': f'{base}/shop?search=' + '{search_term_string}',
                },
                'query-input': 'required name=search_term_string',
            },
        }

    def seo_dump_json(self, data):
        """Helper used inside Qweb templates to JSON-encode safely."""
        try:
            return json.dumps(data, ensure_ascii=False, default=str)
        except Exception:
            return '{}'

    def seo_current_product(self):
        """Return the product.template of the current product detail page,
        or False. Called from the head template to decide whether to
        emit Product schema."""
        if not request:
            return False
        obj = request.params.get('product') or request.env.context.get('main_object')
        # Detect product page via the route
        path = (request.httprequest.path or '')
        if '/shop/' not in path:
            return False
        # Try main_object
        mo = getattr(request, 'main_object', False)
        if mo and mo._name == 'product.template':
            return mo
        return False
