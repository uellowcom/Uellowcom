# -*- coding: utf-8 -*-
import json
from markupsafe import Markup
from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _seo_is_ar(self):
        return not (self.env.context.get('lang') or self.env.lang or '').lower().startswith('en')

    def _seo_heading(self):
        return 'الأسئلة الشائعة' if self._seo_is_ar() else 'Frequently asked questions'

    def _seo_faqs(self):
        """Product-specific FAQ built from the product's own data."""
        self.ensure_one()
        ar = self._seo_is_ar()
        name = (self.name or '').strip()
        cur = self.currency_id.symbol or 'KD'
        price = '%.3f %s' % (self.list_price or 0.0, cur)
        if ar:
            return [
                ('كم سعر %s في الكويت؟' % name,
                 'سعر %s في Uellow هو %s. تابع صفحة المنتج لأحدث الأسعار والعروض.' % (name, price)),
                ('هل يمكن شراء %s بالتقسيط؟' % name,
                 'نعم، يمكنك شراء %s بالتقسيط على 4 دفعات أو عبر Taly و Ci-Net على المنتجات المؤهلة.' % name),
                ('هل %s أصلي وعليه ضمان؟' % name,
                 'نعم، %s أصلي 100%% مع ضمان، وإرجاع سهل خلال 14 يومًا.' % name),
                ('هل يمكن الدفع عند استلام %s؟' % name,
                 'نعم، ادفع نقدًا عند الاستلام أو إلكترونيًا بأمان، مع توصيل سريع لكل مناطق الكويت.'),
            ]
        return [
            ('How much does %s cost in Kuwait?' % name,
             'The price of %s at Uellow is %s. Check the product page for the latest price and offers.' % (name, price)),
            ('Can I buy %s on installments?' % name,
             'Yes, you can buy %s in 4 instalments or via Taly and Ci-Net on eligible products.' % name),
            ('Is %s genuine and under warranty?' % name,
             'Yes, %s is 100%% genuine with warranty and easy 14-day returns.' % name),
            ('Is cash on delivery available for %s?' % name,
             'Yes, pay cash on delivery or securely online, with fast delivery across Kuwait.'),
        ]

    def _seo_faq_jsonld(self):
        """Standalone FAQPage JSON-LD (no Product duplication)."""
        self.ensure_one()
        faqs = self._seo_faqs()
        data = {
            '@context': 'https://schema.org', '@type': 'FAQPage',
            'mainEntity': [{'@type': 'Question', 'name': q,
                            'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in faqs],
        }
        return Markup(json.dumps(data, ensure_ascii=False).replace('<', '\\u003c'))
