from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductSizeChart(models.Model):
    """Per-product-per-size measurement chart.

    Each row is *linked* to an Odoo attribute value (the real source of
    variants), so Beena can resolve the exact product.product when adding
    to cart. Legacy rows with only a free-text size_label still work.
    """
    _name = 'product.size.chart'
    _description = 'Product Size Chart Row'
    _order = 'product_id, sequence, size_label'
    _rec_name = 'size_label'

    product_id   = fields.Many2one('product.template', string='Product',
                                   required=True, ondelete='cascade', index=True)
    sequence     = fields.Integer(string='Sequence', default=10)

    # ── Link to the Odoo attribute system (PRIMARY way to identify a size) ──
    attribute_value_id = fields.Many2one(
        'product.attribute.value', string='Attribute value',
        ondelete='set null', index=True,
        help='Link this row to the actual Odoo attribute value (e.g. the '
             '"L" record of the "Size" attribute on this product). '
             'When set, Beena can resolve the exact variant for add-to-cart.',
    )
    attribute_id = fields.Many2one(
        'product.attribute', related='attribute_value_id.attribute_id',
        store=True, readonly=True,
    )
    # Optional per-variant override. When set, this row applies ONLY to
    # that specific variant (e.g. "Size L in Color Black"). When null, the
    # row applies to all variants matching attribute_value_id.
    product_variant_id = fields.Many2one(
        'product.product', string='Variant override',
        ondelete='cascade', index=True,
        domain="[('product_tmpl_id', '=', product_id)]",
        help='Optional: when set, this row applies only to that specific '
             'variant. Use it when a color/fabric variant has different '
             'measurements than the generic size.',
    )
    # Free-text label (used as fallback or for display). Auto-filled from
    # attribute_value_id.name when present, but admin can still override.
    size_label   = fields.Char(string='Size', required=True,
                               help='Examples: S, M, L, XL, 40, 42 ...')

    # ── Upper body (shirts / dresses / jackets) ──────────────────────────
    chest_cm     = fields.Float(string='Chest (cm)',
                                help='Garment chest measurement (not the body).')
    shoulder_cm  = fields.Float(string='Shoulder (cm)')
    sleeve_cm    = fields.Float(string='Sleeve (cm)')
    length_cm    = fields.Float(string='Total length (cm)')

    # ── Lower body (pants / shorts / skirts) ─────────────────────────────
    waist_cm     = fields.Float(string='Waist (cm)')
    hip_cm       = fields.Float(string='Hip (cm)')
    inseam_cm    = fields.Float(string='Inseam (cm)')
    thigh_cm     = fields.Float(string='Thigh (cm)')

    # ── Shoe-specific measurements ───────────────────────────────────────
    foot_length_cm = fields.Float(string='Inner foot length (cm)',
        help='For shoes only: the foot length the shoe accommodates, in cm.')

    # ── Fit tolerance for this row (overrides product default) ───────────
    tolerance_cm = fields.Float(string='Tolerance ± (cm)', default=0.0,
                                help='Small extra allowance not considered tight.')

    # ── Status flags ────────────────────────────────────────────────────
    is_orphan = fields.Boolean(
        string='Orphan', compute='_compute_is_orphan', store=True,
        help='True when this row was linked to an attribute value '
             'that has been removed from the product. Needs admin attention.',
    )

    @api.depends('attribute_value_id', 'product_id.attribute_line_ids.value_ids')
    def _compute_is_orphan(self):
        for rec in self:
            if not rec.attribute_value_id:
                rec.is_orphan = False
                continue
            current_values = rec.product_id.attribute_line_ids.value_ids
            rec.is_orphan = rec.attribute_value_id not in current_values

    @api.onchange('attribute_value_id')
    def _onchange_attribute_value_id(self):
        if self.attribute_value_id and not self.size_label:
            self.size_label = self.attribute_value_id.name

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-fill size_label from attribute_value if missing
            if not vals.get('size_label') and vals.get('attribute_value_id'):
                av = self.env['product.attribute.value'].browse(vals['attribute_value_id'])
                vals['size_label'] = av.name or 'Size'
        return super().create(vals_list)

    _sql_constraints = [
        ('uniq_product_attr_value_variant',
         'unique(product_id, attribute_value_id, product_variant_id)',
         'Duplicate chart row for the same (product, attribute value, variant).'),
    ]


FASHION_CATEGORY_KEYWORDS = [
    'shirt', 'tshirt', 't-shirt', 'top', 'blouse', 'polo',
    'jacket', 'hoodie', 'sweater', 'coat', 'blazer',
    'pants', 'jeans', 'shorts', 'skirt', 'trousers',
    'dress', 'abaya', 'gown',
    'shoe', 'sneaker', 'boot', 'sandal', 'slipper',
    'قميص', 'تيشرت', 'بنطلون', 'جاكيت', 'فستان', 'عباية', 'تنورة',
    'حذاء', 'كوتش', 'بوت',
]


