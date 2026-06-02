# -*- coding: utf-8 -*-
"""Auto-fill SEO defaults on product.template + emit Product JSON-LD.

Hooks
-----
- `write` / `create`: if a product is published and has no meta_title or
  meta_description, fill them automatically from the product's name +
  list_price + brand.
- `_get_seo_jsonld()`: returns a fully-built Product JSON-LD dict for
  rendering in the website template.
- Public method `action_seo_autofill_missing_bulk()` — wizard hook to
  back-fill the entire catalog.
"""
import json

from odoo import api, fields, models, _


class ProductTemplateSEO(models.Model):
    _inherit = 'product.template'

    # ── Auto-fill on create/write ─────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for r in recs:
            try:
                r._seo_autofill_if_missing()
            except Exception:
                pass
        return recs

    def write(self, vals):
        res = super().write(vals)
        # Only auto-fill when the product gains a name or becomes published;
        # don't loop on every write.
        if 'name' in vals or 'is_published' in vals:
            for r in self:
                try:
                    r._seo_autofill_if_missing()
                except Exception:
                    pass
        return res

    def _seo_autofill_if_missing(self):
        """Fill empty website_meta_title/description from product data."""
        self.ensure_one()
        if not self.is_published:
            return
        vals = {}
        if not (self.website_meta_title or '').strip():
            vals['website_meta_title'] = self._seo_default_title()
        if not (self.website_meta_description or '').strip():
            vals['website_meta_description'] = self._seo_default_description()
        if vals:
            super(ProductTemplateSEO, self.with_context(skip_seo_autofill=True)).write(vals)

    # ── Default meta builders ────────────────────────────────────────
    def _seo_default_title(self):
        """Build a keyword-rich title within 60 chars.
        Format: <product> | <brand> | Uellow"""
        self.ensure_one()
        brand = ''
        if getattr(self, 'brand_id', False) and self.brand_id.name:
            brand = self.brand_id.name
        else:
            for line in self.attribute_line_ids:
                an = (line.attribute_id.name or '').lower()
                if 'brand' in an or 'ماركة' in an or 'علامة' in an:
                    v = line.value_ids[:1]
                    if v:
                        brand = v.name or ''
                    break
        site = (self.env['website'].sudo().search([], limit=1).name or 'Uellow')
        name = (self.name or '').strip()
        # Build candidates, trim from the right side
        if brand:
            cand = f'{name} | {brand} | {site}'
        else:
            cand = f'{name} | {site}'
        if len(cand) > 60:
            # truncate name first
            keep = 60 - len(' | ' + (brand or '') + ' | ' + site)
            cand = f'{name[:max(0, keep-1)]}… | {brand} | {site}' if brand \
                   else f'{name[:max(0, keep-1)]}… | {site}'
        return cand

    def _seo_default_description(self):
        """Build a 130-160 char meta description from name + price + brand."""
        self.ensure_one()
        name = (self.name or '').strip()
        price = self.list_price or 0
        cur = self.currency_id.symbol if self.currency_id else 'KD'
        brand = ''
        if getattr(self, 'brand_id', False) and self.brand_id.name:
            brand = self.brand_id.name
        bits = [f'Buy {name}']
        if brand: bits.append(f'by {brand}')
        if price: bits.append(f'from {price:.3f} {cur}')
        bits.append('with fast delivery in Kuwait & GCC. Free shipping on eligible orders. Shop at Uellow.')
        out = ' '.join(bits)
        # Trim to 158 chars to be safe (Google shows ~155)
        if len(out) > 158:
            out = out[:157].rstrip() + '…'
        return out

    # ── JSON-LD Product schema ───────────────────────────────────────
    def _get_seo_jsonld(self):
        """Return a fully-formed Product JSON-LD dict ready for inclusion
        in the website template. Includes Offer, AggregateRating if any
        reviews, Brand, and images."""
        self.ensure_one()
        Param = self.env['ir.config_parameter'].sudo()
        base = (Param.get_param('web.base.url') or '').rstrip('/')
        url = base + (self.website_url or f'/shop/{self.id}')
        cur = self.currency_id
        cur_code = cur.name if cur else 'KWD'
        price = float(self.list_price or 0)
        compare = float(getattr(self, 'compare_list_price', 0) or 0)
        images = []
        if self.image_1920:
            images.append(f'{base}/web/image/product.template/{self.id}/image_1920')
        for img in (self.product_template_image_ids or []):
            images.append(f'{base}/web/image/product.image/{img.id}/image_1024')

        brand_obj = None
        if getattr(self, 'brand_id', False) and self.brand_id.name:
            brand_obj = {'@type': 'Brand', 'name': self.brand_id.name}
        else:
            for line in self.attribute_line_ids:
                an = (line.attribute_id.name or '').lower()
                if 'brand' in an or 'ماركة' in an or 'علامة' in an:
                    v = line.value_ids[:1]
                    if v:
                        brand_obj = {'@type': 'Brand', 'name': v.name or ''}
                    break

        offer = {
            '@type': 'Offer',
            'url': url,
            'priceCurrency': cur_code,
            'price': f'{price:.3f}',
            'availability': 'https://schema.org/InStock' if self.is_published else 'https://schema.org/OutOfStock',
            'itemCondition': 'https://schema.org/NewCondition',
            'seller': {'@type': 'Organization', 'name': 'Uellow'},
        }
        if compare and compare > price:
            offer['priceSpecification'] = {
                '@type': 'UnitPriceSpecification',
                'price': f'{price:.3f}',
                'priceCurrency': cur_code,
                'referenceQuantity': {'@type': 'QuantitativeValue', 'value': 1},
            }

        data = {
            '@context': 'https://schema.org/',
            '@type': 'Product',
            'name': self.name or '',
            'description': (self.description_sale or self.description or self.name or '')[:5000],
            'sku': self.default_code or str(self.id),
            'mpn': self.default_code or str(self.id),
            'image': images,
            'url': url,
            'offers': offer,
        }
        if brand_obj:
            data['brand'] = brand_obj

        # Aggregate rating — if uellow_product_reviews exists
        try:
            avg = getattr(self, 'rating_avg', 0)
            count = getattr(self, 'rating_count', 0)
            if avg and count:
                data['aggregateRating'] = {
                    '@type': 'AggregateRating',
                    'ratingValue': f'{float(avg):.1f}',
                    'reviewCount': int(count),
                    'bestRating': '5', 'worstRating': '1',
                }
        except Exception:
            pass

        return data

    def _get_breadcrumb_jsonld(self):
        """BreadcrumbList JSON-LD: Home > Category > Product"""
        self.ensure_one()
        Param = self.env['ir.config_parameter'].sudo()
        base = (Param.get_param('web.base.url') or '').rstrip('/')
        items = [{
            '@type': 'ListItem', 'position': 1,
            'name': 'Home', 'item': base + '/',
        }]
        pos = 2
        for cat in (self.public_categ_ids[:1] if self.public_categ_ids else []):
            items.append({
                '@type': 'ListItem', 'position': pos,
                'name': cat.name or '',
                'item': base + f'/shop/category/{cat.id}',
            })
            pos += 1
        items.append({
            '@type': 'ListItem', 'position': pos,
            'name': self.name or '',
            'item': base + (self.website_url or f'/shop/{self.id}'),
        })
        return {
            '@context': 'https://schema.org/',
            '@type': 'BreadcrumbList',
            'itemListElement': items,
        }

    # ── Bulk auto-fix ────────────────────────────────────────────────
    @api.model
    def action_seo_autofill_missing_bulk(self, batch=200):
        """Fill missing meta on every published product. Safe to re-run."""
        dom = [
            ('is_published', '=', True),
            '|', '|',
            ('website_meta_title', '=', False),
            ('website_meta_title', '=', ''),
            ('website_meta_description', '=', False),
        ]
        recs = self.search(dom, limit=batch)
        for r in recs:
            r._seo_autofill_if_missing()
        return len(recs)
