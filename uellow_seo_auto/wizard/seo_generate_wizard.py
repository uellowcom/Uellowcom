"""Bulk AI generation wizard (F8).

Manager selects a set of products → wizard generates SEO meta for them
synchronously in chunks, committing per chunk so progress survives
errors. For very large batches the wizard reports back with a summary.
"""
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SEOGenerateWizard(models.TransientModel):
    _name = 'uellow.seo.generate.wizard'
    _description = 'Bulk SEO Generation'

    scope = fields.Selection([
        ('selected',     'Selected products'),
        ('missing',      'All products missing SEO'),
        ('needs_update', 'All flagged "needs update"'),
        ('low_score',    'All with score < threshold'),
        ('all',          'All published products'),
    ], default='selected', required=True)

    product_ids = fields.Many2many('product.template', string='Products')
    score_threshold = fields.Integer('Score threshold', default=50)
    batch_size = fields.Integer('Batch size', default=20)
    overwrite = fields.Boolean('Overwrite existing', default=True)

    # Result counters (populated after action_run)
    last_run_done = fields.Integer(readonly=True)
    last_run_failed = fields.Integer(readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        if ctx.get('active_model') == 'product.template' and ctx.get('active_ids'):
            res['scope'] = 'selected'
            res['product_ids'] = [(6, 0, ctx['active_ids'])]
        return res

    def _scoped_products(self):
        """Resolve the scope → product.template recordset."""
        self.ensure_one()
        ProductT = self.env['product.template']
        SP = self.env['uellow.seo.product']
        if self.scope == 'selected':
            return self.product_ids
        if self.scope == 'missing':
            self.env.cr.execute(
                'SELECT id FROM product_template '
                'WHERE website_published = TRUE '
                'AND id NOT IN (SELECT product_id FROM uellow_seo_product)'
            )
            return ProductT.browse([row[0] for row in self.env.cr.fetchall()])
        if self.scope == 'needs_update':
            seo = SP.search([('needs_update', '=', True)])
            return seo.mapped('product_id')
        if self.scope == 'low_score':
            seo = SP.search([('score', '<', self.score_threshold or 50)])
            return seo.mapped('product_id')
        if self.scope == 'all':
            return ProductT.search([('website_published', '=', True)])
        return ProductT

    def action_run(self):
        """Run synchronously, committing per batch."""
        self.ensure_one()
        products = self._scoped_products()
        if not products:
            raise UserError(_('No products matched the chosen scope.'))

        SP = self.env['uellow.seo.product']
        config = self.env['uellow.seo.config'].get_config()
        batch = max(1, self.batch_size or 20)
        done = failed = 0
        for i in range(0, len(products), batch):
            chunk = products[i:i + batch]
            for product in chunk:
                # Skip if record exists and we're not overwriting
                if not self.overwrite:
                    if SP.search_count([('product_id', '=', product.id)]):
                        continue
                try:
                    SP._generate_for_product(product, config)
                    done += 1
                except Exception as e:
                    failed += 1
                    _logger.warning('Wizard SEO failed for %s: %s', product.id, e)
            self.env.cr.commit()
            _logger.info('SEO bulk wizard progress: %d/%d (done=%d, failed=%d)',
                         min(i + batch, len(products)), len(products), done, failed)

        self.write({'last_run_done': done, 'last_run_failed': failed})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('SEO generation complete'),
                'message': _('Generated: %d · Failed: %d') % (done, failed),
                'type': 'success' if not failed else 'warning',
                'sticky': bool(failed),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