class ProductTemplateSizeChart(models.Model):
    _inherit = 'product.template'

    size_chart_ids = fields.One2many(
        'product.size.chart', 'product_id', string='جدول المقاسات',
    )
    has_size_chart = fields.Boolean(
        string='يحتوي على جدول مقاسات',
        compute='_compute_has_size_chart', store=True,
    )
    size_chart_count = fields.Integer(
        string='عدد المقاسات',
        compute='_compute_has_size_chart', store=True,
    )

    is_fashion_item = fields.Boolean(
        string='منتج فاشن',
        compute='_compute_is_fashion_item', store=True,
        help='يتم استنتاجه تلقائياً من اسم المنتج وفئته.',
    )
    needs_size_chart = fields.Boolean(
        string='يحتاج جدول مقاسات',
        compute='_compute_needs_size_chart', store=True,
        help='منتج فاشن منشور بدون جدول مقاسات تفصيلي.',
    )

    @api.depends('size_chart_ids')
    def _compute_has_size_chart(self):
        for p in self:
            p.size_chart_count = len(p.size_chart_ids)
            p.has_size_chart   = bool(p.size_chart_ids)

    @api.depends('name', 'categ_id', 'categ_id.name')
    def _compute_is_fashion_item(self):
        for p in self:
            txt = ((p.name or '') + ' ' + (p.categ_id.name or '')).lower()
            p.is_fashion_item = any(kw in txt for kw in FASHION_CATEGORY_KEYWORDS)

    @api.depends('is_fashion_item', 'has_size_chart', 'is_published')
    def _compute_needs_size_chart(self):
        for p in self:
            p.needs_size_chart = bool(p.is_fashion_item) and (not p.has_size_chart) and bool(p.is_published)

    # ── Out-of-sync detection (attribute values changed vs chart rows) ──
    size_chart_out_of_sync = fields.Boolean(
        string='Size chart out of sync',
        compute='_compute_size_chart_out_of_sync', store=True,
        help='True when the product\'s Size attribute has values that '
             'are not represented in the size chart, or vice versa.',
    )
    size_chart_orphan_count = fields.Integer(
        string='# orphan chart rows',
        compute='_compute_size_chart_out_of_sync', store=True,
    )
    size_chart_missing_count = fields.Integer(
        string='# size values without chart row',
        compute='_compute_size_chart_out_of_sync', store=True,
    )

    @api.depends('attribute_line_ids.value_ids', 'size_chart_ids.attribute_value_id', 'size_chart_ids.is_orphan')
    def _compute_size_chart_out_of_sync(self):
        for p in self:
            line = p._detect_size_attribute_line() if hasattr(p, '_detect_size_attribute_line') else False
            if not line:
                p.size_chart_orphan_count = 0
                p.size_chart_missing_count = 0
                p.size_chart_out_of_sync = False
                continue
            value_ids   = set(line.value_ids.ids)
            charted_ids = {r.attribute_value_id.id for r in p.size_chart_ids if r.attribute_value_id}
            orphans = sum(1 for r in p.size_chart_ids if r.is_orphan)
            missing = len(value_ids - charted_ids)
            p.size_chart_orphan_count  = orphans
            p.size_chart_missing_count = missing
            p.size_chart_out_of_sync   = bool(orphans or missing)

    def action_sync_size_chart(self):
        """Add missing rows for new attribute values, leave orphans alone."""
        result = {'created': 0}
        for p in self:
            line = p._detect_size_attribute_line()
            if not line:
                continue
            existing_ids = {r.attribute_value_id.id for r in p.size_chart_ids if r.attribute_value_id}
            Chart = self.env['product.size.chart'].sudo()
            next_seq = max((r.sequence for r in p.size_chart_ids), default=0) + 10
            for value in line.value_ids:
                if value.id in existing_ids:
                    continue
                Chart.create({
                    'product_id':         p.id,
                    'sequence':           next_seq,
                    'attribute_value_id': value.id,
                    'size_label':         value.name,
                })
                next_seq += 10
                result['created'] += 1
        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'type':  'success' if result['created'] else 'info',
                'title': _('Size Chart synced'),
                'message': (
                    _('Created %d new chart rows.') % result['created']
                    if result['created'] else
                    _('Size chart is already in sync.')
                ),
                'sticky': False,
            },
        }

    # ── Size-attribute detection ─────────────────────────────────────────
    def _size_attribute_keywords(self):
        """Read configured keywords (comma-separated) that identify a 'Size'
        attribute. Defaults are sensible for EN+AR Uellow catalog."""
        ICP = self.env['ir.config_parameter'].sudo()
        raw = ICP.get_param('uellow_fit.size_attribute_keywords',
                            'size,مقاس,حجم,size eu,size us,clothing size')
        return [kw.strip().lower() for kw in (raw or '').split(',') if kw.strip()]

    def _detect_size_attribute_line(self):
        """Return the product.template.attribute.line that represents 'Size'
        for this template, or False if none matches the keywords."""
        self.ensure_one()
        keywords = self._size_attribute_keywords()
        for line in self.attribute_line_ids:
            name = (line.attribute_id.name or '').lower().strip()
            if any(kw in name for kw in keywords):
                return line
        return False

    def action_generate_size_chart(self):
        """Create empty chart rows for each value of the detected size attribute.
        Skips values that already have a chart row."""
        self.ensure_one()
        line = self._detect_size_attribute_line()
        if not line:
            raise UserError(_(
                "No 'Size' attribute found on this product. "
                "Add a Size attribute first (the keywords scanned are: %s)."
            ) % ', '.join(self._size_attribute_keywords()))

        Chart = self.env['product.size.chart'].sudo()
        existing = {r.attribute_value_id.id for r in self.size_chart_ids if r.attribute_value_id}
        created  = 0
        for seq, value in enumerate(line.value_ids, start=1):
            if value.id in existing:
                continue
            Chart.create({
                'product_id':         self.id,
                'sequence':           seq * 10,
                'attribute_value_id': value.id,
                'size_label':         value.name,
            })
            created += 1

        return {
            'type': 'ir.actions.client',
            'tag':  'display_notification',
            'params': {
                'type':  'success' if created else 'info',
                'title': _('Size Chart'),
                'message': (
                    _("Created %d empty size rows from the '%s' attribute. Fill in the measurements below.")
                    % (created, line.attribute_id.name)
                    if created else
                    _("All size values already have chart rows. Nothing to add.")
                ),
                'sticky': False,
            },
        }
