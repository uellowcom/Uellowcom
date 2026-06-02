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
        """Apply review decisions and push approved lines to catalog.

        Bugfixes vs. prior version:
          - D2: `filter_type` is now honoured — was defined but ignored.
          - A8: per-line apply errors are collected and surfaced via chatter
            instead of silently swallowed with `try/except: pass`. The job
            stays in `review` (not flipped to `done`) if any apply failed,
            so the manager can retry.
        """
        self.ensure_one()
        job = self.job_id
        pending = job.line_ids.filtered(lambda l: l.line_state == 'pending')

        # D2: scope by filter_type
        if self.filter_type == 'warnings':
            scope = pending.filtered('has_warning')
        elif self.filter_type == 'new':
            scope = pending.filtered(lambda l: l.product_action == 'new')
        elif self.filter_type == 'updates':
            scope = pending.filtered(lambda l: l.product_action == 'update')
        else:
            scope = pending

        if self.reject_warnings:
            scope.filtered('has_warning').write({'line_state': 'rejected'})
            scope = scope.filtered(lambda l: l.line_state == 'pending')

        if self.approve_all:
            scope.write({'line_state': 'approved'})

        # Apply all approved lines — but collect failures.
        approved = job.line_ids.filtered(lambda l: l.line_state == 'approved')
        applied = 0
        failures = []
        for line in approved:
            try:
                line.action_apply()
                applied += 1
            except Exception as e:
                failures.append((line.name_en or str(line.id), str(e)[:160]))

        job.imported_product_ids = [(6, 0, [
            l.applied_product_id.id
            for l in job.line_ids
            if l.applied_product_id
        ])]

        rejected_count = len(job.line_ids.filtered(lambda l: l.line_state == 'rejected'))
        if failures:
            failure_lines = '\n'.join(
                '• %s — %s' % (name, err) for name, err in failures[:20]
            )
            job.message_post(body=_(
                'تم التطبيق: %d منتج · مرفوض: %d · فشل: %d.\n%s'
            ) % (applied, rejected_count, len(failures), failure_lines))
            # Keep job in review so the user can retry the failed lines.
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('تمت المعالجة مع وجود أخطاء'),
                    'message': _('تم تطبيق %d منتج، وفشل %d. راجع المحادثة للتفاصيل.')
                               % (applied, len(failures)),
                    'type': 'warning',
                    'sticky': True,
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        # All clean → mark done
        job.state = 'done'
        job.message_post(body=_(
            'تم التطبيق: %d منتج · مرفوض: %d سطر.') % (applied, rejected_count))
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
