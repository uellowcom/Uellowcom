from odoo import models, fields, api, _


class FraudRule(models.Model):
    """Configurable fraud detection rules."""
    _name = 'uellow.fraud.rule'
    _description = 'Fraud Detection Rule'
    _rec_name = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    rule_type = fields.Selection([
        ('cod_cancel_rate',    'COD Cancellation Rate'),
        ('same_address_names', 'Same Address Multiple Names'),
        ('rapid_orders',       'Rapid Orders Same IP'),
        ('high_value_guest',   'High Value Guest Order'),
        ('multiple_accounts',  'Multiple Accounts Same Phone'),
    ], required=True, string='Rule Type')

    threshold = fields.Float('Threshold', required=True)
    window_days = fields.Integer('Check Window (days)', default=30)

    action = fields.Selection([
        ('flag',     'Flag for Review'),
        ('hold',     'Hold Order'),
        ('block',    'Block Customer'),
        ('cancel',   'Cancel Order'),
    ], default='flag', required=True)

    score_weight = fields.Integer('Risk Score Weight', default=10)
    description = fields.Text('Description')

    trigger_count = fields.Integer('Times Triggered', default=0, readonly=True)
