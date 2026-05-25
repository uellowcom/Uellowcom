from odoo import models, fields, api, _


class VendorApproveWizard(models.TransientModel):
    _name = 'uellow.vendor.approve.wizard'
    _description = 'Approve Vendor'

    vendor_id = fields.Many2one('uellow.vendor', required=True)
    plan_id = fields.Many2one('uellow.commission.plan', string='Assign Plan', required=True)
    admin_note = fields.Text('Note to Vendor')
    confirmed_date = fields.Date('Approval Date', default=fields.Date.today)

    def action_approve(self):
        self.ensure_one()
        self.vendor_id.plan_id = self.plan_id
        self.vendor_id.action_approve()
        if self.admin_note:
            self.vendor_id.message_post(body=self.admin_note)
        return {'type': 'ir.actions.act_window_close'}


class VendorRejectWizard(models.TransientModel):
    _name = 'uellow.vendor.reject.wizard'
    _description = 'Reject Vendor'

    vendor_id = fields.Many2one('uellow.vendor', required=True)
    reason = fields.Selection([
        ('incomplete_docs',  'Incomplete Documents'),
        ('ineligible',       'Does Not Meet Criteria'),
        ('duplicate',        'Duplicate Account'),
        ('other',            'Other'),
    ], required=True, string='Reason')
    note = fields.Text('Details')

    def action_reject(self):
        self.ensure_one()
        self.vendor_id.write({
            'state': 'rejected',
            'rejection_reason': f'{dict(self._fields["reason"].selection)[self.reason]}: {self.note or ""}',
        })
        self.vendor_id.message_post(
            body=_('Application rejected. Reason: %s') % self.note or '')
        return {'type': 'ir.actions.act_window_close'}
