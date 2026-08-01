# -*- coding: utf-8 -*-
import random
from odoo import http
from odoo.http import request


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
                }
                if sec.section_type in ('product_row', 'category_strip', 'flash_deals'):
                    d['products'] = self._home_products(sec, force='discounted' if sec.section_type == 'flash_deals' else None)
                elif sec.section_type == 'dept_spotlight':
                    d['cats'] = self._home_departments(lang)
                elif sec.section_type == 'infinite_products':
                    d['products'] = self._cards(self._random_page(seed, 0, d['limit']))
                sections.append(d)
        return request.render('uellow_home_slider.home_preview_page', {
            'page': page, 'sections': sections, 'is_ar': lang == 'ar', 'lang': lang,
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
                              {'products': self._cards(recs), 'is_ar': lang == 'ar'})

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

    def _home_departments(self, lang):
        PC = request.env['product.public.category'].sudo()
        wid = request.website.id if request.website else False
        out = []
        for c in PC.search([('parent_id', '=', False), ('website_id', 'in', [False, wid])],
                            order='sequence, name', limit=14):
            out.append({'name': c.name, 'url': '/shop/category/%d' % c.id,
                        'image': ('/web/image/product.public.category/%d/image_256' % c.id) if c.image_128 else ''})
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
                cands = Tmpl.search(base, limit=limit * 5, order='create_date desc')
                recs = cands.filtered(lambda p: (getattr(p, 'compare_list_price', 0) or 0) > (p.list_price or 0))[:limit]
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
        ids = Tmpl.search(self._base_dom()).ids
        random.Random(seed or 1).shuffle(ids)
        chunk = ids[page * limit:(page + 1) * limit]
        # keep DB order stable but preserve our shuffled order
        recs = Tmpl.browse(chunk)
        by_id = {r.id: r for r in recs}
        return [by_id[i] for i in chunk if i in by_id]
