"""
Home endpoint — /api/mobile/v2/home

Single call returns EVERYTHING the home screen needs, sourced ONLY
from mobile.* models — never from website templates or hero sliders.
This is the key independence guarantee: changing /shop or the website
hero on Odoo never affects the app home screen.
"""
from datetime import datetime

from odoo import http
from odoo.http import request

from ._common import safe_endpoint, ok, base_url, img_url, bilingual, get_lang, get_website


class MobileHomeAPI(http.Controller):

    @http.route('/api/mobile/v2/home', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def home(self, **kw):
        env = request.env
        now = datetime.now()

        # ─── Sliders ─────────────────────────────────────────────────
        sliders = []
        for s in env['mobile.slider'].sudo().search(
                [('active', '=', True)], order='sequence asc'):
            if s.start_date and s.start_date > now: continue
            if s.end_date and s.end_date < now: continue
            sliders.append(_slider_dict(s))

        # ─── Category icons ──────────────────────────────────────────
        icons = []
        for ic in env['mobile.category.icon'].sudo().search(
                [('active', '=', True)], order='sequence asc'):
            icons.append(_icon_dict(ic))

        # ─── Feature banners ─────────────────────────────────────────
        banners = []
        for b in env['mobile.feature.banner'].sudo().search(
                [('active', '=', True)], order='sequence asc'):
            banners.append(_feature_banner_dict(b))

        # ─── Product sections (rails of products) ────────────────────
        sections = []
        for sec in env['mobile.product.slider'].sudo().search(
                [('active', '=', True)], order='sequence asc'):
            sections.append(_section_dict(sec))

        # ─── Popups (eligible by date) ───────────────────────────────
        popups = []
        for p in env['mobile.popup'].sudo().search(
                [('active', '=', True)], order='sequence asc'):
            if p.start_date and p.start_date > now.date(): continue
            if p.end_date and p.end_date < now.date(): continue
            popups.append(_popup_dict(p))

        # ─── Flash sales (live only) ─────────────────────────────────
        from .flash_sale import _serialize_sale
        from ._common import get_lang
        lang = get_lang()
        website = get_website()
        flash_sales_recs = env['mobile.flash.sale'].sudo().search([
            ('active', '=', True),
            '|', ('website_id', '=', False), ('website_id', '=', website.id),
        ], order='sequence asc')
        flash_sales = [_serialize_sale(s, lang)
                       for s in flash_sales_recs if s.is_live]

        return ok({
            'sliders': sliders,
            'category_icons': icons,
            'feature_banners': banners,
            'flash_sales': flash_sales,
            'sections': sections,
            'popups': popups,
        })


# ─── Serializers (kept here so home stays self-contained) ─────────────

def _action_value(rec):
    if not rec or not getattr(rec, 'action_type', None):
        return None
    t = rec.action_type
    if t == 'product':
        return getattr(rec, 'product_id', False) and rec.product_id.id or None
    if t == 'category':
        return getattr(rec, 'category_id', False) and rec.category_id.id or None
    if t == 'url':
        return getattr(rec, 'url', None) or getattr(rec, 'action_url', None)
    if t == 'search':
        return getattr(rec, 'search_keyword', None) or getattr(rec, 'more_search', None)
    return None


def _slider_dict(s):
    return {
        'id': s.id,
        'title': bilingual(s, 'name'),
        'subtitle': bilingual(s, 'subtitle') if 'subtitle' in s._fields else {'en': '', 'ar': ''},
        'image_url': img_url('mobile.slider', s.id, 'image', unique=s.write_date),
        'action_type': s.action_type,
        'action_value': _action_value(s),
        'cta_label': bilingual(s, 'cta_label') if 'cta_label' in s._fields else None,
    }


def _icon_dict(ic):
    return {
        'id': ic.id,
        'label': bilingual(ic, 'name'),
        'icon_url': img_url('mobile.category.icon', ic.id, 'icon_image',
                            unique=ic.write_date),
        'action_type': ic.action_type,
        'action_value': _action_value(ic),
    }


def _feature_banner_dict(b):
    return {
        'id': b.id,
        'title': bilingual(b, 'name'),
        'subtitle': bilingual(b, 'description'),
        'icon_type': b.icon_type,
        'icon_emoji': b.icon_emoji or '',
        'icon_url': (img_url('mobile.feature.banner', b.id, 'icon_image',
                             unique=b.write_date)
                     if b.icon_type == 'image' else None),
        'background_color': getattr(b, 'background_color', None),
        'text_color': getattr(b, 'text_color', None),
    }


def _section_dict(sec):
    more = sec.more_action_type
    more_value = None
    if more == 'category' and sec.more_category_id:
        more_value = sec.more_category_id.id
    elif more == 'url':
        more_value = sec.more_url
    elif more == 'search':
        more_value = sec.more_search
    return {
        'id': sec.id,
        'title': bilingual(sec, 'name'),
        'section_type': sec.section_type,
        'display_style': sec.display_style,
        'show_discount_badge': sec.show_discount_badge,
        'show_sold_count':     sec.show_sold_count,
        'show_rating':         sec.show_rating,
        'show_view_more':      sec.show_view_more,
        'show_timer':          sec.show_timer,
        'timer_end':           sec.timer_end and sec.timer_end.isoformat() or None,
        'max_products':        sec.max_products,
        'more_action_type':    more,
        'more_action_value':   more_value,
        # Source identifiers — Flutter pulls products via
        # /api/mobile/v2/products/section/<id>
        'products_endpoint': f'/api/mobile/v2/products/section/{sec.id}',
    }


def _popup_dict(p):
    av = None
    if p.action_type == 'product' and p.product_id:
        av = p.product_id.id
    elif p.action_type == 'category' and p.category_id:
        av = p.category_id.id
    elif p.action_type == 'url':
        av = p.action_url
    return {
        'id': p.id,
        'name': bilingual(p, 'name'),
        'image_url': img_url('mobile.popup', p.id, 'image', unique=p.write_date),
        'trigger': p.trigger,
        'frequency': p.frequency,
        'action_type': p.action_type,
        'action_value': av,
    }
