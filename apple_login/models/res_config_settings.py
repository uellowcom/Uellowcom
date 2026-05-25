# -*- coding: utf-8 -*-
from odoo import fields, models, api


class AppleLoginConfig(models.Model):
    _name = 'apple.login.config'
    _description = 'Sign in with Apple Configuration'

    name = fields.Char(default='Apple Login Config')
    enabled = fields.Boolean(string='Enable Sign in with Apple')
    client_id = fields.Char(string='Client ID (Service ID)')
    team_id = fields.Char(string='Team ID')
    key_id = fields.Char(string='Key ID')
    private_key = fields.Text(string='Private Key (.p8)')

    def write(self, vals):
        res = super().write(vals)
        # Sync to ir.config_parameter on every save
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('apple_login.enabled', str(self.enabled))
        ICP.set_param('apple_login.client_id', self.client_id or '')
        ICP.set_param('apple_login.team_id', self.team_id or '')
        ICP.set_param('apple_login.key_id', self.key_id or '')
        ICP.set_param('apple_login.private_key', self.private_key or '')
        return res

    def action_save(self):
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('apple_login.enabled', str(self.enabled))
        ICP.set_param('apple_login.client_id', self.client_id or '')
        ICP.set_param('apple_login.team_id', self.team_id or '')
        ICP.set_param('apple_login.key_id', self.key_id or '')
        ICP.set_param('apple_login.private_key', self.private_key or '')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Saved',
                'message': 'Apple Login settings saved successfully.',
                'type': 'success',
                'sticky': False,
            }
        }


class ResPartner(models.Model):
    _inherit = 'res.partner'

    apple_user_id = fields.Char(string='Apple User ID', index=True, copy=False)
