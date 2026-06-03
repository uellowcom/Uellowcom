from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    upayments_enabled = fields.Boolean(
        string='Enable UPayments',
        config_parameter='uellow_upayments.enabled')
    upayments_token = fields.Char(
        string='UPayments API token (Bearer)',
        config_parameter='uellow_upayments.token',
        help='Sandbox test token is "jtest123". Production token from UPayments.')
    upayments_base_url = fields.Char(
        string='UPayments API base URL',
        config_parameter='uellow_upayments.base_url',
        help='Sandbox: https://sandboxapi.upayments.com/api/v1  ·  '
             'Production: get from UPayments support.')
