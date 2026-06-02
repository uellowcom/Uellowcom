# -*- coding: utf-8 -*-
from odoo import fields, models


class SEOAuditIssue(models.Model):
    _name = 'uellow.seo.audit.issue'
    _description = 'SEO Audit Finding'
    _order = 'severity, audit_id desc'

    audit_id = fields.Many2one('uellow.seo.audit', ondelete='cascade', required=True)
    severity = fields.Selection([
        ('critical', '🔴 Critical'),
        ('warning',  '🟡 Warning'),
        ('info',     '🔵 Info'),
    ], required=True)
    code = fields.Char(string='Check', required=True,
        help='Machine-readable check id, e.g. meta_title_missing')
    message = fields.Char(required=True)
    res_model = fields.Char()
    res_id = fields.Integer()
    record_name = fields.Char(string='On')

    def action_open_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
