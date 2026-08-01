# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class UellowHomePageController(http.Controller):

    @http.route(['/home-preview'], type='http', auth='public', website=True, sitemap=False)
    def home_preview(self, **kw):
        Page = request.env['uellow.home.page'].sudo()
        page = Page.get_live()
        lang = 'en' if (request.env.lang or '').lower().startswith('en') else 'ar'
        sections = []
        if page:
            for sec in page.section_ids.filtered('active').sorted(lambda s: (s.sequence, s.id)):
                d = {
                    'sec': sec,
                    'type': sec.section_type,
                    'show_title': sec.show_title,
                    'title': sec.title(lang),
                    'subtitle': (sec.subtitle_en if lang == 'en' else sec.subtitle_ar) or '',
                    'link_url': sec.link_url or '/shop',
                    'link_label': (sec.link_label_en if lang == 'en' else sec.link_label_ar) or ('View all' if lang == 'en' else 'عرض الكل'),
                    'show_link': sec.show_link,
                    'style': sec.style or 'rail',
                    'columns': max(2, sec.columns or 2),
                    'bg': sec.bg_color or '',
                    'pad_y': sec.pad_y if sec.pad_y is not None else 18,
                    'html': (sec.html_en if lang == 'en' else sec.html_ar) or '',
                    'image': self._sec_image(sec, lang),
                }
                if sec.section_type in ('product_row', 'category_strip'):
                    d['products'] = self._home_products(sec)
                elif sec.section_type == 'dept_spotlight':
                    d['cats'] = self._home_departments(lang)
                sections.append(d)
        return request.render('uellow_home_slider.home_preview_page', {
            'page': page, 'sections': sections, 'is_ar': lang == 'ar', 'lang': lang,
        })

    # ── helpers ───────────────────────────────────────────────
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
            out.append({
                'name': c.name, 'url': '/shop/category/%d' % c.id,
                'image': ('/web/image/product.public.category/%d/image_256' % c.id) if c.image_128 else '',
            })
        return out

    def _home_products(self, sec):
        Tmpl = request.env['product.template'].sudo()
        wid = request.website.id if request.website else False
        base = [('is_published', '=', True), ('sale_ok', '=', True),
                ('website_id', 'in', [False, wid])]
        src = sec.product_source or 'newest'
        limit = max(4, min(sec.limit or 12, 30))
        recs = Tmpl.browse([])
        try:
            if sec.product_ids:
                recs = sec.product_ids.filtered(lambda p: p.is_published)[:limit]
            elif src == 'category' and sec.category_id:
                recs = Tmpl.search(base + [('public_categ_ids', 'child_of', sec.category_id.id)],
                                   limit=limit, order='create_date desc')
            elif src == 'discounted':
                cands = Tmpl.search(base, limit=limit * 4, order='create_date desc')
                recs = cands.filtered(
                    lambda p: (getattr(p, 'compare_list_price', 0) or 0) > (p.list_price or 0))[:limit]
            elif src in ('bestsellers', 'trending'):
                cands = Tmpl.search(base, limit=limit * 4, order='create_date desc')
                try:
                    recs = cands.sorted(lambda p: -(p.sales_count or 0))[:limit]
                except Exception:
                    recs = cands[:limit]
            elif src == 'installments':
                recs = Tmpl.search(base + [('list_price', '>=', 10)], limit=limit, order='create_date desc')
            else:  # newest / you_may_like / fallback
                recs = Tmpl.search(base, limit=limit, order='create_date desc')
        except Exception:
            recs = Tmpl.search(base, limit=limit, order='create_date desc')
        out = []
        for p in recs:
            price = p.list_price or 0.0
            cmp = getattr(p, 'compare_list_price', 0.0) or 0.0
            disc = int(round((1 - price / cmp) * 100)) if (cmp and price and cmp > price) else 0
            out.append({
                'name': p.name or '',
                'url': p.website_url or ('/shop/%d' % p.id),
                'image': '/web/image/product.template/%d/image_256' % p.id,
                'price': price,
                'currency': p.currency_id.symbol or 'KD',
                'compare': cmp if disc else 0,
                'discount': disc,
            })
        return out
