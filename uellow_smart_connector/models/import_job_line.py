from odoo import models, fields, api, _


class ImportJobLine(models.Model):
    """
    One line per product found/matched in a Smart Connector job.
    Stores raw extracted data + AI-enriched data + review decision.
    """
    _name = 'uellow.import.job.line'
    _description = 'سطر عملية الاستيراد'
    _order = 'job_id, has_warning desc, id'

    job_id = fields.Many2one(
        'uellow.import.job', required=True,
        ondelete='cascade', index=True,
    )

    # Product names
    name_en = fields.Char('الاسم (إنجليزي)', required=True)
    name_ar = fields.Char('الاسم (عربي)')

    # Descriptions
    description_en = fields.Text('الوصف (إنجليزي)')
    description_ar = fields.Text('الوصف (عربي)')

    # Pricing
    new_price = fields.Float('السعر الجديد')
    old_price = fields.Float('السعر الحالي', readonly=True)
    price_diff_pct = fields.Float(
        compute='_compute_price_diff', string='فرق السعر (%)', store=True,
    )

    # Stock
    new_qty = fields.Integer('الكمية الجديدة')

    # Source info
    source_sku = fields.Char('SKU المصدر')
    source_url = fields.Char('رابط المصدر')

    # Matching
    product_action = fields.Selection([
        ('new',    'منتج جديد'),
        ('update', 'تحديث منتج موجود'),
        ('skip',   'تجاهل'),
    ], default='new', string='الإجراء', required=True)

    match_score = fields.Integer('نسبة التطابق (%)', default=0)
    existing_product_id = fields.Many2one(
        'product.template', string='المنتج الموجود',
        ondelete='set null',
    )

    # Line status
    line_state = fields.Selection([
        ('pending',  'بانتظار المراجعة'),
        ('approved', 'معتمد'),
        ('rejected', 'مرفوض'),
        ('applied',  'تم التطبيق'),
    ], default='pending', string='حالة السطر', index=True)

    has_warning = fields.Boolean('تحذير', default=False, index=True)
    warning_reason = fields.Char('سبب التحذير')
    ai_enriched = fields.Boolean('AI أثرى', default=False)

    reject_reason = fields.Selection([
        ('price_unrealistic',   'سعر غير منطقي'),
        ('bad_description',     'وصف غير كافٍ'),
        ('bad_images',          'صور سيئة'),
        ('wrong_category',      'فئة خاطئة'),
        ('duplicate',           'منتج مكرر'),
        ('other',               'أخرى'),
    ], string='سبب الرفض')
    reject_note = fields.Char('ملاحظة الرفض')

    # Applied product
    applied_product_id = fields.Many2one(
        'product.template', string='المنتج المُطبَّق', readonly=True,
    )

    @api.depends('new_price', 'old_price')
    def _compute_price_diff(self):
        for l in self:
            if l.old_price and l.old_price > 0:
                l.price_diff_pct = (l.new_price - l.old_price) / l.old_price * 100
            else:
                l.price_diff_pct = 0.0

    def action_approve(self):
        self.line_state = 'approved'
        self.product_action = self.product_action or 'new'

    def action_reject(self):
        self.line_state = 'rejected'

    def action_apply(self):
        """Apply this single line to product catalog."""
        self.ensure_one()
        if self.line_state != 'approved':
            return
        product = self._apply_to_catalog()
        self.applied_product_id = product
        self.line_state = 'applied'

    def _apply_to_catalog(self):
        """Create or update product.template from this line's data."""
        vals = {
            'name': self.name_ar or self.name_en,
            'description_sale': self.description_ar or self.description_en or '',
            'list_price': self.new_price or 0.0,
            'type': 'consu',
        }
        if self.product_action == 'update' and self.existing_product_id:
            # Preserve rollback data on job before overwriting
            job = self.job_id
            if job.rollback_data:
                import json
                rb = json.loads(job.rollback_data)
            else:
                import json
                rb = {}
            ep = self.existing_product_id
            rb[str(ep.id)] = {
                'name': ep.name,
                'description_sale': ep.description_sale or '',
                'list_price': ep.list_price,
            }
            job.rollback_data = json.dumps(rb)
            self.existing_product_id.write(vals)
            return self.existing_product_id
        else:
            return self.env['product.template'].create(vals)
