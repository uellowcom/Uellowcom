# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


def _json_response(data, status=200):
    return request.make_response(
        json.dumps(data, default=str),
        headers=[
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-App-Token'),
        ],
        status=status,
    )


def _error(message, status=400):
    return _json_response({'success': False, 'error': message}, status)


class MobileApiController(http.Controller):

    # ─────────────────────────────────────────────────────────────────
    #  HOME PAGE DATA  –  single endpoint that returns everything
    # ─────────────────────────────────────────────────────────────────
    @http.route('/api/mobile/home', type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    def home_data(self, website_id=None, **kw):
        """Returns all home page content in one call."""
        try:
            env = request.env
            base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
            now = datetime.now()

            domain_ws = []
            if website_id:
                domain_ws = [('website_id', '=', int(website_id))]

            # ── Sliders ──────────────────────────────────────────────
            slider_domain = [('active', '=', True)] + domain_ws
            sliders_rec = env['mobile.slider'].sudo().search(slider_domain, order='sequence asc')
            sliders = []
            for s in sliders_rec:
                # Check schedule
                if s.start_date and s.start_date > now:
                    continue
                if s.end_date and s.end_date < now:
                    continue
                action_value = None
                if s.action_type == 'product' and s.product_id:
                    action_value = s.product_id.id
                elif s.action_type == 'category' and s.category_id:
                    action_value = s.category_id.id
                elif s.action_type == 'url':
                    action_value = s.url
                elif s.action_type == 'search':
                    action_value = s.search_keyword
                sliders.append({
                    'id': s.id,
                    'title': s.name,
                    'image_url': f"{base_url}/web/image/mobile.slider/{s.id}/image",
                    'action_type': s.action_type,
                    'action_value': action_value,
                })

            # ── Category Icons ────────────────────────────────────────
            icons_rec = env['mobile.category.icon'].sudo().search(
                [('active', '=', True)] + domain_ws, order='sequence asc'
            )
            icons = []
            for ic in icons_rec:
                av = None
                if ic.action_type == 'category' and ic.category_id:
                    av = ic.category_id.id
                elif ic.action_type == 'url':
                    av = ic.url
                elif ic.action_type == 'search':
                    av = ic.search_keyword
                icons.append({
                    'id': ic.id,
                    'label_en': ic.name,
                    'label_ar': ic.name_ar or ic.name,
                    'icon_url': f"{base_url}/web/image/mobile.category.icon/{ic.id}/icon_image",
                    'action_type': ic.action_type,
                    'action_value': av,
                })

            # ── Feature Banners ───────────────────────────────────────
            banners_rec = env['mobile.feature.banner'].sudo().search(
                [('active', '=', True)] + domain_ws, order='sequence asc'
            )
            banners = []
            for b in banners_rec:
                banners.append({
                    'id': b.id,
                    'title_en': b.name,
                    'title_ar': b.name_ar or b.name,
                    'subtitle_en': b.description or '',
                    'subtitle_ar': b.description_ar or b.description or '',
                    'icon_type': b.icon_type,
                    'icon_emoji': b.icon_emoji or '',
                    'icon_url': f"{base_url}/web/image/mobile.feature.banner/{b.id}/icon_image" if b.icon_type == 'image' else None,
                })

            # ── Product Sections ──────────────────────────────────────
            sections_rec = env['mobile.product.slider'].sudo().search(
                [('active', '=', True)] + domain_ws, order='sequence asc'
            )
            sections = []
            for sec in sections_rec:
                more_value = None
                if sec.more_action_type == 'category' and sec.more_category_id:
                    more_value = sec.more_category_id.id
                elif sec.more_action_type == 'url':
                    more_value = sec.more_url
                elif sec.more_action_type == 'search':
                    more_value = sec.more_search

                sections.append({
                    'id': sec.id,
                    'title_en': sec.name,
                    'title_ar': sec.name_ar or sec.name,
                    'section_type': sec.section_type,
                    'display_style': sec.display_style,
                    'show_discount_badge': sec.show_discount_badge,
                    'show_sold_count': sec.show_sold_count,
                    'show_rating': sec.show_rating,
                    'show_view_more': sec.show_view_more,
                    'show_timer': sec.show_timer,
                    'timer_end': str(sec.timer_end) if sec.timer_end else None,
                    'max_products': sec.max_products,
                    'more_action_type': sec.more_action_type,
                    'more_action_value': more_value,
                    # Source identifiers for Flutter to fetch products
                    'category_id': sec.category_id.id if sec.category_id else None,
                    'brand_id': sec.brand_attribute_value_id.id if sec.brand_attribute_value_id else None,
                    'tag_id': sec.product_tag_id.id if sec.product_tag_id else None,
                    'product_ids': sec.product_ids.ids if sec.section_type == 'manual' else [],
                })

            # ── Popups ────────────────────────────────────────────────
            popups_rec = env['mobile.popup'].sudo().search(
                [('active', '=', True)] + domain_ws, order='sequence asc'
            )
            popups = []
            for p in popups_rec:
                if p.start_date and p.start_date > now.date():
                    continue
                if p.end_date and p.end_date < now.date():
                    continue
                av = None
                if p.action_type == 'product' and p.product_id:
                    av = p.product_id.id
                elif p.action_type == 'category' and p.category_id:
                    av = p.category_id.id
                elif p.action_type == 'url':
                    av = p.action_url
                popups.append({
                    'id': p.id,
                    'name': p.name,
                    'image_url': f"{base_url}/web/image/mobile.popup/{p.id}/image",
                    'trigger': p.trigger,
                    'frequency': p.frequency,
                    'action_type': p.action_type,
                    'action_value': av,
                })

            return _json_response({
                'success': True,
                'data': {
                    'sliders': sliders,
                    'category_icons': icons,
                    'feature_banners': banners,
                    'sections': sections,
                    'popups': popups,
                }
            })
        except Exception as e:
            _logger.error("Mobile API /home error: %s", e)
            return _error(str(e), 500)

    # ─────────────────────────────────────────────────────────────────
    #  APP SETTINGS
    # ─────────────────────────────────────────────────────────────────
    @http.route('/api/mobile/settings', type='http', auth='public', methods=['GET'], csrf=False)
    def app_settings(self, website_id=None, **kw):
        try:
            env = request.env
            domain = []
            if website_id:
                domain = [('website_id', '=', int(website_id))]
            setting = env['mobile.app.setting'].sudo().search(domain, limit=1)
            if not setting:
                return _error('No settings configured', 404)

            base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
            return _json_response({
                'success': True,
                'data': {
                    'app_name': setting.app_name,
                    'app_logo_url': f"{base_url}/web/image/mobile.app.setting/{setting.id}/app_logo" if setting.app_logo else None,
                    'min_version_android': setting.app_version_android,
                    'min_version_ios': setting.app_version_ios,
                    'force_update': setting.force_update,
                    'maintenance_mode': setting.maintenance_mode,
                    'maintenance_message': setting.maintenance_message or '',
                    'social': {
                        'whatsapp': setting.whatsapp_number or '',
                        'facebook': setting.facebook_url or '',
                        'instagram': setting.instagram_url or '',
                        'youtube': setting.youtube_url or '',
                        'tiktok': setting.tiktok_url or '',
                        'twitter': setting.twitter_url or '',
                    },
                    'contact': {
                        'support_email': setting.support_email or '',
                        'support_phone': setting.support_phone or '',
                        'contact_url': setting.contact_url or '',
                        'about_us_url': setting.about_us_url or '',
                        'privacy_policy_url': setting.privacy_policy_url or '',
                        'terms_url': setting.terms_url or '',
                        'blog_url': setting.blog_url or '',
                    },
                    'chat': {
                        'enabled': setting.chat_enabled,
                        'provider': setting.chat_provider,
                        'custom_url': setting.chat_custom_url or '',
                    },
                    'stores': {
                        'google_play': setting.google_play_url or '',
                        'app_store': setting.app_store_url or '',
                    },
                    'theme': {
                        'primary_color': setting.primary_color or '#FFC107',
                        'secondary_color': setting.secondary_color or '#FF9800',
                        'accent_color': setting.accent_color or '#FF5722',
                    },
                }
            })
        except Exception as e:
            _logger.error("Mobile API /settings error: %s", e)
            return _error(str(e), 500)

    # ─────────────────────────────────────────────────────────────────
    #  SESSION REGISTRATION
    # ─────────────────────────────────────────────────────────────────
    @http.route('/api/mobile/session/register', type='json', auth='public', methods=['POST'], csrf=False)
    def register_session(self, **kw):
        try:
            params = request.jsonrequest
            device_id = params.get('device_id')
            platform = params.get('platform', 'android')
            app_version = params.get('app_version', '')
            fcm_token = params.get('fcm_token')
            user_id = params.get('user_id')
            device_name = params.get('device_name')
            os_version = params.get('os_version')
            ip = request.httprequest.environ.get('REMOTE_ADDR')

            if not device_id:
                return {'success': False, 'error': 'device_id is required'}

            session_id = request.env['mobile.session'].sudo().register_session(
                device_id=device_id,
                platform=platform,
                app_version=app_version,
                fcm_token=fcm_token,
                user_id=user_id,
                device_name=device_name,
                os_version=os_version,
                ip=ip,
            )
            return {'success': True, 'session_id': session_id}
        except Exception as e:
            _logger.error("Mobile API /session/register error: %s", e)
            return {'success': False, 'error': str(e)}

    # ─────────────────────────────────────────────────────────────────
    #  ACTIVE SESSION COUNT  (for dashboard)
    # ─────────────────────────────────────────────────────────────────
    @http.route('/api/mobile/session/count', type='http', auth='public', methods=['GET'], csrf=False)
    def session_count(self, **kw):
        try:
            count = request.env['mobile.session'].sudo().get_active_count()
            return _json_response({'success': True, 'active_sessions': count})
        except Exception as e:
            return _error(str(e), 500)
