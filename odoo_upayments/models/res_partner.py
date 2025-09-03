from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    unique_token = fields.Char('Unique token')
