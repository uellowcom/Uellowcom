# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PpcConfigSettings(models.TransientModel):
    """
    Standalone settings wizard for Product Page Custom.
    Reads/writes values via ir.config_parameter directly.
    No inheritance from res.config.settings — avoids Odoo 18 xpath issues.
    """
    _name = "ppc.config.settings"
    _description = "Product Page Custom Settings"

    whatsapp_number = fields.Char(
        string="رقم الواتساب",
        help="رقم الواتساب مع كود الدولة، مثال: +201234567890",
        placeholder="+201234567890",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        param = self.env["ir.config_parameter"].sudo()
        res["whatsapp_number"] = param.get_param(
            "product_page_custom.whatsapp_number", default=""
        )
        return res

    def action_save(self):
        self.ensure_one()
        param = self.env["ir.config_parameter"].sudo()
        param.set_param(
            "product_page_custom.whatsapp_number",
            self.whatsapp_number or "",
        )
        return {"type": "ir.actions.act_window_close"}
