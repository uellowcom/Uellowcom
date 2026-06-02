# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SEOAuditWizard(models.TransientModel):
    _name = 'uellow.seo.audit.wizard'
    _description = 'Run SEO Audit'

    scope_products   = fields.Boolean(default=True, string='Products')
    scope_categories = fields.Boolean(default=True, string='Categories')
    scope_pages      = fields.Boolean(default=True, string='Website pages')
    scope_limit      = fields.Integer(default=200,
        help='Cap on number of records per type. 0 = unlimited (slow).')

    def action_run(self):
        self.ensure_one()
        audit = self.env['uellow.seo.audit'].create({
            'name': _('Audit %s') % fields.Datetime.now(),
            'scope_products':  self.scope_products,
            'scope_categories':self.scope_categories,
            'scope_pages':     self.scope_pages,
            'scope_limit':     self.scope_limit,
        })
        audit.action_run()
        return {
            'type': 'ir.actions.act_window',
            'name': _('SEO Audit Result'),
            'res_model': 'uellow.seo.audit',
            'res_id': audit.id,
            'view_mode': 'form',
            'target': 'current',
        }
