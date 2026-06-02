from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SizeChartTemplate(models.Model):
    """A reusable size-chart definition (e.g. 'Men's T-Shirts 2026').

    One template lists a set of named sizes with their measurements.
    Admins apply a template to one or many products — the template lines
    are copied into product.size.chart rows. Future edits to the template
    can be re-applied via the same action.
    """
    _name = 'product.size.chart.template'
    _description = 'Size Chart Template'
    _order = 'name'

    name        = fields.Char(string='Name', required=True,
                              help="e.g. 'Men's T-Shirts — Standard 2026'.")
    description = fields.Text(string='Description')
    category_id = fields.Many2one(
        'product.category', string='Default category',
        help='Optional: if set, applying this template in bulk picks all '
             'products in this category.',
    )
    is_active   = fields.Boolean(string='Active', default=True)

    line_ids = fields.One2many(
        'product.size.chart.template.line', 'template_id',
        string='Sizes', copy=True,
    )

    applied_product_ids = fields.Many2many(
        'product.template', string='Applied to', copy=False,
        help='Products that currently use this template.',
    )
    applied_product_count = fields.Integer(
        compute='_compute_applied_count', string='# applied products',
    )

    @api.depends('applied_product_ids')
    def _compute_applied_count(self):
        for tpl in self:
            tpl.applied_product_count = len(tpl.applied_product_ids)

    # ── Apply to products ────────────────────────────────────────────────
    def action_apply_to_products(self):
        """Open a wizard to pick target products."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.size.chart.template.apply.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_template_id': self.id},
        }

    def apply_to_products(self, products, replace_existing=False):
        """Copy this template's lines into product.size.chart rows of each
        target product. Returns counts.

        If replace_existing is True, deletes existing chart rows first.
        Otherwise creates missing rows and updates existing ones by size_label.
        """
        self.ensure_one()
        Chart = self.env['product.size.chart'].sudo()
        created = updated = 0

        for product in products:
            if replace_existing:
                product.size_chart_ids.unlink()
                existing_by_label = {}
            else:
                existing_by_label = {
                    (r.size_label or '').strip().lower(): r
                    for r in product.size_chart_ids
                }

            # Try to auto-link to product's Size attribute if present
            size_line = product._detect_size_attribute_line() \
                if hasattr(product, '_detect_size_attribute_line') else False
            values_by_name = {}
            if size_line:
                values_by_name = {
                    (v.name or '').strip().lower(): v
                    for v in size_line.value_ids
                }

            for tline in self.line_ids:
                key = (tline.size_label or '').strip().lower()
                vals = tline._copy_to_chart_vals(product.id)
                # auto-link attribute value when possible
                if key in values_by_name and not vals.get('attribute_value_id'):
                    vals['attribute_value_id'] = values_by_name[key].id

                existing = existing_by_label.get(key)
                if existing:
                    existing.write(vals)
                    updated += 1
                else:
                    Chart.create(vals)
                    created += 1

            if product not in self.applied_product_ids:
                self.applied_product_ids = [(4, product.id)]

        return {'created': created, 'updated': updated}

    def action_view_applied_products(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Applied products'),
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.applied_product_ids.ids)],
        }


class SizeChartTemplateLine(models.Model):
    _name = 'product.size.chart.template.line'
    _description = 'Size Chart Template Line'
    _order = 'sequence, size_label'

    template_id = fields.Many2one('product.size.chart.template',
                                  required=True, ondelete='cascade')
    sequence    = fields.Integer(default=10)
    size_label  = fields.Char(string='Size', required=True)

    chest_cm       = fields.Float(string='Chest (cm)')
    shoulder_cm    = fields.Float(string='Shoulder (cm)')
    sleeve_cm      = fields.Float(string='Sleeve (cm)')
    length_cm      = fields.Float(string='Total length (cm)')
    waist_cm       = fields.Float(string='Waist (cm)')
    hip_cm         = fields.Float(string='Hip (cm)')
    inseam_cm      = fields.Float(string='Inseam (cm)')
    thigh_cm       = fields.Float(string='Thigh (cm)')
    foot_length_cm = fields.Float(string='Foot length (cm)')
    tolerance_cm   = fields.Float(string='Tolerance ± (cm)', default=0.0)

    def _copy_to_chart_vals(self, product_id):
        self.ensure_one()
        return {
            'product_id':    product_id,
            'sequence':      self.sequence,
            'size_label':    self.size_label,
            'chest_cm':      self.chest_cm,
            'shoulder_cm':   self.shoulder_cm,
            'sleeve_cm':     self.sleeve_cm,
            'length_cm':     self.length_cm,
            'waist_cm':      self.waist_cm,
            'hip_cm':        self.hip_cm,
            'inseam_cm':     self.inseam_cm,
            'thigh_cm':      self.thigh_cm,
            'foot_length_cm':self.foot_length_cm,
            'tolerance_cm':  self.tolerance_cm,
        }


# ──────────────────────────────────────────────────────────────────────────
# Wizard: apply a template to selected products
# ──────────────────────────────────────────────────────────────────────────
class SizeChartTemplateApplyWizard(models.TransientModel):
    _name = 'product.size.chart.template.apply.wizard'
    _description = 'Apply Size Chart Template to Products'

    template_id = fields.Many2one('product.size.chart.template',
                                  required=True, readonly=True)
    mode = fields.Selection([
        ('selected', 'A specific list of products'),
        ('category', 'All products in a category'),
    ], default='selected', required=True)
    product_ids = fields.Many2many('product.template', string='Products')
    category_id = fields.Many2one('product.category', string='Category')
    replace_existing = fields.Boolean(
        string='Replace existing chart rows', default=False,
        help='If checked, deletes existing chart rows on each product '
             'before applying. Otherwise merges by size label.',
    )

    @api.onchange('template_id')
    def _onchange_template_default_category(self):
        if self.template_id and self.template_id.category_id and not self.category_id:
            self.category_id = self.template_id.category_id
            if self.mode == 'selected':
                self.mode = 'category'

    def action_apply(self):
        self.ensure_one()
        if self.mode == 'selected':
            products = self.product_ids
        else:
            if not self.category_id:
                raise UserError(_('Please choose a category.'))
            products = self.env['product.template'].search(
                [('categ_id', 'child_of', self.category_id.id)]
            )

        if not products:
            raise UserError(_('No products selected to apply the template to.'))

        result = self.template_id.apply_to_products(
            products, replace_existing=self.replace_existing,
        )
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'type':  'success',
                'title': _('Size Chart Template applied'),
                'message': _(
                    'Applied to %d products — created %d rows, updated %d rows.'
                ) % (len(products), result['created'], result['updated']),
                'sticky': True,
            },
        }
