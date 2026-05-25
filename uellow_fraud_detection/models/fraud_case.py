from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class FraudCase(models.Model):
    """A detected fraud event — links to order and partner."""
    _name = 'uellow.fraud.case'
    _description = 'Fraud Case'
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(readonly=True, default='New')
    order_id = fields.Many2one('sale.order', ondelete='set null', index=True)
    partner_id = fields.Many2one('res.partner', ondelete='restrict', index=True)
    rule_id = fields.Many2one('uellow.fraud.rule', ondelete='set null')

    risk_score = fields.Integer('Risk Score', default=0)
    state = fields.Selection([
        ('open',       'Open'),
        ('reviewing',  'Under Review'),
        ('confirmed',  'Confirmed Fraud'),
        ('false_pos',  'False Positive'),
        ('resolved',   'Resolved'),
    ], default='open', string='Status', index=True)

    details = fields.Text('Details')
    admin_note = fields.Text('Admin Note')
    resolved_by = fields.Many2one('res.users', ondelete='set null')
    resolved_at = fields.Datetime('Resolved At')

    is_blocked = fields.Boolean('Partner Blocked', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code(
                    'uellow.fraud.case') or 'New'
        return super().create(vals_list)

    def action_confirm_fraud(self):
        for case in self:
            case.state = 'confirmed'
            if case.partner_id and case.risk_score >= 50:
                case.partner_id.write({'active': False})
                case.is_blocked = True

    def action_false_positive(self):
        self.write({'state': 'false_pos'})

    def action_resolve(self):
        self.write({
            'state': 'resolved',
            'resolved_by': self.env.user.id,
            'resolved_at': fields.Datetime.now(),
        })

    @api.model
    def cron_scan_orders(self):
        """Daily cron: scan recent orders for fraud signals."""
        from datetime import timedelta
        rules = self.env['uellow.fraud.rule'].search([('active', '=', True)])
        for rule in rules:
            self._apply_rule(rule)

    def _apply_rule(self, rule):
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(days=rule.window_days)

        if rule.rule_type == 'cod_cancel_rate':
            # Partners with high COD cancellation rate
            cancelled = self.env['sale.order'].read_group(
                [('state', '=', 'cancel'),
                 ('date_order', '>=', cutoff)],
                ['partner_id'],
                ['partner_id'],
            )
            for rec in cancelled:
                partner_id = rec['partner_id'][0] if rec['partner_id'] else False
                if not partner_id:
                    continue
                total = self.env['sale.order'].search_count([
                    ('partner_id', '=', partner_id),
                    ('date_order', '>=', cutoff),
                ])
                if total == 0:
                    continue
                rate = rec['partner_id_count'] / total * 100
                if rate >= rule.threshold:
                    self._create_case_if_new(
                        partner_id=partner_id,
                        rule=rule,
                        score=int(rate),
                        details=f'COD cancel rate: {rate:.1f}% ({rec["partner_id_count"]}/{total} orders)',
                    )
            rule.trigger_count += 1

    def _create_case_if_new(self, partner_id, rule, score, details, order_id=False):
        existing = self.search([
            ('partner_id', '=', partner_id),
            ('rule_id', '=', rule.id),
            ('state', 'in', ('open', 'reviewing')),
        ], limit=1)
        if not existing:
            self.create({
                'partner_id': partner_id,
                'rule_id': rule.id,
                'order_id': order_id or False,
                'risk_score': score,
                'details': details,
            })
