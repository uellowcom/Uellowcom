from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ImportReviewWizard(models.TransientModel):
    """
    Wizard for bulk approval/rejection of import job lines.
    Opens from the import job form view.
    """
    _name = 'uellow.import.review.wizard'
    _description = 'مراجعة نتائج الاستيراد'

    job_id = fields.Many2one('uellow.import.job', required=True, ondelete='cascade')
    job_name = fields.Char(related='job_id.name', readonly=True)

    filter_type = fields.Selection([
        ('all',      'الكل'),
        ('warnings', 'التحذيرات فقط'),
        ('new',      'المنتجات الجديدة فقط'),
        ('updates',  'التحديثات فقط'),
    ], default='all', string='عرض')

    approve_all = fields.Boolean('اعتماد الكل تلقائياً')
    reject_warnings = fields.Boolean('رفض التحذيرات تلقائياً')

    line_count = fields.Integer(compute='_compute_counts')
    warning_count = fields.Integer(compute='_compute_counts')
    new_count = fields.Integer(compute='_compute_counts')
    update_count = fields.Integer(compute='_compute_counts')

    @api.depends('job_id')
    def _compute_counts(self):
        for w in self:
            lines = w.job_id.line_ids
            w.line_count = len(lines)
            w.warning_count = len(lines.filtered('has_warning'))
            w.new_count = len(lines.filtered(lambda l: l.product_action == 'new'))
            w.update_count = len(lines.filtered(lambda l: l.product_action == 'update'))

    def action_apply_review(self):
        """Apply review decisions and push approved lines to catalog."""
        self.ensure_one()
        job = self.job_id
        lines = job.line_ids.filtered(lambda l: l.line_state == 'pending')

        if self.reject_warnings:
            lines.filtered('has_warning').write({'line_state': 'rejected'})
            lines = lines.filtered(lambda l: l.line_state == 'pending')

        if self.approve_all:
            lines.write({'line_state': 'approved'})

        # Apply all approved lines
        approved = job.line_ids.filtered(lambda l: l.line_state == 'approved')
        applied = 0
        for line in approved:
            try:
                line.action_apply()
                applied += 1
            except Exception:
                pass

        job.state = 'done'
        job.imported_product_ids = [(6, 0, [
            l.applied_product_id.id
            for l in job.line_ids
            if l.applied_product_id
        ])]
        job.message_post(body=_(
            'تم التطبيق: %d منتج · مرفوض: %d سطر.') % (
            applied,
            len(job.line_ids.filtered(lambda l: l.line_state == 'rejected')),
        ))
        return {'type': 'ir.actions.act_window_close'}

    def action_open_lines(self):
        """Open line list for manual review."""
        return {
            'type': 'ir.actions.act_window',
            'name': f'سطور — {self.job_id.name}',
            'res_model': 'uellow.import.job.line',
            'view_mode': 'list,form',
            'domain': [('job_id', '=', self.job_id.id)],
        }
