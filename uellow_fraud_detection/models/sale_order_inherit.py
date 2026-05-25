from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fraud_risk_score = fields.Integer('Fraud Risk Score', default=0)
    fraud_flagged = fields.Boolean('Fraud Flagged', default=False)
    fraud_case_id = fields.Many2one(
        'uellow.fraud.case', string='Fraud Case', ondelete='set null',
    )
