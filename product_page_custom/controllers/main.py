# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class PpcController(http.Controller):

    @http.route('/ppc/bulk_pricing/<int:template_id>', type='json', auth='public', website=True)
    def bulk_pricing(self, template_id, **kw):
        env = request.env
        tmpl = env['product.template'].sudo().browse(template_id)
        if not tmpl.exists():
            return []
        website = env['website'].get_current_website()
        pricelist = website._get_current_pricelist()
        if not pricelist:
            return []
        cur = env.company.currency_id.symbol or 'KD'
        base_price = tmpl.list_price or 0

        # Get pricelist items for this product/category
        items = pricelist.item_ids.filtered(lambda i:
            i.compute_price == 'percentage' and i.min_quantity > 0 and
            (i.applied_on == '3_global' or
             (i.applied_on == '2_product_category' and i.categ_id and
              (i.categ_id == tmpl.categ_id or i.categ_id in tmpl.categ_id.parent_path.split('/') if tmpl.categ_id else False)) or
             (i.applied_on == '1_product' and i.product_tmpl_id.id == template_id) or
             (i.applied_on == '0_product_variant' and i.product_id.product_tmpl_id.id == template_id))
        ).sorted('min_quantity')

        if not items:
            # Fallback: all global percentage items
            items = pricelist.item_ids.filtered(lambda i:
                i.compute_price == 'percentage' and i.min_quantity > 0
            ).sorted('min_quantity')

        result = []
        seen_qty = set()
        for item in items:
            qty = int(item.min_quantity)
            if qty in seen_qty:
                continue
            seen_qty.add(qty)
            disc = item.percent_price or 0
            price = round(base_price * (1 - disc/100), 3)
            result.append({
                'min_qty': qty,
                'price': price,
                'orig': base_price,
                'disc': round(disc),
                'cur': cur,
            })

        return result

    @http.route('/ppc/variant_images/<int:product_tmpl_id>', type='json', auth='public', website=True)
    def variant_images(self, product_tmpl_id, **kw):
        """Return map: ptav_id → product_id for each variant"""
        env = request.env
        tmpl = env['product.template'].sudo().browse(product_tmpl_id)
        if not tmpl.exists():
            return {}
        result = {}
        for variant in tmpl.product_variant_ids:
            # Get color ptav ids for this variant
            for ptav in variant.product_template_attribute_value_ids:
                attr = ptav.attribute_id
                if attr.display_type == 'color' or attr.name.lower() in ('color','colour','لون'):
                    result[ptav.id] = {
                        'product_id': variant.id,
                        'has_image': bool(variant.image_variant_128),
                    }
        return result

    @http.route('/ppc/related/<int:product_id>', type='json', auth='public', website=True)
    def related_products(self, product_id, offset=0, limit=48, **kw):
        env = request.env
        product = env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return []
        cur = env.company.currency_id.symbol or 'KD'
        ids_seen = set([product_id])
        result = []

        def fmt(rp):
            orig  = rp.compare_list_price or 0
            price = rp.list_price or 0
            disc  = round((1-price/orig)*100) if orig > price+0.001 else 0
            return {'id':rp.id,'name':rp.name or '',
                    'url':rp.website_url or '/shop/%d'%rp.id,
                    'price':price,'orig':orig,'disc':disc,'cur':cur}

        def add_products(domain, order='website_sequence asc', lim=None):
            prods = env['product.template'].sudo().search(domain, limit=lim or limit, order=order)
            for rp in prods:
                if rp.id not in ids_seen:
                    ids_seen.add(rp.id)
                    result.append(fmt(rp))

        base = [('id','!=',product_id),('is_published','=',True)]

        # Same category + similar name keywords first
        if product.categ_id:
            cat_domain = base + [('categ_id','=',product.categ_id.id)]
            words = [w for w in (product.name or '').split() if len(w) > 2]
            if words:
                add_products(cat_domain + [('name','ilike',words[0])], lim=12)
            if len(result) < 8:
                add_products(cat_domain, lim=16)

        # Same public category
        if product.public_categ_ids and len(result) < 12:
            for pc in product.public_categ_ids[:2]:
                add_products(base + [('public_categ_ids','in',[pc.id])], lim=12)

        return result
    @http.route('/ppc/top_selling', type='json', auth='public', website=True)
    def top_selling(self, product_id, offset=0, limit=48, **kw):
        env = request.env
        product = env['product.template'].sudo().browse(product_id)
        if not product.exists():
            return []
        cur = env.company.currency_id.symbol or 'KD'
        ids_seen = set([product_id])
        result = []

        def fmt(rp):
            orig  = rp.compare_list_price or 0
            price = rp.list_price or 0
            disc  = round((1-price/orig)*100) if orig > price+0.001 else 0
            return {'id':rp.id,'name':rp.name or '',
                    'url':rp.website_url or '/shop/%d'%rp.id,
                    'price':price,'orig':orig,'disc':disc,'cur':cur}

        base = [('id','!=',product_id),('is_published','=',True)]

        # Explore More: same category only
        if product.categ_id:
            prods = env['product.template'].sudo().search(
                base + [('categ_id','=',product.categ_id.id)],
                limit=limit, order='website_sequence asc')
            for rp in prods:
                if rp.id not in ids_seen:
                    ids_seen.add(rp.id)
                    result.append(fmt(rp))

        # Fallback: same public category
        if product.public_categ_ids and len(result) < 8:
            for pc in product.public_categ_ids[:1]:
                prods = env['product.template'].sudo().search(
                    base + [('public_categ_ids','in',[pc.id])], limit=16)
                for rp in prods:
                    if rp.id not in ids_seen:
                        ids_seen.add(rp.id)
                        result.append(fmt(rp))

        return result
    @http.route('/ppc/bulk_pricing/<int:template_id>', type='json', auth='public', website=True)
    def bulk_pricing(self, template_id, **kw):
        env = request.env
        tmpl = env['product.template'].sudo().browse(template_id)
        if not tmpl.exists():
            return []
        website = env['website'].get_current_website()
        pricelist = website._get_current_pricelist()
        if not pricelist:
            return []
        cur = env.company.currency_id.symbol or 'KD'
        base_price = tmpl.list_price or 0

        # Get pricelist items for this product/category
        items = pricelist.item_ids.filtered(lambda i:
            i.compute_price == 'percentage' and i.min_quantity > 0 and
            (i.applied_on == '3_global' or
             (i.applied_on == '2_product_category' and i.categ_id and
              (i.categ_id == tmpl.categ_id or i.categ_id in tmpl.categ_id.parent_path.split('/') if tmpl.categ_id else False)) or
             (i.applied_on == '1_product' and i.product_tmpl_id.id == template_id) or
             (i.applied_on == '0_product_variant' and i.product_id.product_tmpl_id.id == template_id))
        ).sorted('min_quantity')

        if not items:
            # Fallback: all global percentage items
            items = pricelist.item_ids.filtered(lambda i:
                i.compute_price == 'percentage' and i.min_quantity > 0
            ).sorted('min_quantity')

        result = []
        seen_qty = set()
        for item in items:
            qty = int(item.min_quantity)
            if qty in seen_qty:
                continue
            seen_qty.add(qty)
            disc = item.percent_price or 0
            price = round(base_price * (1 - disc/100), 3)
            result.append({
                'min_qty': qty,
                'price': price,
                'orig': base_price,
                'disc': round(disc),
                'cur': cur,
            })

        return result

    @http.route('/ppc/variant_images/<int:template_id>', type='json', auth='public', website=True)
    def variant_images(self, template_id, **kw):
        env = request.env
        tmpl = env['product.template'].sudo().browse(template_id)
        if not tmpl.exists():
            return {}
        result = {}
        for variant in tmpl.product_variant_ids:
            ptav_ids = variant.product_template_attribute_value_ids.ids
            has_img = bool(variant.image_variant_128)
            img_url = '/web/image/product.product/%d/image_256' % variant.id
            for ptav_id in ptav_ids:
                result[str(ptav_id)] = {
                    'product_id': variant.id,
                    'img': img_url,
                    'has_img': has_img,
                }
        return result

    @http.route('/ppc/reviews/<int:product_id>', type='json', auth='public', website=True)
    def get_reviews(self, product_id, limit=3, offset=0, **kw):
        env = request.env
        try:
            ratings = env['rating.rating'].sudo().search(
                [('res_model','=','product.template'),('res_id','=',product_id),('is_internal','=',False)],
                limit=limit, offset=offset, order='write_date desc')
            total = env['rating.rating'].sudo().search_count(
                [('res_model','=','product.template'),('res_id','=',product_id),('is_internal','=',False)])
            return {'reviews': [{'id':r.id,'rating':r.rating or 0,'body':r.feedback or '',
                'partner_name':r.partner_id.name if r.partner_id else 'Anonymous',
                'date':r.write_date.strftime('%m/%d/%Y') if r.write_date else ''} for r in ratings],
                'total': total}
        except:
            return {'reviews':[],'total':0}
