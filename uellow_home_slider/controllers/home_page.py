# -*- coding: utf-8 -*-
import json
import random
from markupsafe import Markup
from odoo import http
from odoo.http import request


# Buying guides — answer-ready content pages optimised for AI search engines.
# (slug, category_id [0 = whole store], title_ar, title_en, noun_ar, noun_en)
GUIDES = [
    ('mobiles-installments-kuwait', 855, 'الجوالات بالتقسيط في الكويت', 'Phones on installments in Kuwait', 'جوال', 'phone'),
    ('laptops-installments-kuwait', 625, 'اللابتوبات بالتقسيط في الكويت', 'Laptops on installments in Kuwait', 'لابتوب', 'laptop'),
    ('smartwatches-kuwait', 1, 'الساعات الذكية في الكويت', 'Smartwatches in Kuwait', 'ساعة ذكية', 'smartwatch'),
    ('home-appliances-installments-kuwait', 436, 'الأجهزة المنزلية بالتقسيط في الكويت', 'Home appliances on installments in Kuwait', 'جهاز منزلي', 'home appliance'),
    ('perfumes-kuwait', 645, 'العطور الأصلية في الكويت', 'Original perfumes in Kuwait', 'عطر', 'perfume'),
    ('electronics-kuwait', 412, 'الإلكترونيات في الكويت', 'Electronics in Kuwait', 'جهاز إلكتروني', 'electronics item'),
    ('mobile-accessories-kuwait', 418, 'ملحقات الجوال في الكويت', 'Mobile accessories in Kuwait', 'ملحق', 'accessory'),
    ('baby-products-kuwait', 410, 'مستلزمات الأطفال في الكويت', 'Baby products in Kuwait', 'منتج', 'product'),
    ('jewellery-kuwait', 421, 'المجوهرات والإكسسوارات في الكويت', 'Jewellery and accessories in Kuwait', 'قطعة', 'piece'),
    ('best-online-store-kuwait', 0, 'أفضل متجر تسوّق أونلاين في الكويت', 'Best online shopping store in Kuwait', 'منتج', 'product'),
    ('iphone-installments-kuwait', 855, 'آيفون بالتقسيط في الكويت', 'iPhone on installments in Kuwait', 'آيفون', 'iPhone'),
    ('samsung-phones-kuwait', 855, 'جوالات سامسونج في الكويت', 'Samsung phones in Kuwait', 'جوال سامسونج', 'Samsung phone'),
    ('tablets-kuwait', 603, 'الأجهزة اللوحية (تابلت) في الكويت', 'Tablets in Kuwait', 'تابلت', 'tablet'),
    ('cash-on-delivery-shopping-kuwait', 0, 'التسوّق بالدفع عند الاستلام في الكويت', 'Cash-on-delivery shopping in Kuwait', 'منتج', 'product'),
    ('installments-shopping-kuwait', 0, 'التسوّق بالتقسيط في الكويت', 'Installment shopping in Kuwait', 'منتج', 'product'),
    ('free-shipping-kuwait', 0, 'التسوّق بتوصيل مجاني في الكويت', 'Free-shipping shopping in Kuwait', 'منتج', 'product'),
    ('gaming-kuwait', 412, 'أجهزة وملحقات الألعاب في الكويت', 'Gaming gear in Kuwait', 'جهاز ألعاب', 'gaming item'),
    ('security-cameras-kuwait', 406, 'كاميرات المراقبة وأنظمة الأمان في الكويت', 'Security cameras in Kuwait', 'كاميرا مراقبة', 'security camera'),
    ('electronics-installments-kuwait', 412, 'الإلكترونيات بالتقسيط في الكويت', 'Electronics on installments in Kuwait', 'جهاز', 'device'),
    ('watches-installments-kuwait', 1, 'الساعات بالتقسيط في الكويت', 'Watches on installments in Kuwait', 'ساعة', 'watch'),
    ('earbuds-kuwait', 861, 'السماعات اللاسلكية (EarBuds) في الكويت', 'Wireless earbuds in Kuwait', 'سماعة', 'earbuds'),
    ('speakers-kuwait', 770, 'السماعات ومكبرات الصوت في الكويت', 'Speakers in Kuwait', 'سماعة', 'speaker'),
    ('power-bank-kuwait', 728, 'باور بانك (بطاريات متنقلة) في الكويت', 'Power banks in Kuwait', 'باور بانك', 'power bank'),
    ('chargers-kuwait', 500, 'شواحن الجوال في الكويت', 'Phone chargers in Kuwait', 'شاحن', 'charger'),
    ('cables-kuwait', 481, 'كابلات الشحن والبيانات في الكويت', 'Charging & data cables in Kuwait', 'كابل', 'cable'),
    ('phone-holders-kuwait', 598, 'حاملات الجوال والاستاند في الكويت', 'Phone holders and stands in Kuwait', 'حامل', 'holder'),
    ('wireless-chargers-kuwait', 819, 'الشواحن اللاسلكية في الكويت', 'Wireless chargers in Kuwait', 'شاحن لاسلكي', 'wireless charger'),
    ('car-chargers-kuwait', 488, 'شواحن السيارة في الكويت', 'Car chargers in Kuwait', 'شاحن سيارة', 'car charger'),
    ('headphones-kuwait', 587, 'سماعات الرأس في الكويت', 'Headphones in Kuwait', 'سماعة رأس', 'headphone'),
    ('televisions-kuwait', 738, 'الشاشات والتلفزيونات في الكويت', 'Televisions in Kuwait', 'تلفزيون', 'TV'),
    ('kitchen-appliances-kuwait', 619, 'أجهزة المطبخ في الكويت', 'Kitchen appliances in Kuwait', 'جهاز مطبخ', 'kitchen appliance'),
    ('cameras-kuwait', 416, 'الكاميرات في الكويت', 'Cameras in Kuwait', 'كاميرا', 'camera'),
    ('health-care-kuwait', 451, 'منتجات العناية والصحة في الكويت', 'Health & personal care in Kuwait', 'منتج', 'product'),
    ('car-accessories-kuwait', 425, 'إكسسوارات وقطع السيارات في الكويت', 'Car accessories in Kuwait', 'قطعة', 'accessory'),
    ('phone-cases-kuwait', 495, 'جرابات وكفرات الجوال في الكويت', 'Phone cases and covers in Kuwait', 'كفر', 'case'),
    ('men-perfumes-kuwait', 646, 'العطور الرجالية في الكويت', 'Men fragrances in Kuwait', 'عطر رجالي', "men's perfume"),
    ('sports-outdoor-kuwait', 485, 'مستلزمات الرياضة والأنشطة الخارجية في الكويت', 'Sports & outdoor gear in Kuwait', 'منتج رياضي', 'sports item'),
]


