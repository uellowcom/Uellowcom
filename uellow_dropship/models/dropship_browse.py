# -*- coding: utf-8 -*-
"""Browse & Import — a backend screen to search AliExpress and import products.

The DS feed API can't free-text search the catalog, so this scans the promo
feeds and filters them by the admin's keyword/category/price/rating settings,
shows a live grid (nothing stored yet), and lets the admin Import or
Import & Publish per product or in bulk.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DropshipBrowseWizard(models.TransientModel):
    _name = 'dropship.browse.wizard'
    _description = 'Browse & Import from AliExpress'

    provider_ids = fields.Many2many(
        'dropship.provider', string="Providers",
        domain=[('active', '=', True), ('state', '=', 'connected')],
        help="Leave empty to use every connected provider.")
    keywords = fields.Char(
        string="Keywords", help="Comma-separated words to match in the title.")
    category_ids = fields.Many2many('dropship.category', string="Categories")
    min_price = fields.Float(string="Min Price (USD)")
    max_price = fields.Float(string="Max Price (USD)")
    min_orders = fields.Integer(string="Min Units Sold")
    min_rating = fields.Float(string="Min Rating (0-5)")
    max_results = fields.Integer(string="Max Results", default=40)
    line_ids = fields.One2many('dropship.browse.line', 'wizard_id', string="Results")
    searched = fields.Boolean(default=False)

    def _opts(self):
        self.ensure_one()

        def _split(v):
            return [x.strip() for x in (v or '').split(',') if x.strip()]

        cats = [c.ext_id or c.code or c.name for c in self.category_ids]
        return {
            'provider_ids': self.provider_ids.ids or None,
            'keywords': _split(self.keywords) or None,
            'categories': cats or None,
            'min_price': self.min_price or 0.0,
            'max_price': self.max_price or 0.0,
            'min_orders': self.min_orders or 0,
            'min_rating': self.min_rating or 0.0,
        }

    def action_search(self):
        self.ensure_one()
        self.line_ids.unlink()
        rows = self.env['dropship.import.service'].preview(
            self._opts(), limit=min(self.max_results or 40, 120))
        self.line_ids = [(0, 0, {
            'source_id': r['source_id'],
            'provider_id': r['provider_id'],
            'title': r['title'][:180],
            'image_url': r['image_url'],
            'price': r['price'],
            'currency': r['currency'],
            'orders_text': r['orders_text'],
            'rating': r['rating'],
            'category_name': r['category_name'],
            'imported': bool(r['existing_id']),
            'published': r['published'],
        }) for r in rows]
        self.searched = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'views': [[False, 'form']],
            'target': 'current',
        }

    def _do(self, lines, publish):
        ids = [l.source_id for l in lines if l.source_id]
        if not ids:
            raise UserError(_("Select at least one product first."))
        svc = self.env['dropship.import.service']
        svc.run_now({'source_ids': ids, 'skip_existing': False,
                     'enrich_on_import': True})
        DP = self.env['dropship.product'].sudo()
        recs = DP.search([('source_id', 'in', ids)])
        if publish and recs:
            recs.action_publish()
        # refresh line flags in place
        by_sid = {r.source_id: r for r in recs}
        for l in lines:
            r = by_sid.get(l.source_id)
            if r:
                l.imported = True
                l.published = bool(r.product_tmpl_id and r.product_tmpl_id.is_published)
        return len(recs)

    def action_import_selected(self):
        self.ensure_one()
        n = self._do(self.line_ids.filtered('selected'), publish=False)
        return self._reopen('%d product(s) imported.' % n)

    def action_publish_selected(self):
        self.ensure_one()
        n = self._do(self.line_ids.filtered('selected'), publish=True)
        return self._reopen('%d product(s) imported & published.' % n)

    def _reopen(self, msg):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name, 'res_id': self.id,
            'view_mode': 'form', 'views': [[False, 'form']],
            'target': 'current', 'context': dict(self.env.context, browse_msg=msg),
        }


class DropshipBrowseLine(models.TransientModel):
    _name = 'dropship.browse.line'
    _description = 'Browse & Import result'

    wizard_id = fields.Many2one('dropship.browse.wizard', ondelete='cascade')
    provider_id = fields.Many2one('dropship.provider')
    selected = fields.Boolean(string="✓")
    source_id = fields.Char(string="Product ID", readonly=True)
    title = fields.Char(readonly=True)
    image_url = fields.Char(readonly=True)
    price = fields.Float(readonly=True)
    currency = fields.Char(readonly=True)
    orders_text = fields.Char(string="Sold", readonly=True)
    rating = fields.Float(string="★", readonly=True)
    category_name = fields.Char(string="Category", readonly=True)
    imported = fields.Boolean(string="Imported", readonly=True)
    published = fields.Boolean(string="Live", readonly=True)

    def action_import(self):
        self.ensure_one()
        return self.wizard_id._do(self, publish=False) and \
            self.wizard_id._reopen('Imported: %s' % (self.title or self.source_id))

    def action_import_publish(self):
        self.ensure_one()
        self.wizard_id._do(self, publish=True)
        return self.wizard_id._reopen('Imported & published: %s'
                                      % (self.title or self.source_id))
