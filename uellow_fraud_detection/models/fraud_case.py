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

        elif rule.rule_type == 'multiple_accounts':
            # Same phone/mobile shared across many DISTINCT partner accounts.
            self.env.cr.execute("""
                SELECT regexp_replace(COALESCE(phone, mobile), '[^0-9]', '', 'g') AS ph,
                       array_agg(DISTINCT id) AS ids
                FROM res_partner
                WHERE COALESCE(phone, mobile) IS NOT NULL
                  AND length(regexp_replace(COALESCE(phone, mobile), '[^0-9]', '', 'g')) >= 8
                GROUP BY ph
                HAVING COUNT(DISTINCT id) >= %s
            """, (int(rule.threshold) or 2,))
            for ph, ids in self.env.cr.fetchall():
                for pid in ids:
                    self._create_case_if_new(
                        partner_id=pid, rule=rule, score=rule.score_weight,
                        details='Phone %s shared by %d accounts' % (ph, len(ids)))
            rule.trigger_count += 1

        elif rule.rule_type == 'same_address_names':
            # One shipping address used by many DISTINCT customer names.
            self.env.cr.execute("""
                SELECT lower(trim(rp.street)) AS st,
                       array_agg(DISTINCT so.partner_id) AS ids
                FROM sale_order so
                JOIN res_partner rp ON rp.id = so.partner_shipping_id
                WHERE so.date_order >= %s AND rp.street IS NOT NULL
                  AND length(trim(rp.street)) > 5
                GROUP BY st
                HAVING COUNT(DISTINCT so.partner_id) >= %s
            """, (cutoff, int(rule.threshold) or 3,))
            for st, ids in self.env.cr.fetchall():
                for pid in ids:
                    self._create_case_if_new(
                        partner_id=pid, rule=rule, score=rule.score_weight,
                        details='Shipping address shared by %d names' % len(ids))
            rule.trigger_count += 1

        elif rule.rule_type == 'high_value_guest':
            # High-value orders placed by portal/guest partners in the window.
            orders = self.env['sale.order'].search([
                ('date_order', '>=', cutoff),
                ('amount_total', '>=', rule.threshold),
                ('state', 'in', ('draft', 'sent', 'sale')),
            ])
            for o in orders:
                users = o.partner_id.user_ids
                is_guest = (not users) or all(
                    u.has_group('base.group_portal') for u in users)
                if is_guest:
                    self._create_case_if_new(
                        partner_id=o.partner_id.id, rule=rule,
                        score=rule.score_weight,
                        details='High-value guest order %s: %.2f'
                                % (o.name, o.amount_total),
                        order_id=o.id)
            rule.trigger_count += 1

        elif rule.rule_type == 'rapid_orders':
            # No client IP is tracked on sale.order, so this flags many orders
            # from the SAME partner within the window (a rapid-ordering signal).
            grp = self.env['sale.order'].read_group(
                [('date_order', '>=', cutoff)], ['partner_id'], ['partner_id'])
            for rec in grp:
                pid = rec['partner_id'][0] if rec['partner_id'] else False
                cnt = rec['partner_id_count']
                if pid and cnt >= (int(rule.threshold) or 5):
                    self._create_case_if_new(
                        partner_id=pid, rule=rule, score=rule.score_weight,
                        details='%d orders in %d days' % (cnt, rule.window_days))
            rule.trigger_count += 1

    def _create_case_if_new(self, partner_id, rule, score, details, order_id=False):
        existing = self.search([
            ('partner_id', '=', partner_id),
            ('rule_id', '=', rule.id),
            ('state', 'in', ('open', 'reviewing')),
        ], limit=1)
        if not existing:
            case = self.create({
                'partner_id': partner_id,
                'rule_id': rule.id,
                'order_id': order_id or False,
                'risk_score': score,
                'details': details,
            })
            # Reflect the risk on the customer's affected order(s) for review
            # visibility. These flags are INFORMATIONAL — no order is auto-held
            # or cancelled here.
            SO = self.env['sale.order']
            orders = SO.browse(order_id) if order_id else SO.search([
                ('partner_id', '=', partner_id),
                ('state', 'in', ('draft', 'sent', 'sale')),
            ], limit=20)
            orders = orders.exists()
            if orders:
                orders.write({
                    'fraud_flagged': True,
                    'fraud_risk_score': score,
                    'fraud_case_id': case.id,
                })
