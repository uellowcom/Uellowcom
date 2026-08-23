# -*- coding: utf-8 -*-
# Phase 2 search: a stored, GIN-trigram-indexed NORMALIZED text field so Arabic
# variants (ة/ه · أ/إ/آ/ا · ى/ي) match, and pg_trgm gives typo tolerance.
import re
from odoo import api, fields, models

_AR_DIAC = re.compile('[ً-ْٰـ]')  # tashkeel + superscript alef + tatweel


def _norm_full(s):
    s = (s or '').strip().lower()
    s = _AR_DIAC.sub('', s)
    s = re.sub(r'\s+', ' ', s)
    for a, b in (('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ة', 'ه'),
                 ('ى', 'ي'), ('ؤ', 'و'), ('ئ', 'ي')):
        s = s.replace(a, b)
    return s


class ProductTemplateSearchIndex(models.Model):
    _inherit = 'product.template'

    x_search_norm = fields.Char(
        string='Normalized search text',
        compute='_compute_x_search_norm', store=True, index=False)

    @api.depends('name', 'default_code', 'brand_id.name',
                 'public_categ_ids.name', 'product_tag_ids.name')
    def _compute_x_search_norm(self):
        name_map = {}
        if self.ids:
            try:
                self.env.cr.execute(
                    "SELECT id, name FROM product_template WHERE id IN %s",
                    (tuple(self.ids),))
                name_map = dict(self.env.cr.fetchall())
            except Exception:
                name_map = {}
        for r in self:
            _raw = name_map.get(r.id)
            if isinstance(_raw, dict):
                _names = ' '.join(str(v) for v in _raw.values() if v)
            elif _raw is not None:
                _names = str(_raw)
            else:
                _names = r.name or ''
            parts = [_names, r.default_code or '']
            try:
                if r.brand_id:
                    parts.append(r.brand_id.name or '')
            except Exception:
                pass
            try:
                parts.append(' '.join(r.public_categ_ids.mapped('name')))
            except Exception:
                pass
            try:
                parts.append(' '.join(r.product_tag_ids.mapped('name')))
            except Exception:
                pass
            r.x_search_norm = _norm_full(' '.join(p for p in parts if p))[:512]

    def init(self):
        try:
            self.env.cr.execute(
                "SELECT 1 FROM pg_indexes WHERE indexname = "
                "'product_template_x_search_norm_trgm'")
            if not self.env.cr.fetchone():
                self.env.cr.execute(
                    "CREATE INDEX product_template_x_search_norm_trgm "
                    "ON product_template USING gin (x_search_norm gin_trgm_ops)")
        except Exception:
            pass
