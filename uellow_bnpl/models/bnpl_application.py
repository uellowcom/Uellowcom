from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta


class BNPLApplication(models.Model):
    _name = 'uellow.bnpl.application'
    _description = 'BNPL Application'
    _inherit = ['mail.thread']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(readonly=True, default='New')
    order_id = fields.Many2one('sale.order', required=True, ondelete='restrict', index=True)
    partner_id = fields.Many2one(related='order_id.partner_id', store=True)
    plan_id = fields.Many2one('uellow.bnpl.plan', required=True)

    total_amount = fields.Float('Total Amount', readonly=True)
    installment_amount = fields.Float('Per Installment (KD)', readonly=True, compute='_compute_installment', store=True)
    admin_fee = fields.Float('Admin Fee (KD)', readonly=True)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', store=True)

    state = fields.Selection([
        ('pending',   'Pending'),
        ('approved',  'Approved'),
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('defaulted', 'Defaulted'),
        ('cancelled', 'Cancelled'),
    ], default='pending', tracking=True)

    installment_line_ids = fields.One2many(
        'uellow.bnpl.installment', 'application_id', string='Installments',
    )
    paid_count = fields.Integer(compute='_compute_paid', string='Paid', store=True)
    remaining_amount = fields.Float(compute='_compute_paid', string='Remaining', store=True)

    @api.depends('plan_id', 'total_amount')
    def _compute_installment(self):
        for rec in self:
            if rec.plan_id and rec.plan_id.installments and rec.total_amount:
                rec.installment_amount = rec.total_amount / rec.plan_id.installments
            else:
                rec.installment_amount = 0.0

    @api.depends('installment_line_ids.state')
    def _compute_paid(self):
        for rec in self:
            paid = rec.installment_line_ids.filtered(lambda l: l.state == 'paid')
            rec.paid_count = len(paid)
            rec.remaining_amount = rec.total_amount - sum(paid.mapped('amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('uellow.bnpl') or 'New'
        return super().create(vals_list)

    def action_approve(self):
        self.state = 'approved'
        self._create_installment_schedule()

    def _create_installment_schedule(self):
        plan = self.plan_id
        base_date = fields.Date.today()
        amount = self.installment_amount
        for i in range(plan.installments):
            due_date = base_date + timedelta(days=plan.interval_days * i)
            self.env['uellow.bnpl.installment'].create({
                'application_id': self.id,
                'installment_no': i + 1,
                'amount': amount,
                'due_date': due_date,
            })
        self.state = 'active'

    def action_cancel(self):
        self.state = 'cancelled'


class BNPLInstallment(models.Model):
    _name = 'uellow.bnpl.installment'
    _description = 'BNPL Installment Line'
    _order = 'installment_no'

    application_id = fields.Many2one('uellow.bnpl.application', ondelete='cascade')
    installment_no = fields.Integer('#')
    amount = fields.Float('Amount (KD)')
    due_date = fields.Date('Due Date')
    paid_date = fields.Date('Paid Date')
    state = fields.Selection([
        ('due', 'Due'), ('paid', 'Paid'), ('overdue', 'Overdue'),
    ], default='due')
    late_fee = fields.Float('Late Fee', default=0.0)

    def action_mark_paid(self):
        self.write({'state': 'paid', 'paid_date': fields.Date.today()})
        app = self.application_id
        if all(l.state == 'paid' for l in app.installment_line_ids):
            app.state = 'completed'
