# -*- coding: utf-8 -*-
"""
In-app ads — /api/mobile/v2/ads
===============================
GET  /ads?type=popup|splash|infeed[&category_id=]  → active ads
POST /ads/<id>/event {event: view|click}           → stats
"""
from odoo import http
from odoo.http import request

from ._common import (safe_endpoint, get_payload, ok, fail, img_url,
                      bilingual, get_website)


def _serialize_ad(a):
    image = None
    if a.image:
        image = img_url('mobile.app.ad', a.id, 'image', unique=a.write_date)
    elif a.image_url:
        image = a.image_url
    return {
        'id': a.id,
        'type': a.ad_type,
        'title': {'en': a.title_en or '', 'ar': a.title_ar or a.title_en or ''},
        'image': image,
        'video_url': a.video_url or '',
        'link_type': a.link_type,
        'target_product_id': a.target_product_id.id if a.target_product_id else None,
        'target_category_id': a.target_category_id.id if a.target_category_id else None,
        'target_url': a.target_url or '',
        # type-specific knobs
        'popup_frequency': a.popup_frequency,
        'popup_delay': a.popup_delay or 0,
        'splash_seconds': a.splash_seconds or 4,
        'splash_skippable': bool(a.splash_skippable),
        'infeed_mode': a.infeed_mode,
        'infeed_every_n': max(2, a.infeed_every_n or 8),
    }


class MobileAdsAPI(http.Controller):

    @http.route('/api/mobile/v2/ads', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def list_ads(self, **kw):
        ad_type = (kw.get('type') or 'popup').strip()
        if ad_type not in ('popup', 'splash', 'infeed'):
            return fail('BAD_TYPE', 'type must be popup|splash|infeed', 400)
        cat = None
        try:
            cat = int(kw.get('category_id') or 0) or None
        except Exception:
            cat = None
        ads = request.env['mobile.app.ad'].sudo().active_ads(
            ad_type, website_id=get_website().id, category_id=cat)
        return ok([_serialize_ad(a) for a in ads])

    @http.route('/api/mobile/v2/ads/<int:ad_id>/event', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def ad_event(self, ad_id, **kw):
        p = get_payload()
        event = (p.get('event') or '').strip()
        if event not in ('view', 'click'):
            return fail('BAD_EVENT', 'event must be view|click', 400)
        a = request.env['mobile.app.ad'].sudo().browse(ad_id)
        if not a.exists():
            return fail('NOT_FOUND', 'Ad not found', 404)
        a.register_event(event)
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'done': True})
