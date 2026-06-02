# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SEOBulkWizard(models.TransientModel):
    _name = 'uellow.seo.bulk.wizard'
    _description = 'Bulk Auto-Fill Missing SEO Meta'

    batch_size = fields.Integer(default=200, required=True,
        help='How many products to process per click.')
    last_count = fields.Integer(readonly=True,
        help='Number of records filled on the last run.')

    def action_run_bulk(self):
        self.ensure_one()
        n = self.env['product.template'].action_seo_autofill_missing_bulk(
            batch=self.batch_size)
        self.last_count = n
        # Re-open the wizard so the user can fire again
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bulk SEO Auto-Fill'),
            'res_model': 'uellow.seo.bulk.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
