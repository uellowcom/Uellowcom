# -*- coding: utf-8 -*-
"""Phase 3 — SERP Preview.

Adds computed `seo_serp_*` fields on product.template that render the
title + description exactly the way Google would crop them. Used by a
small Qweb view embedded in the product form (Edit Online → Promote tab).
"""
from odoo import api, fields, models


GOOGLE_DESKTOP_TITLE_CHARS = 60
GOOGLE_DESKTOP_DESC_CHARS = 160
GOOGLE_MOBILE_TITLE_CHARS = 50
GOOGLE_MOBILE_DESC_CHARS = 130


def _ellipsize(s, n):
    if not s: return ''
    s = s.strip()
    return s if len(s) <= n else (s[:n-1].rstrip() + '…')


class ProductTemplateSERP(models.Model):
    _inherit = 'product.template'

    seo_serp_title = fields.Char(compute='_compute_serp_preview',
        help='What Google will show as the SERP title (desktop, ~60 chars).')
    seo_serp_desc = fields.Char(compute='_compute_serp_preview',
        help='What Google will show as the SERP description (~160 chars).')
    seo_serp_url = fields.Char(compute='_compute_serp_preview')
    seo_serp_title_length = fields.Integer(compute='_compute_serp_preview')
    seo_serp_desc_length = fields.Integer(compute='_compute_serp_preview')
    seo_serp_title_quality = fields.Selection([
        ('empty', '⚪ empty'),
        ('short', '🟡 too short'),
        ('good',  '🟢 ideal'),
        ('long',  '🟡 too long'),
    ], compute='_compute_serp_preview')
    seo_serp_desc_quality = fields.Selection([
        ('empty', '⚪ empty'),
        ('short', '🟡 too short'),
        ('good',  '🟢 ideal'),
        ('long',  '🟡 too long'),
    ], compute='_compute_serp_preview')

    def _compute_serp_preview(self):
        Param = self.env['ir.config_parameter'].sudo()
        base = (Param.get_param('web.base.url') or '').rstrip('/')
        for r in self:
            title = (r.website_meta_title or r.name or '').strip()
            desc  = (r.website_meta_description or '').strip()
            r.seo_serp_title = _ellipsize(title, GOOGLE_DESKTOP_TITLE_CHARS)
            r.seo_serp_desc  = _ellipsize(desc, GOOGLE_DESKTOP_DESC_CHARS)
            r.seo_serp_url = base + (r.website_url or f'/shop/{r.id}')
            r.seo_serp_title_length = len(title)
            r.seo_serp_desc_length = len(desc)

            # Quality lights
            if not title:
                r.seo_serp_title_quality = 'empty'
            elif len(title) < 30:
                r.seo_serp_title_quality = 'short'
            elif len(title) > 65:
                r.seo_serp_title_quality = 'long'
            else:
                r.seo_serp_title_quality = 'good'

            if not desc:
                r.seo_serp_desc_quality = 'empty'
            elif len(desc) < 70:
                r.seo_serp_desc_quality = 'short'
            elif len(desc) > 165:
                r.seo_serp_desc_quality = 'long'
            else:
                r.seo_serp_desc_quality = 'good'
