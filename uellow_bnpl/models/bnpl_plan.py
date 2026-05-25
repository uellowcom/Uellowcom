from odoo import models, fields, api


class BNPLPlan(models.Model):
    _name = 'uellow.bnpl.plan'
    _description = 'BNPL Installment Plan'
    _rec_name = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    installments = fields.Integer('Number of Installments', required=True, default=4)
    interval_days = fields.Integer('Days Between Payments', default=30)
    min_order_amount = fields.Float('Minimum Order Amount (KD)', default=30.0)
    max_order_amount = fields.Float('Maximum Order Amount (KD)', default=500.0)
    admin_fee_pct = fields.Float('Admin Fee (%)', default=0.0)
    late_fee_kd = fields.Float('Late Payment Fee (KD)', default=2.0)
    requires_approval = fields.Boolean('Requires Manual Approval', default=False)
    currency_ids = fields.Many2many('res.currency', string='Eligible Currencies')
    country_ids = fields.Many2many('res.country', string='Eligible Countries')
    description = fields.Text('Plan Description')
