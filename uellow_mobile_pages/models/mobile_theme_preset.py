# -*- coding: utf-8 -*-
from odoo import fields, models


class MobileThemePreset(models.Model):
    _name = 'mobile.theme.preset'
    _description = 'Mobile page theme preset'
    _order = 'sequence, id'

    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    primary = fields.Char(string='Primary color',  default='#F5C320')
    dark = fields.Char(string='Dark color',     default='#412402')
    page_bg = fields.Char(string='Page background', default='#FAF6EB')
    hero_bg = fields.Char(string='Hero gradient (CSS)',
                          default='linear-gradient(135deg,#412402 0%,#6b3a05 60%,#F5C320 100%)')
    accent = fields.Char(default='#1F8A40')
    text_color = fields.Char(default='#1F1206')
    muted_color = fields.Char(default='#7A6850')
    extras_json = fields.Text(default='{}',
        help='JSON: extra tokens e.g. {"lanterns":true,"confetti":true}')
    icon = fields.Char(help='Emoji shown next to the preset name')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Theme code must be unique'),
    ]

    def to_dict(self):
        import json
        self.ensure_one()
        try:
            extras = json.loads(self.extras_json or '{}')
        except Exception:
            extras = {}
        return {
            'id': self.code,
            'name': (self.icon and (self.icon + ' ') or '') + self.name,
            'primary': self.primary,
            'dark': self.dark,
            'page_bg': self.page_bg,
            'hero_bg': self.hero_bg,
            'accent': self.accent,
            'text_color': self.text_color,
            'muted_color': self.muted_color,
            **extras,
        }
