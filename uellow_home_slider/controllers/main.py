# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class UellowHomeSliderController(http.Controller):

    @http.route('/uellow/slider/data', type='http', auth='public', website=True)
    def slider_data(self, **kwargs):
        slider = request.env['uellow.home.slider'].sudo().get_active()
        if not slider:
            return request.make_json_response({})

        lang_code = (request.env.lang or 'ar_001').lower()
        lang = 'en' if lang_code.startswith('en') else 'ar'

        def img(rec, field, fallback=''):
            if rec[field]:
                return '/web/image/%s/%d/%s' % (rec._name, rec.id, field)
            return fallback

        logo = img(slider, 'logo_image', slider.logo_url or '')

        if lang == 'ar':
            banners = {
                'b1': {'src': img(slider, 'ar_banner1_image', 'https://www.uellow.com/web/image/134895'), 'href': slider.ar_banner1_url or '/shop', 'alt': slider.ar_banner1_alt or ''},
                'b2': {'src': img(slider, 'ar_banner2_image', 'https://www.uellow.com/web/image/134896'), 'href': slider.ar_banner2_url or '/shop', 'alt': slider.ar_banner2_alt or ''},
            }
        else:
            banners = {
                'b1': {'src': img(slider, 'en_banner1_image', 'https://www.uellow.com/web/image/134895'), 'href': slider.en_banner1_url or '/shop', 'alt': slider.en_banner1_alt or ''},
                'b2': {'src': img(slider, 'en_banner2_image', 'https://www.uellow.com/web/image/134896'), 'href': slider.en_banner2_url or '/shop', 'alt': slider.en_banner2_alt or ''},
            }

        def get_slides(device):
            slides = slider.slide_ids.filtered(
                lambda s: s.language == lang and s.device == device and s.active
            ).sorted('sequence')
            if not slides and device == 'mobile':
                slides = slider.slide_ids.filtered(
                    lambda s: s.language == lang and s.device == 'desktop' and s.active
                ).sorted('sequence')
            return [{
                'src': s.get_src(), 'href': s.link_url or '/shop', 'alt': s.alt_text or '',
                'target': s.get_target(), 'overlay': s.show_overlay,
                'kicker': s.overlay_kicker or '', 'title': s.overlay_title or '',
                'sub': s.overlay_sub or '', 'btn': s.overlay_btn or '',
                'btn_url': s.overlay_btn_url or s.link_url or '/shop',
                # per-slide coupon + features (resolved against the slider defaults)
                'coupon_show': (False if s.sl_coupon_mode == 'hide'
                                else (True if s.sl_coupon_mode == 'custom' else bool(slider.show_coupon))),
                'coupon_code': (s.sl_coupon_code if s.sl_coupon_mode == 'custom' else slider.coupon_code) or '',
                'coupon_disc': (s.sl_coupon_disc if s.sl_coupon_mode == 'custom' else slider.coupon_discount) or '',
                'feats_show': (s.sl_feats_mode != 'hide') and bool(slider.show_features),
            } for s in slides]

        # departments menu (add/remove controlled from the backend)
        menu = []
        if slider.show_menu:
            for m in slider.menu_ids.filtered('active').sorted('sequence'):
                menu.append({
                    'label': (m.name_en if lang == 'en' else m.name_ar) or m.name_ar or m.name_en or '',
                    'icon': m.icon or 'tag',
                    'url': m.url or '/shop',
                })

        # feature badges (delivery / COD / secure ... — add/remove from backend)
        features = []
        if slider.show_features:
            for f in slider.feature_ids.filtered('active').sorted('sequence'):
                features.append({
                    'label': (f.name_en if lang == 'en' else f.name_ar) or f.name_ar or f.name_en or '',
                    'icon': f.icon or 'star',
                })

        # real number of top-level storefront categories (for the menu footer)
        try:
            menu_total = request.env['product.public.category'].sudo().search_count([('parent_id', '=', False)])
        except Exception:
            menu_total = len(menu)

        # real, full storefront category tree (parents + subcategories) for a
        # professional flyout menu, matching the site header.
        categories = []
        if slider.show_menu:
            PC = request.env['product.public.category'].sudo()
            wid = request.website.id if request.website else False
            parents = PC.search([('parent_id', '=', False),
                                 ('website_id', 'in', [False, wid])],
                                order='sequence, name', limit=40)
            website = request.website
            for _i, c in enumerate(parents):
                kids = []
                for ch in c.child_id.sorted(lambda x: (x.sequence, x.name or '')):
                    kids.append({
                        'name': ch.name,
                        'url': '/shop/category/%d' % ch.id,
                        'image': ('/web/image/product.public.category/%d/image_128' % ch.id) if ch.image_128 else '',
                    })
                brands = []
                if _i < 20:
                    try:
                        for b in website._uc_category_brands(c, limit=8):
                            brands.append({
                                'name': b.name,
                                'url': '/shop?attribute_value=%d' % b.id,
                                'image': ('/web/image/product.attribute.value/%d/dr_image' % b.id) if getattr(b, 'dr_image', False) else '',
                            })
                    except Exception:
                        brands = []
                mega_img = ''
                if getattr(c, 'uc_mega_image', False):
                    mega_img = '/web/image/product.public.category/%d/uc_mega_image' % c.id
                elif c.image_128:
                    mega_img = '/web/image/product.public.category/%d/image_512' % c.id
                categories.append({
                    'id': c.id, 'name': c.name,
                    'url': '/shop/category/%d' % c.id,
                    'image': ('/web/image/product.public.category/%d/image_128' % c.id) if c.image_128 else '',
                    'children': kids,
                    'brands': brands,
                    'mega_image': mega_img,
                    'mega_eyebrow': (getattr(c, 'uc_mega_eyebrow', '') or ''),
                    'mega_tagline': (getattr(c, 'uc_mega_tagline', '') or ''),
                })
            menu_total = len(parents)

        return request.make_json_response({
            'lang': lang,
            'logo': logo,
            'show_coupon': slider.show_coupon,
            'coupon_code': slider.coupon_code or 'WELCOME05',
            'coupon_discount': slider.coupon_discount or '5%',
            'signup_url': slider.signup_url or '/web/signup',
            'login_url': slider.login_url or '/web/login',
            'banners': banners,
            'desktop': get_slides('desktop'),
            'mobile': get_slides('mobile'),
            # v2 config
            'show_menu': slider.show_menu,
            'show_features': slider.show_features,
            'show_overlay_text': slider.show_overlay_text,
            'show_arrows': slider.show_arrows,
            'show_dots': slider.show_dots,
            'autoplay': slider.autoplay,
            'autoplay_speed': max(2, slider.autoplay_speed or 5),
            'overlay_opacity': slider.overlay_opacity if slider.overlay_opacity is not None else 100,
            'menu_title': slider.menu_title_en if lang == 'en' else slider.menu_title_ar,
            'menu_footer': slider.menu_footer_en if lang == 'en' else slider.menu_footer_ar,
            'menu_footer_url': slider.menu_footer_url or '/shop',
            'menu_total': menu_total,
            'cta_label': slider.cta_label_en if lang == 'en' else slider.cta_label_ar,
            'menu': menu,
            'categories': categories,
            'features': features,
        })