def sitemap_guides(env, rule, qs):
    """Expose every buying guide in the sitemap (dynamic route)."""
    for g in GUIDES:
        loc = '/guide/%s' % g[0]
        if not qs or qs.lower() in loc.lower():
            yield {'loc': loc}


class UellowHomePageController(http.Controller):

    @http.route(['/home-preview'], type='http', auth='public', website=True, sitemap=False)
    def home_preview(self, **kw):
        Page = request.env['uellow.home.page'].sudo()
        page = Page.get_live()
        lang = 'en' if (request.env.lang or '').lower().startswith('en') else 'ar'
        seed = random.randint(1, 999999)
        sections = []
        if page:
            for sec in page.section_ids.filtered('active').sorted(lambda s: (s.sequence, s.id)):
                d = {
                    'sec': sec, 'type': sec.section_type,
                    'show_title': sec.show_title, 'title': sec.title(lang),
                    'subtitle': (sec.subtitle_en if lang == 'en' else sec.subtitle_ar) or '',
                    'link_url': sec.link_url or '/shop',
                    'link_label': (sec.link_label_en if lang == 'en' else sec.link_label_ar) or ('View all' if lang == 'en' else 'عرض الكل'),
                    'show_link': sec.show_link, 'style': sec.style or 'rail',
                    'columns': max(2, sec.columns or 2),
                    'bg': sec.bg_color or '', 'pad_y': sec.pad_y if sec.pad_y is not None else 20,
                    'html': (sec.html_en if lang == 'en' else sec.html_ar) or '',
                    'image': self._sec_image(sec, lang),
                    'limit': max(4, min(sec.limit or 12, 30)),
                    'seed': seed,
                    'show_save': sec.show_save_badge,
                    'show_disc': sec.show_discount_badge,
                    'cat_width': sec.cat_width or 250,
                    'hero_height': sec.hero_height or 620,
                    'icon': sec.panel_icon or '🎁',
                    'btn': (sec.panel_btn_en if lang == 'en' else sec.panel_btn_ar) or ('Go' if lang == 'en' else 'اذهب'),
                    'panel_link': sec.panel_link or '/web/signup',
                    'color1': sec.panel_color1 or '#FFD24D',
                    'color2': sec.panel_color2 or '#F4A100',
                    'flash_label': (sec.flash_label_en if lang == 'en' else sec.flash_label_ar) or ('Ends in' if lang == 'en' else 'تنتهي خلال'),
                    'fcolor1': sec.flash_color1 or '#E63946',
                    'fcolor2': sec.flash_color2 or '#F26A2E',
                    'flash_btn': (sec.flash_btn_en if lang == 'en' else sec.flash_btn_ar) or ('View all' if lang == 'en' else 'عرض الكل'),
                    'flash_end': (sec.flash_end.strftime('%Y-%m-%dT%H:%M:%SZ') if sec.flash_end else ''),
                    'flash_daily': sec.flash_daily,
                }
                if sec.section_type in ('product_row', 'category_strip', 'flash_deals'):
                    d['products'] = self._home_products(sec, force='discounted' if sec.section_type == 'flash_deals' else None)
                elif sec.section_type in ('dept_spotlight', 'category_grid'):
                    d['cats'] = self._home_departments(lang, limit=d['limit'])
                elif sec.section_type == 'brand_strip':
                    d['brands'] = self._home_brands(d['limit'])
                elif sec.section_type == 'stats_bar':
                    d['stats'] = self._home_stats(lang)
                elif sec.section_type == 'testimonials':
                    d['reviews'] = self._home_testimonials(lang)
                elif sec.section_type == 'deal_of_day':
                    src = sec.product_source if sec.product_source and sec.product_source != 'newest' else 'discounted'
                    prods = self._home_products(sec, force=src)
                    d['deal'] = prods[0] if prods else None
                elif sec.section_type == 'promo_banners':
                    d['banners'] = self._promo_banners(sec)
                elif sec.section_type == 'category_tabs':
                    d['tabs'] = self._home_tabs(max(2, min(sec.limit or 5, 8)))
                elif sec.section_type == 'recently_viewed':
                    d['seed'] = seed  # rendered client-side from localStorage
                elif sec.section_type == 'infinite_products':
                    d['products'] = self._cards(self._random_page(seed, 0, d['limit']))
                elif sec.section_type == 'new_user_bonus':
                    d['products'] = self._home_products(sec, force=(sec.product_source or 'newest'))
                if sec.section_type == 'flash_deals' and d.get('products'):
                    fs = sec.flash_sort or 'disc_desc'
                    if fs == 'disc_desc':
                        d['products'].sort(key=lambda p: -(p.get('discount') or 0))
                    elif fs == 'price_asc':
                        d['products'].sort(key=lambda p: p.get('price') or 0)
                    elif fs == 'price_desc':
                        d['products'].sort(key=lambda p: -(p.get('price') or 0))
                # category-scoped block: auto title + "view all" link from the chosen category
                if sec.product_source == 'category' and sec.category_id:
                    if not d['title']:
                        d['title'] = sec.category_id.name or ''
                    if not sec.link_url or sec.link_url == '/shop':
                        d['link_url'] = '/shop/category/%d' % sec.category_id.id
                sections.append(d)
        # Banggood layout: fold the new-user bonus that follows the hero into the hero's left column
        for i, d in enumerate(sections):
            if d['type'] == 'hero_slider':
                nxt = sections[i + 1] if i + 1 < len(sections) else None
                if nxt and nxt['type'] == 'new_user_bonus':
                    d['bonus'] = nxt
                    nxt['_skip'] = True
                break
        # ── SEO: Product ItemList structured data from the rendered products ──
        items = []
        for sd in sections:
            for p in (sd.get('products') or []):
                if len(items) >= 24:
                    break
                items.append({
                    '@type': 'ListItem', 'position': len(items) + 1,
                    'item': {
                        '@type': 'Product', 'name': p['name'],
                        'url': 'https://www.uellow.com' + (p['url'] or '/'),
                        'image': 'https://www.uellow.com' + (p['image'] or ''),
                        'offers': {'@type': 'Offer', 'price': '%.3f' % (p['price'] or 0),
                                   'priceCurrency': 'KWD',
                                   'availability': 'https://schema.org/InStock'},
                    },
                })
            if len(items) >= 24:
                break
        ld = {'@context': 'https://schema.org', '@type': 'ItemList', 'itemListElement': items}
        structured = Markup(json.dumps(ld, ensure_ascii=False).replace('<', '\\u003c'))
        # ── FAQ structured data (helps AI answer engines cite Uellow) ──
        faqs_ar = [
            ('هل توصّلون لكل مناطق الكويت؟', 'نعم، Uellow (أويلو) توفّر توصيلًا سريعًا لجميع مناطق الكويت، مع توصيل مجاني على الطلبات المؤهلة.'),
            ('هل الدفع عند الاستلام متاح؟', 'نعم، يمكنك الدفع نقدًا عند الاستلام أو الدفع الإلكتروني الآمن عبر البطاقة.'),
            ('هل يوجد تقسيط على المنتجات؟', 'نعم، يمكنك التقسيط على 4 دفعات وعبر Taly و Ci-Net على المنتجات المؤهلة.'),
            ('ما هي سياسة الإرجاع؟', 'إرجاع سهل خلال 14 يومًا من الاستلام.'),
            ('هل عملية الدفع آمنة؟', 'نعم، جميع المدفوعات تتم عبر اتصال مشفّر SSL وحماية كاملة للبيانات.'),
        ]
        faqs_en = [
            ('Do you deliver across Kuwait?', 'Yes. Uellow offers fast delivery to all areas of Kuwait, with free delivery on qualifying orders.'),
            ('Is cash on delivery available?', 'Yes, you can pay cash on delivery or use secure online card payment.'),
            ('Do you offer installments?', 'Yes — pay in 4 instalments and via Taly and Ci-Net on eligible products.'),
            ('What is the return policy?', 'Easy returns within 14 days of delivery.'),
            ('Is payment secure?', 'Yes, all payments use an SSL-encrypted, fully protected checkout.'),
        ]
        faqs = faqs_ar if lang == 'ar' else faqs_en
        faq = {'@context': 'https://schema.org', '@type': 'FAQPage',
               'mainEntity': [{'@type': 'Question', 'name': q,
                               'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faqs]}
        faq_ld = Markup(json.dumps(faq, ensure_ascii=False).replace('<', '\\u003c'))
        # ── LCP: preload the first hero slide image (loads via JS otherwise) ──
        hero_preload = ''
        try:
            hero_sec = page.section_ids.filtered(lambda s: s.section_type == 'hero_slider' and s.active)[:1] if page else None
            sl = hero_sec.slider_id if hero_sec else False
            if sl:
                slides = sl.slide_ids.filtered(
                    lambda s: s.active and s.device == 'desktop' and (s.language == lang or not s.language)
                ).sorted('sequence')
                if not slides:
                    slides = sl.slide_ids.filtered(lambda s: s.active and s.device == 'desktop').sorted('sequence')
                if slides:
                    hero_preload = slides[0].get_src() or ''
        except Exception:
            hero_preload = ''
        meta_title = (page and ((page.meta_title_ar if lang == 'ar' else page.meta_title_en) or page.name)) or 'Uellow'
        meta_desc = (page and (page.meta_description_ar if lang == 'ar' else page.meta_description_en)) or (
            'تسوّق أونلاين في الكويت: جوّالات، إلكترونيات، أجهزة منزلية وأزياء وعروض يومية مع توصيل سريع وأقساط مريحة.'
            if lang == 'ar' else
            'Shop online in Kuwait: phones, electronics, home appliances, fashion and daily deals with fast delivery and easy installments.')
        return request.render('uellow_home_slider.home_preview_page', {
            'page': page, 'sections': sections, 'is_ar': lang == 'ar', 'lang': lang,
            'structured_data': structured, 'faq_ld': faq_ld, 'seo_desc': meta_desc, 'seo_title': meta_title,
            'website_meta_description': meta_desc, 'website_meta_title': meta_title,
            'hero_preload': hero_preload,
        })

    @http.route(['/home-preview/more'], type='http', auth='public', website=True, sitemap=False)
    def home_more(self, seed=0, page=1, limit=12, **kw):
        try:
            seed = int(seed); page = int(page); limit = max(4, min(int(limit), 30))
        except Exception:
            seed, page, limit = 0, 1, 12
        lang = 'en' if (request.env.lang or '').lower().startswith('en') else 'ar'
        recs = self._random_page(seed, page, limit)
        return request.render('uellow_home_slider.home_cards',
                              {'products': self._cards(recs), 'is_ar': lang == 'ar',
                               'show_save': True, 'show_disc': True})

    @http.route(['/llms.txt'], type='http', auth='public', website=True, sitemap=False)
    def llms_txt(self, **kw):
        # real top-level categories, so LLMs learn what Uellow actually sells
        cat_lines = ''
        try:
            wid = request.website.id if request.website else False
            cats = request.env['product.public.category'].sudo().search(
                [('parent_id', '=', False), ('website_id', 'in', [False, wid])],
                order='sequence, name', limit=25)
            cat_lines = ''.join('- %s: https://www.uellow.com/shop/category/%d\n' % (c.name, c.id) for c in cats)
        except Exception:
            cat_lines = ''
        body = (
            "# Uellow (أويلو)\n\n"
            "> Uellow (uellow.com) is a leading online marketplace in Kuwait for electronics, mobile "
            "phones, home appliances, watches, fragrances, fashion, beauty, baby products and more, "
            "with fast delivery across Kuwait, cash on delivery, secure payment and installment plans.\n\n"
            "## About\n"
            "- Brand: Uellow / أويلو\n"
            "- Market: Kuwait (توصيل سريع لكل مناطق الكويت)\n"
            "- Payment: Secure card payment, Cash on Delivery, Installments (4 payments, Taly, Ci-Net)\n"
            "- Delivery: Fast delivery across Kuwait; free delivery on qualifying orders\n"
            "- Returns: Easy 14-day returns\n"
            "- Support: 24/7 customer service\n"
            "- Apps: iOS and Android\n\n"
            "## Shop by category\n" + cat_lines + "\n"
            "## Key pages\n"
            "- Home: https://www.uellow.com/\n"
            "- Shop / all products: https://www.uellow.com/shop\n"
            "- Sitemap: https://www.uellow.com/sitemap.xml\n"
        )
        return request.make_response(body, headers=[
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Cache-Control', 'public, max-age=86400')])

    @http.route(['/guides'], type='http', auth='public', website=True, sitemap=True)
    def guides_index(self, **kw):
        lang = 'en' if (request.env.lang or '').lower().startswith('en') else 'ar'
        guides = [{'slug': g[0], 'title': (g[2] if lang == 'ar' else g[3])} for g in GUIDES]
        return request.render('uellow_home_slider.guides_index', {'guides': guides, 'is_ar': lang == 'ar'})

    @http.route(['/guide/<string:slug>'], type='http', auth='public', website=True, sitemap=sitemap_guides)
    def guide_page(self, slug, **kw):
        g = next((x for x in GUIDES if x[0] == slug), None)
        if not g:
            return request.not_found()
        _slug, cat_id, ar_t, en_t, ar_n, en_n = g
        lang = 'en' if (request.env.lang or '').lower().startswith('en') else 'ar'
        Tmpl = request.env['product.template'].sudo()
        dom = self._base_dom()
        recs = Tmpl.browse([])
        if cat_id:
            recs = Tmpl.search(dom + [('public_categ_ids', 'child_of', cat_id)],
                               limit=12, order='website_sequence, create_date desc')
        if not recs:
            recs = Tmpl.search(dom, limit=12, order='create_date desc')
        products = self._cards(recs)
        topic = ar_t if lang == 'ar' else en_t
        noun = ar_n if lang == 'ar' else en_n
        cat_url = ('/shop/category/%d' % cat_id) if cat_id else '/shop'
        base_url = 'https://www.uellow.com'
        if lang == 'ar':
            lead = ('يقدّم Uellow (أويلو) أفضل خيارات %s: منتجات أصلية 100%%، تقسيط مريح على 4 دفعات أو عبر Taly و Ci-Net، '
                    'دفع عند الاستلام، توصيل سريع لكل مناطق الكويت، وضمان وإرجاع سهل خلال 14 يومًا. تحت أبرز المنتجات المتاحة وأكثر الأسئلة شيوعًا.') % topic
            faqs = [
                ('كيف أشتري %s بالتقسيط في الكويت من Uellow؟' % noun,
                 'اختر المنتج، وفي صفحة الدفع اختر التقسيط: 4 دفعات أو عبر Taly أو Ci-Net على المنتجات المؤهلة، وأكمل الطلب في دقائق.'),
                ('هل يوجد دفع عند الاستلام؟', 'نعم، ادفع نقدًا عند الاستلام أو إلكترونيًا بأمان.'),
                ('كم مدة التوصيل داخل الكويت؟', 'توصيل سريع لكل المناطق، مع توصيل مجاني على الطلبات المؤهلة.'),
                ('هل المنتجات أصلية وعليها ضمان؟', 'نعم، أصلية 100% مع ضمان وإرجاع سهل خلال 14 يومًا.'),
            ]
            headline = topic + ' — دليل 2026'
        else:
            lead = ('Uellow offers the best %s: 100%% genuine products, easy installments (4 payments or via Taly and Ci-Net), '
                    'cash on delivery, fast delivery to all areas of Kuwait, warranty and easy 14-day returns. Below are top products and common questions.') % topic
            faqs = [
                ('How do I buy a %s on installments in Kuwait from Uellow?' % noun,
                 'Pick the product, then at checkout choose installments: 4 payments or via Taly or Ci-Net on eligible products, and finish in minutes.'),
                ('Is cash on delivery available?', 'Yes, pay cash on delivery or securely online.'),
                ('How fast is delivery in Kuwait?', 'Fast delivery to all areas, with free delivery on qualifying orders.'),
                ('Are products genuine and under warranty?', 'Yes, 100% genuine with warranty and easy 14-day returns.'),
            ]
            headline = topic + ' — 2026 guide'
        item_els = [{'@type': 'ListItem', 'position': i + 1, 'url': base_url + (p['url'] or '/'), 'name': p['name']}
                    for i, p in enumerate(products)]
        graph = [
            {'@context': 'https://schema.org', '@type': 'Article', 'headline': headline,
             'author': {'@type': 'Organization', 'name': 'Uellow'},
             'publisher': {'@type': 'Organization', 'name': 'Uellow'},
             'mainEntityOfPage': base_url + '/guide/' + _slug},
            {'@context': 'https://schema.org', '@type': 'FAQPage',
             'mainEntity': [{'@type': 'Question', 'name': q,
                             'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faqs]},
            {'@context': 'https://schema.org', '@type': 'ItemList', 'itemListElement': item_els},
        ]
        schema = Markup(json.dumps(graph, ensure_ascii=False).replace('<', '\\u003c'))
        return request.render('uellow_home_slider.guide_page', {
            'products': products, 'is_ar': lang == 'ar', 'faqs': faqs, 'schema': schema,
            'g_title': topic, 'g_lead': lead, 'g_cat_url': cat_url,
            'show_save': True, 'show_disc': True,
        })

    # ── helpers ───────────────────────────────────────────────
    def _base_dom(self):
        wid = request.website.id if request.website else False
        return [('is_published', '=', True), ('sale_ok', '=', True), ('website_id', 'in', [False, wid])]

    def _sec_image(self, sec, lang):
        if sec.image:
            return '/web/image/uellow.home.section/%d/image' % sec.id
        if lang == 'ar' and sec.image_url_ar:
            return sec.image_url_ar
        return sec.image_url or ''

    def _home_departments(self, lang, limit=14):
        PC = request.env['product.public.category'].sudo()
        wid = request.website.id if request.website else False
        out = []
        for c in PC.search([('parent_id', '=', False), ('website_id', 'in', [False, wid])],
                            order='sequence, name', limit=max(4, min(limit or 14, 30))):
            out.append({'name': c.name, 'url': '/shop/category/%d' % c.id,
                        'image': ('/web/image/product.public.category/%d/image_256' % c.id) if c.image_128 else ''})
        return out

    def _home_tabs(self, ncats=5, nprods=8):
        """Top categories, each with a few products, for a tabbed block."""
        PC = request.env['product.public.category'].sudo()
        Tmpl = request.env['product.template'].sudo()
        base = self._base_dom()
        wid = request.website.id if request.website else False
        out = []
        cats = PC.search([('parent_id', '=', False), ('website_id', 'in', [False, wid])],
                         order='sequence, name', limit=ncats)
        for c in cats:
            recs = Tmpl.search(base + [('public_categ_ids', 'child_of', c.id)],
                               limit=nprods, order='create_date desc')
            if recs:
                out.append({'name': c.name, 'url': '/shop/category/%d' % c.id,
                            'products': self._cards(recs)})
        return out

    def _promo_banners(self, sec):
        out = []
        slots = [(sec.image, sec.image_url, sec.link_url, 'image'),
                 (sec.image2, sec.image2_url, sec.link_url2, 'image2'),
                 (sec.image3, sec.image3_url, sec.link_url3, 'image3')]
        for img, url, link, field in slots:
            src = ('/web/image/uellow.home.section/%d/%s' % (sec.id, field)) if img else (url or '')
            if src:
                out.append({'image': src, 'link': link or '/shop'})
        return out

    def _home_stats(self, lang):
        env = request.env
        wid = request.website.id if request.website else False
        Tmpl = env['product.template'].sudo()
        try:
            prod = Tmpl.search_count(self._base_dom())
        except Exception:
            prod = 0
        try:
            cats = env['product.public.category'].sudo().search_count([('website_id', 'in', [False, wid])])
        except Exception:
            cats = 0
        try:
            battrs = request.website._get_brand_attributes()
            brands = env['product.attribute.value'].sudo().search_count(
                [('attribute_id', 'in', battrs.ids)]) if battrs else 0
        except Exception:
            brands = 0
        L = (lambda ar, en: ar if lang == 'ar' else en)
        return [
            {'n': prod, 's': '+', 'label': L('منتج', 'Products')},
            {'n': brands, 's': '+', 'label': L('علامة تجارية', 'Brands')},
            {'n': cats, 's': '+', 'label': L('قسم', 'Categories')},
            {'n': None, 'txt': '24/7', 'label': L('دعم ومساندة', 'Support')},
        ]

    def _home_testimonials(self, lang):
        ar = (lang == 'ar')
        data = [
            ('نورة العتيبي', 'الكويت', 'توصيل أسرع من المتوقّع والمنتج أصلي 100%. تجربة تسوّق ممتازة!',
             'Noura Al-Otaibi', 'Kuwait', 'Faster delivery than expected and 100% genuine products. Excellent experience!'),
            ('أحمد الرشيد', 'حولي', 'أسعار منافسة وخدمة عملاء بترد بسرعة. صرت أطلب منهم باستمرار.',
             'Ahmed Al-Rashid', 'Hawally', 'Great prices and quick customer service. Now I order regularly.'),
            ('سارة المطيري', 'الفروانية', 'الأقساط سهّلت عليّ الشراء، والتغليف كان احترافي ومرتّب.',
             'Sara Al-Mutairi', 'Farwaniya', 'Installments made buying easy, and the packaging was neat and professional.'),
            ('يوسف العنزي', 'الجهراء', 'تشكيلة ضخمة وعروض حقيقية. أنصح فيهم بشدّة.',
             'Yousef Al-Anzi', 'Jahra', 'Huge selection and real deals. Highly recommended.'),
        ]
        out = []
        for a_name, a_city, a_txt, e_name, e_city, e_txt in data:
            out.append({
                'name': a_name if ar else e_name,
                'city': a_city if ar else e_city,
                'text': a_txt if ar else e_txt,
                'initial': (a_name if ar else e_name)[:1],
            })
        return out

    def _home_brands(self, limit=12):
        """Top storefront brands (product.attribute.value) with their logos."""
        out = []
        try:
            brands = request.website._uc_category_brands(False, limit=max(4, min(limit or 12, 30)))
            for b in brands:
                out.append({
                    'name': b.name,
                    'url': '/shop?attribute_value=%d' % b.id,
                    'image': ('/web/image/product.attribute.value/%d/dr_image' % b.id) if getattr(b, 'dr_image', False) else '',
                })
        except Exception:
            out = []
        return out

    def _cards(self, recs):
        out = []
        for p in recs:
            price = p.list_price or 0.0
            cmp = getattr(p, 'compare_list_price', 0.0) or 0.0
            disc = int(round((1 - price / cmp) * 100)) if (cmp and price and cmp > price) else 0
            out.append({
                'name': p.name or '', 'url': p.website_url or ('/shop/%d' % p.id),
                'image': '/web/image/product.template/%d/image_256' % p.id,
                'price': price, 'currency': p.currency_id.symbol or 'KD',
                'compare': cmp if disc else 0, 'discount': disc,
                'save': round(cmp - price, 3) if disc else 0,
            })
        return out

    def _home_products(self, sec, force=None):
        Tmpl = request.env['product.template'].sudo()
        base = self._base_dom()
        src = force or sec.product_source or 'newest'
        limit = max(4, min(sec.limit or 12, 30))
        recs = Tmpl.browse([])
        try:
            if not force and sec.product_ids:
                recs = sec.product_ids.filtered(lambda p: p.is_published)[:limit]
            elif src == 'category' and sec.category_id:
                recs = Tmpl.search(base + [('public_categ_ids', 'child_of', sec.category_id.id)], limit=limit, order='create_date desc')
            elif src == 'discounted':
                dom = base + ([('compare_list_price', '>', 0)] if 'compare_list_price' in Tmpl._fields else [])
                cands = Tmpl.search(dom, limit=limit * 4, order='create_date desc')
                md = max(0, sec.min_discount or 0)

                def _disc(p):
                    c = getattr(p, 'compare_list_price', 0) or 0
                    pr = p.list_price or 0
                    return int(round((1 - pr / c) * 100)) if (c and pr and c > pr) else 0
                recs = cands.filtered(lambda p: _disc(p) >= max(1, md))[:limit]
            elif src in ('bestsellers', 'trending'):
                cands = Tmpl.search(base, limit=limit * 4, order='create_date desc')
                try:
                    recs = cands.sorted(lambda p: -(p.sales_count or 0))[:limit]
                except Exception:
                    recs = cands[:limit]
            elif src == 'installments':
                recs = Tmpl.search(base + [('list_price', '>=', 10)], limit=limit, order='create_date desc')
            else:
                recs = Tmpl.search(base, limit=limit, order='create_date desc')
        except Exception:
            recs = Tmpl.search(base, limit=limit, order='create_date desc')
        return self._cards(recs)

    def _random_page(self, seed, page, limit):
        Tmpl = request.env['product.template'].sudo()
        # cap the pool (a large catalogue's full id list is slow to fetch/shuffle)
        ids = Tmpl.search(self._base_dom(), limit=500).ids
        random.Random(seed or 1).shuffle(ids)
        chunk = ids[page * limit:(page + 1) * limit]
        # keep DB order stable but preserve our shuffled order
        recs = Tmpl.browse(chunk)
        by_id = {r.id: r for r in recs}
        return [by_id[i] for i in chunk if i in by_id]
