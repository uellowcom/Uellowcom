# -*- coding: utf-8 -*-
from odoo import fields, models


class PaymentTalyLog(models.Model):
    _name = 'payment.taly.log'
    _description = 'Taly API Log'
    _order = 'create_date desc'
    _rec_name = 'action'

    provider_id = fields.Many2one(
        'payment.provider',
        string='Provider',
        ondelete='cascade',
    )
    action = fields.Char(string='Action / Endpoint', required=True)
    status = fields.Selection(
        selection=[
            ('success', 'Success'),
            ('error', 'Error'),
            ('warning', 'Warning'),
        ],
        string='Status',
        default='success',
    )
    message = fields.Text(string='Response / Message')
    payload = fields.Text(string='Request Payload')
    create_date = fields.Datetime(string='Date', readonly=True)
    color = fields.Integer(compute='_compute_color')

    def _compute_color(self):
        for rec in self:
            rec.color = 10 if rec.status == 'success' else (1 if rec.status == 'error' else 3)

    def action_clear_logs(self):
        """Delete all logs for the provider."""
        domain = [('provider_id', '=', self.env.context.get('active_id'))]
        self.search(domain).unlink()
        return {'type': 'ir.actions.act_window_close'}
