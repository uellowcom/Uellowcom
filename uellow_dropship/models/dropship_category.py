# -*- coding: utf-8 -*-
"""dropship.category — a SEPARATE category taxonomy that lives entirely inside
this module.

The Uellow World store deliberately does NOT reuse the shared
``product.public.category`` table (that is the main store's taxonomy, shared
across every website). Instead the World browsing categories are their own
records here: each carries a bilingual name + an emoji icon + a 2-level parent
tree, and is matched to the lightweight ``dropship.product`` rows by ``code``
(the provider category name). Kept module-internal so it never pollutes the
main store's category management.
"""
from odoo import api, fields, models


class DropshipCategory(models.Model):
    _name = 'dropship.category'
    _description = 'Uellow World Category'
    _order = 'sequence, name'
    _parent_store = True
    _parent_name = 'parent_id'

    name = fields.Char(required=True, translate=True,
                       help="Display name (EN primary + AR translation).")
    code = fields.Char(index=True, required=True,
                       help="Provider category name — the match key to dropship.product.category_name.")
    icon = fields.Char(help="Emoji icon shown on the Uellow World category tiles.")
    ext_id = fields.Char(
        string="Provider Category ID", index=True,
        help="AliExpress category id — used to import & link the full taxonomy.")
    image = fields.Image(
        string="Category Image", max_width=1024, max_height=1024,
        help="Custom tile image. Upload your own here to override the "
             "auto-picked product photo shown on the storefront/app tiles.")
    parent_id = fields.Many2one('dropship.category', string="Parent Category",
                                ondelete='cascade', index=True)
    parent_path = fields.Char(index=True, unaccent=False)
    child_ids = fields.One2many('dropship.category', 'parent_id', string="Sub-categories")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    product_count = fields.Integer(compute='_compute_product_count', string="Products")
    shop_url = fields.Char(compute='_compute_shop_url',
                           help="URL-encoded link to the World shop filtered by this category.")
    effective_image_url = fields.Char(
        compute='_compute_effective_image', string="Tile image URL",
        help="The image actually shown on the storefront/app tile: the uploaded "
             "override if any, otherwise the real AliExpress photo of the best "
             "product in this category.")
    image_preview = fields.Html(
        compute='_compute_effective_image', sanitize=False, string="Tile preview",
        help="Live preview of the category tile image used on the app/storefront.")

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'A category with this code already exists.'),
    ]

    def _compute_product_count(self):
        DP = self.env['dropship.product'].sudo()
        for rec in self:
            rec.product_count = DP.search_count([('category_name', '=', rec.code)]) if rec.code else 0

    def _compute_shop_url(self):
        from urllib.parse import quote
        for rec in self:
            rec.shop_url = '/world/shop?category=%s' % quote(rec.code or '')

    def _match_codes_cached(self):
        """This category's code + all descendant codes (uses the parent tree)."""
        self.ensure_one()
        cats = self.search([('id', 'child_of', self.id)])
        return [c.code for c in cats if c.code]

    def _compute_effective_image(self):
        """Resolve the tile image shown everywhere (backend preview + app +
        storefront): an uploaded override wins, else the real AliExpress photo
        of the best-rated product in this category (or its sub-categories)."""
        DP = self.env['dropship.product'].sudo()
        for rec in self:
            url = False
            if rec.image:
                url = '/web/image/dropship.category/%d/image' % rec.id
            else:
                codes = rec._match_codes_cached()
                prod = DP.search([
                    ('category_name', 'in', codes),
                    ('image_url', '!=', False),
                ], order='rating desc, id desc', limit=1) if codes else DP.browse()
                if prod and prod.image_url:
                    url = prod.image_url
            rec.effective_image_url = url or False
            if url:
                rec.image_preview = (
                    '<img src="%s" style="max-width:128px;max-height:128px;'
                    'border-radius:12px;object-fit:cover;border:1px solid #eee"/>'
                    % url)
            else:
                rec.image_preview = (
                    '<span style="color:#999">%s</span>' % (rec.icon or '🏷️'))

    # ------------------------------------------------------------------ #
    # sync from the source catalog (idempotent)
    # ------------------------------------------------------------------ #
    @api.model
    def _sync_from_catalog(self):
        """Create/refresh a record for every distinct provider category present
        in dropship.product (icons + AR names). Called on install/upgrade and by
        a daily cron so the taxonomy stays in step with imports.
        """
        DP = self.env['dropship.product'].sudo()
        ar_lang = self.env['res.lang'].sudo().search(
            [('code', 'like', 'ar%'), ('active', '=', True)], limit=1)
        groups = DP.read_group([('category_name', '!=', False)],
                               ['category_name'], ['category_name'])
        for g in groups:
            name = g.get('category_name')
            if not name:
                continue
            rec = DP.search([('category_name', '=', name)], limit=1)
            self._ensure(name, rec.category_parent, ar_lang)
        return True

    def _match_codes(self):
        """This category's code + all descendant codes (leaf match keys)."""
        self.ensure_one()
        cats = self.search([('id', 'child_of', self.id)])
        return [c.code for c in cats if c.code]

    def action_view_products(self):
        """Open the source-catalog products that belong to this category
        (and its sub-categories). Smart button on the category form."""
        self.ensure_one()
        codes = self._match_codes()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products — %s' % (self.name or self.code or ''),
            'res_model': 'dropship.product',
            'domain': [('category_name', 'in', codes)],
            'views': [[False, 'list'], [False, 'form']],
            'view_mode': 'list,form',
            'target': 'current',
            'context': {'search_default_g_category': 1},
        }

    @api.model
    def _import_provider_tree(self, provider=None):
        """Import the FULL AliExpress category taxonomy (not just categories seen
        in already-imported products). Idempotent: upserts by provider id.
        Returns the number of categories imported."""
        from odoo.exceptions import UserError
        if provider is None:
            provider = self.env['dropship.provider'].sudo().search([
                ('code', '=', 'aliexpress'), ('state', '=', 'connected'),
            ], limit=1)
        if not provider:
            raise UserError("No connected AliExpress provider to import categories from.")
        try:
            cats = provider._adapter().get_categories()
        except Exception as e:  # noqa: BLE001
            raise UserError("Category import failed: %s" % e)
        ar_lang = self.env['res.lang'].sudo().search(
            [('code', 'like', 'ar%'), ('active', '=', True)], limit=1)
        from .dropship_product import CATEGORY_AR, CATEGORY_ICON
        by_ext = {}
        # pass 1 — upsert each category (match on ext_id, then legacy code)
        for c in cats:
            rec = self.search([('ext_id', '=', c['id'])], limit=1)
            if not rec:
                rec = self.search([('code', '=', c['name'])], limit=1)
            vals = {'ext_id': c['id'], 'name': c['name'], 'code': c['name']}
            if not rec:
                vals['icon'] = CATEGORY_ICON.get(c['name']) or '🏷️'
                rec = self.create(vals)
            else:
                rec.write(vals)
            ar = CATEGORY_AR.get(c['name'])
            if ar and ar_lang and rec.with_context(lang=ar_lang.code).name in (False, c['name']):
                rec.with_context(lang=ar_lang.code).name = ar
            by_ext[c['id']] = (rec, c.get('parent_id') or '0')
        # pass 2 — link parents
        for _ext, (rec, pext) in by_ext.items():
            if pext and pext != '0' and pext in by_ext:
                parent = by_ext[pext][0]
                if parent.id != rec.id and rec.parent_id.id != parent.id:
                    rec.parent_id = parent.id
        self.env.cr.commit()
        return len(by_ext)

    @api.model
    def action_import_provider_tree(self):
        n = self._import_provider_tree()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Categories imported',
                'message': '%d AliExpress categories synced.' % n,
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def _ensure(self, code, parent_code, ar_lang=None):
        """Find/create a category (with its parent) by provider name. Returns it."""
        code = (code or '').strip()
        if not code:
            return self.browse()
        if ar_lang is None:
            ar_lang = self.env['res.lang'].sudo().search(
                [('code', 'like', 'ar%'), ('active', '=', True)], limit=1)
        parent = self.browse()
        pcode = (parent_code or '').strip()
        if pcode and pcode != code:
            parent = self._upsert_one(pcode, self.browse(), ar_lang)
        return self._upsert_one(code, parent, ar_lang)

    def _upsert_one(self, code, parent, ar_lang):
        from .dropship_product import CATEGORY_AR, CATEGORY_ICON
        rec = self.search([('code', '=', code)], limit=1)
        icon = CATEGORY_ICON.get(code) or '🏷️'
        if not rec:
            rec = self.create({
                'code': code,
                'name': code,                      # English (default lang)
                'icon': icon,
                'parent_id': parent.id if parent else False,
            })
        else:
            upd = {}
            if rec.icon != icon:
                upd['icon'] = icon
            if parent and rec.parent_id.id != parent.id:
                upd['parent_id'] = parent.id
            if upd:
                rec.write(upd)
        # Arabic translation (only fill if missing / still equal to the code)
        ar = CATEGORY_AR.get(code)
        if ar and ar_lang and rec.with_context(lang=ar_lang.code).name in (False, code):
            rec.with_context(lang=ar_lang.code).name = ar
        return rec
