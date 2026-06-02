# -*- coding: utf-8 -*-
import re
from odoo import fields, models, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    website_description_ar = fields.Html(
        string="وصف المنتج (عربي)",
        translate=False,
        sanitize=True,
        sanitize_overridable=True,
        help="وصف تفصيلي للمنتج باللغة العربية — يظهر في تاب 'الوصف' بصفحة المنتج، "
             "ويُستخدم كذلك بواسطة Beena AI والأنظمة الخارجية.",
    )

    website_description_en = fields.Html(
        string="Product Description (English)",
        translate=False,
        sanitize=True,
        sanitize_overridable=True,
        help="Detailed product description in English — shown in the Description tab on "
             "the product page. Also used by Beena AI and external integrations.",
    )

    # ──────────────────────────────────────────────────────────────────
    #  Source-of-truth helpers — used by Beena, OG meta, SEO, sitemap
    # ──────────────────────────────────────────────────────────────────

    def get_description_html(self, lang=None):
        """Return the rich HTML description for the requested language.

        Resolution order:
          1. website_description_ar  (if lang starts with 'ar')
          2. website_description_en  (if lang starts with 'en' or unspecified)
          3. The other custom field (fallback)
          4. Standard website_description (Odoo default field)
          5. description_sale (sales note)
          6. description (internal note) — last resort
        """
        self.ensure_one()
        lang = (lang or self.env.context.get('lang') or 'en').lower()
        prefer_ar = lang.startswith('ar')
        candidates = (
            [self.website_description_ar, self.website_description_en]
            if prefer_ar
            else [self.website_description_en, self.website_description_ar]
        )
        for c in candidates:
            if c and (c or '').strip():
                return c
        # Fallbacks — these are NOT bilingual but better than nothing
        for c in (self.website_description, self.description_sale, self.description):
            if c and (c or '').strip():
                return c
        return ''

    def get_description_plain(self, lang=None, max_chars=0):
        """Return the description as plain text. Used by Beena's system prompt,
        Open Graph meta, JSON-LD, sitemap, etc.

        Args:
            lang:      'ar' / 'en' / None (use context)
            max_chars: truncate to this many chars (0 = full)
        """
        html = self.get_description_html(lang=lang) or ''
        # Strip HTML tags + collapse whitespace
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text).strip()
        if max_chars and len(text) > max_chars:
            text = text[:max_chars].rstrip() + '…'
        return text

    def get_description_bullets(self, lang=None, max_items=8):
        """Extract bullet points from the description HTML.
        Returns a list of plain-text strings. If the description has no <li>
        elements, returns the first N non-empty paragraphs/lines."""
        html = self.get_description_html(lang=lang) or ''
        # Try real <li> first
        lis = re.findall(r'<li[^>]*>(.*?)</li>', html, flags=re.IGNORECASE | re.DOTALL)
        if lis:
            cleaned = [re.sub(r'<[^>]+>', ' ', x) for x in lis]
            cleaned = [re.sub(r'\s+', ' ', x).strip() for x in cleaned]
            return [x for x in cleaned if x][:max_items]
        # Fall back to splitting on <br> / </p>
        chunks = re.split(r'</?(?:p|br|div)[^>]*>', html, flags=re.IGNORECASE)
        cleaned = [re.sub(r'<[^>]+>', ' ', x) for x in chunks]
        cleaned = [re.sub(r'\s+', ' ', x).strip() for x in cleaned]
        return [x for x in cleaned if len(x) > 8][:max_items]

    def get_specifications(self):
        """Build a structured list of product specifications from the
        attribute lines + key catalog fields. Used by the Specifications
        tab and the Beena product card."""
        self.ensure_one()
        rows = []
        # 1. Attribute lines (color, size, material, etc.)
        for line in self.valid_product_template_attribute_line_ids:
            values = [v.name for v in line.value_ids if v.name]
            if not values:
                continue
            rows.append({
                'group': line.attribute_id.name or '',
                'label': line.attribute_id.name or '',
                'value': ' · '.join(values),
                'icon':  self._spec_icon_for(line.attribute_id.name or ''),
                'source': 'attribute',
            })
        # 2. Key catalog facts — only when actually set
        if self.default_code:
            rows.append({'group': 'Catalog', 'label': 'SKU',
                         'value': self.default_code, 'icon': '🔖', 'source': 'catalog'})
        if self.barcode:
            rows.append({'group': 'Catalog', 'label': 'Barcode',
                         'value': self.barcode, 'icon': '📊', 'source': 'catalog'})
        if self.weight:
            rows.append({'group': 'Logistics', 'label': 'Weight',
                         'value': f'{self.weight:g} kg', 'icon': '⚖', 'source': 'logistics'})
        if self.volume:
            rows.append({'group': 'Logistics', 'label': 'Volume',
                         'value': f'{self.volume:g} m³', 'icon': '📦', 'source': 'logistics'})
        return rows

    @staticmethod
    def _spec_icon_for(attr_name):
        """Map common attribute names to icons for the spec rows."""
        n = (attr_name or '').lower()
        if any(k in n for k in ('color', 'colour', 'لون')):  return '🎨'
        if any(k in n for k in ('size', 'مقاس', 'حجم')):     return '📏'
        if any(k in n for k in ('material', 'مادة', 'خامة')): return '🧵'
        if any(k in n for k in ('weight', 'وزن')):             return '⚖'
        if any(k in n for k in ('capacity', 'سعة')):           return '🔋'
        if any(k in n for k in ('warranty', 'ضمان')):          return '🛡'
        if any(k in n for k in ('brand', 'ماركة', 'علامة')):  return '🏷'
        return '•'
