# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductPublicCategory(models.Model):
    _inherit = 'product.public.category'

    # Per-category hero colors (optional override). Empty → a distinct default
    # gradient is picked automatically from the palette (see website._ucp_hero_style).
    ucp_hero_c1 = fields.Char('Hero color 1', help='Hex like #11182B. Leave empty for the auto default.')
    ucp_hero_c2 = fields.Char('Hero color 2', help='Hex like #3A2F8F. Leave empty for the auto default.')
    ucp_hero_c3 = fields.Char('Hero color 3 (optional)', help='Optional 3rd gradient stop, e.g. #EC4899.')
