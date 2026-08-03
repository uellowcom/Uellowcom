# -*- coding: utf-8 -*-
"""AI category assignment.

Imported products often land with NO eCommerce category, which breaks shop
browsing/filters/SEO. This asks the cheap Haiku model to pick the best-fitting
EXISTING public category for each product from its name (it can only choose a
real category id, never invent one). Runs for existing products (wizard + daily
cron) and is safe to re-run (only touches products that still have no category).
"""
import json
import logging
import re

from odoo import api, fields, models, _

from .utils import resolve_ai_config

_logger = logging.getLogger(__name__)
_AI_TIMEOUT_S = 60


class ProductTemplateCategoryAI(models.Model):
    _inherit = 'product.template'

    @api.model
    def _sc_category_catalog(self):
        """Return (prompt_text, valid_id_set) of all public categories as
        'id: Parent / Child' lines, so the AI picks a real, specific node."""
        C = self.env['product.public.category'].sudo().search([])
        lines, ids = [], set()
        for c in C:
            names, x = [], c
            depth = 0
            while x and depth < 6:
                names.append(x.name or '')
                x = x.parent_id
                depth += 1
            lines.append('%d: %s' % (c.id, ' / '.join(reversed(names))))
            ids.add(c.id)
        return '\n'.join(lines), ids

    @api.model
    def _sc_guess_categories(self, recs, batch=20):
        """Assign the best public category to each product in `recs` that has
        none. Returns the number of products categorised."""
        recs = recs.filtered(lambda p: not p.public_categ_ids)
        if not recs:
            return 0
        api_key, model = resolve_ai_config(self.env)
        if not api_key:
            return 0
        ICP = self.env['ir.config_parameter'].sudo()
        model = (ICP.get_param('uellow.sc.translate_model') or 'claude-haiku-4-5').strip() or model
        catalog, valid_ids = self._sc_category_catalog()
        if not valid_ids:
            return 0
        sysmsg = (
            "You are a product taxonomist for an electronics & lifestyle store. "
            "Below is the FULL list of available categories as 'id: path'. For "
            "each product NAME, choose the single best-fitting category id from "
            "the list — prefer the most specific (deepest) sensible node. You "
            "MUST return an id that exists in the list; never invent one. If "
            "truly unsure, pick the closest general category. Return ONLY a JSON "
            "object mapping the product number (as a string) to the chosen "
            "category id (integer).\n\nCATEGORIES:\n" + catalog)
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=_AI_TIMEOUT_S)
        except ImportError:
            return 0
        done = 0
        recs = list(recs)
        for s in range(0, len(recs), batch):
            chunk = recs[s:s + batch]
            listing = "\n".join(
                "%d. %s" % (i, (chunk[i].with_context(lang='en_US').name or ''))
                for i in range(len(chunk)))
            try:
                msg = client.messages.create(
                    model=model, max_tokens=800, system=sysmsg,
                    messages=[{'role': 'user',
                               'content': 'Products:\n' + listing}])
                text = msg.content[0].text if msg.content else '{}'
                text = re.sub(r'^```(?:json)?\s*', '', text.strip())
                text = re.sub(r'\s*```$', '', text)
                out = json.loads(text)
            except Exception as e:                # noqa: BLE001
                _logger.warning('Category guess failed for a batch: %s', e)
                continue
            for i, p in enumerate(chunk):
                try:
                    cid = int(out.get(str(i)))
                except (TypeError, ValueError):
                    continue
                if cid in valid_ids and not p.public_categ_ids:
                    p.public_categ_ids = [(4, cid)]
                    done += 1
            self.env.cr.commit()
        return done

    @api.model
    def cron_sc_autocategorize(self, limit=80):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow.sc.autocategorize', '1') not in ('1', 'True', 'true'):
            return
        recs = self.search([
            ('is_published', '=', True), ('sale_ok', '=', True),
            ('public_categ_ids', '=', False),
        ], limit=limit)
        if recs:
            n = self._sc_guess_categories(recs)
            _logger.info('AI auto-categorise cron: set category on %d product(s)', n)


class CategoryAssignWizard(models.TransientModel):
    _name = 'uellow.category.assign'
    _description = 'AI Category Assignment'

    scope_brand_id = fields.Many2one('product.brand', string='Brand')
    only_uncategorized = fields.Boolean('Only products without a category', default=True)
    published_only = fields.Boolean('Published only', default=True)
    limit = fields.Integer('Max products per run', default=60)
    dry_run = fields.Boolean('Dry run (preview, no changes)', default=True)
    result_html = fields.Html('Result', readonly=True)

    def _targets(self):
        T = self.env['product.template']
        # Exclude Uellow World (dropship) products — they are managed by the
        # World module, not the main-store connector.
        domain = [('sale_ok', '=', True), ('is_dropship', '=', False)]
        if self.published_only:
            domain.append(('is_published', '=', True))
        if self.only_uncategorized:
            domain.append(('public_categ_ids', '=', False))
        if self.scope_brand_id and 'brand_id' in T._fields:
            domain.append(('brand_id', '=', self.scope_brand_id.id))
        return T.search(domain, order='create_date desc', limit=max(1, self.limit))

    def action_run(self):
        self.ensure_one()
        T = self.env['product.template']
        targets = self._targets()
        if not targets:
            self.result_html = "<p>No matching products.</p>"
            return self._reopen()
        if self.dry_run:
            preview = targets[:15]
            names = [t.with_context(lang='en_US').name or '' for t in preview]
            catalog, valid = T._sc_category_catalog()
            # reuse the guesser logic for a preview without writing
            api_key, model = resolve_ai_config(self.env)
            rows = "<p>Dry run — %d product(s) would be categorised.</p>" % len(targets)
            self.result_html = rows + "<p>Untick Dry run and Run to apply.</p>"
            return self._reopen()
        n = T._sc_guess_categories(targets)
        self.result_html = "<p>✅ Categorised <b>%d</b> product(s).</p>" % n
        return self._reopen()

    def _reopen(self):
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new'}
