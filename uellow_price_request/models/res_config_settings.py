# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    prr_allow_apply = fields.Boolean(
        string="Allow applying supplier prices",
        config_parameter='uellow_price_request.allow_apply', default=True,
        help="When on, the 'Apply New Prices' button writes the supplier's "
             "returned prices back onto the catalogue.")
    prr_default_note = fields.Text(
        string="Default supplier instructions",
        config_parameter='uellow_price_request.default_note',
        help="Pre-filled note printed on every price-update request.")
