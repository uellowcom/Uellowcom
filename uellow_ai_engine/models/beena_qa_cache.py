# -*- coding: utf-8 -*-
"""Beena Answer Cache: store normalized Q&A pairs to answer repeats without Claude."""

import re
from odoo import models, fields, api


class BeenaQaCache(models.Model):
    _name = 'beena.qa.cache'
    _description = 'Beena Answer Cache'
    _order = 'hit_count desc, write_date desc'
    _rec_name = 'question'

    question = fields.Char(string='Question', required=True, index=True)
    question_norm = fields.Char(string='Normalized', index=True)
    answer = fields.Text(string='Answer', required=True)

    product_id = fields.Many2one('product.template', string='Product Context', ondelete='cascade')
    lang = fields.Char(string='Language', default='ar')

    hit_count = fields.Integer(string='Times Used', default=0)
    approved = fields.Boolean(string='Approved', default=True)

    saved_cost = fields.Float(string='Estimated Saved Cost (USD)', default=0.0, digits=(12, 6))

    @api.model
    def normalize(self, text):
        if not text:
            return ''
        t = text.strip().lower()
        t = re.sub(r'[\u0617-\u061A\u064B-\u0652]', '', t)
        t = t.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا')
        t = re.sub(r'[^\w\u0600-\u06FF\s]', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    _DEFAULT_GENERIC_KEYWORDS = (
        'توصيل,التوصيل,شحن,الشحن,عنوان,عنوانكم,فرع,فروع,'
        'دفع,الدفع,ارجاع,إرجاع,استبدال,ضمان,الضمان,'
        'كاش,تقسيط,ساعات,دوام,تواصل,رقم,'
        'delivery,shipping,address,branch,payment,return,'
        'refund,warranty,installment,contact,hours'
    )

    @api.model
    def _generic_keywords(self):
        """Merge default keywords with any extra keywords from settings."""
        extra = self.env['ir.config_parameter'].sudo().get_param(
            'uellow_ai.generic_keywords', ''
        )
        combined = self._DEFAULT_GENERIC_KEYWORDS + ',' + (extra or '')
        kws = []
        for kw in combined.replace('\n', ',').split(','):
            kw = self.normalize(kw)
            if kw and kw not in kws:
                kws.append(kw)
        return kws

    @api.model
    def is_generic(self, question):
        norm = self.normalize(question)
        if not norm:
            return False
        return any(kw in norm for kw in self._generic_keywords())

    @api.model
    def lookup(self, question, product_id=None, lang=None):
        norm = self.normalize(question)
        if not norm:
            return None
        # Generic questions are matched store-wide, ignoring product context
        if self.is_generic(question):
            domain = [('question_norm', '=', norm), ('approved', '=', True),
                      ('product_id', '=', False)]
            return self.search(domain, limit=1) or None
        domain = [('question_norm', '=', norm), ('approved', '=', True)]
        if product_id:
            domain.append(('product_id', '=', int(product_id)))
        else:
            domain.append(('product_id', '=', False))
        return self.search(domain, limit=1) or None

    @api.model
    def store(self, question, answer, product_id=None, lang=None, saved_cost=0.0):
        norm = self.normalize(question)
        if not norm or not answer:
            return None
        if self.is_generic(question):
            product_id = False
        existing = self.lookup(question, product_id, lang)
        if existing:
            return existing
        import re as _re
        _clean = lambda t: _re.sub(r'<[^>]+>', '', t or '').strip()
        return self.create({
            'question': _clean(question)[:255],
            'question_norm': norm,
            'answer': _clean(answer),
            'product_id': int(product_id) if product_id else False,
            'lang': lang or 'ar',
            'approved': True,
            'saved_cost': saved_cost,
        })

    def register_hit(self, saved_cost=0.0):
        for rec in self:
            rec.hit_count += 1
            rec.saved_cost += saved_cost
