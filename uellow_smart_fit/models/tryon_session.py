from odoo import models, fields, api


class CustomerTryOnSession(models.Model):
    """A virtual try-on session: one customer + one product = one session
    that can hold multiple generated images (one per color variant)."""
    _name        = 'customer.tryon.session'
    _description = 'Virtual Try-On Session'
    _order       = 'create_date desc'
    _rec_name    = 'display_name'

    partner_id   = fields.Many2one('res.partner', string='Customer',
                                   required=True, ondelete='cascade', index=True)
    product_id   = fields.Many2one('product.template', string='المنتج',
                                   required=True, ondelete='cascade', index=True)

    source_photo          = fields.Binary(string='صورة المصدر', attachment=True,
                                          help='Snapshot of the customer photo used for this session.')
    source_photo_filename = fields.Char(string='اسم ملف المصدر')

    image_ids    = fields.One2many('customer.tryon.image', 'session_id', string='الصور المولّدة')
    image_count  = fields.Integer(compute='_compute_image_count', store=True)

    status       = fields.Selection([
        ('draft',     'مسودة'),
        ('queued',    'بالانتظار'),
        ('running',   'قيد التوليد'),
        ('done',      'مكتمل'),
        ('failed',    'فشل'),
    ], default='draft', index=True)

    total_cost_usd = fields.Float(string='إجمالي التكلفة (USD)',
                                  compute='_compute_total_cost', store=True, digits=(10, 4))

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('image_ids')
    def _compute_image_count(self):
        for rec in self:
            rec.image_count = len(rec.image_ids)

    @api.depends('image_ids.cost_usd')
    def _compute_total_cost(self):
        for rec in self:
            rec.total_cost_usd = sum(img.cost_usd or 0.0 for img in rec.image_ids)

    @api.depends('partner_id', 'product_id', 'create_date')
    def _compute_display_name(self):
        for rec in self:
            partner = rec.partner_id.name or '—'
            product = rec.product_id.name or '—'
            rec.display_name = f'{partner} · {product}'


class CustomerTryOnImage(models.Model):
    """One generated image inside a try-on session. Each color variant
    produces a separate image record. Phase 2: single image per session.
    Phase 3: multiple (one per color)."""
    _name        = 'customer.tryon.image'
    _description = 'Virtual Try-On Generated Image'
    _order       = 'create_date desc'

    session_id   = fields.Many2one('customer.tryon.session', required=True,
                                   ondelete='cascade', index=True)
    partner_id   = fields.Many2one(related='session_id.partner_id', store=True, index=True)
    product_id   = fields.Many2one(related='session_id.product_id', store=True, index=True)

    # Color (phase 3 will link to product.attribute.value)
    color_text   = fields.Char(string='اللون')

    # Generated image
    image        = fields.Binary(string='الصورة المولّدة', attachment=True)
    image_url    = fields.Char(string='URL الصورة',
                               help='Direct URL from Replicate (CDN). Available until prediction expires.')

    # Provider metadata
    provider     = fields.Selection([
        ('replicate', 'Replicate'),
        ('fashn',     'FASHN AI'),
    ], default='replicate', index=True)
    provider_model         = fields.Char(string='نموذج المزوّد',
                                         help='e.g. cuuupid/idm-vton')
    provider_prediction_id = fields.Char(string='Prediction ID', index=True)

    status       = fields.Selection([
        ('queued',    'بالانتظار'),
        ('running',   'قيد التوليد'),
        ('done',      'مكتمل'),
        ('failed',    'فشل'),
    ], default='queued', index=True)
    error_msg    = fields.Text(string='رسالة الخطأ')

    cost_usd     = fields.Float(string='التكلفة (USD)', digits=(10, 4),
                                help='Cost charged by provider for this single generation.')

    started_at   = fields.Datetime(string='بدأ في')
    finished_at  = fields.Datetime(string='انتهى في')

    reviewer_batch_token = fields.Char(string='Reviewer batch token', index=True,
        help='When the customer asks multiple reviewers for an opinion on this '
             'try-on, all their review.request records share this token.')
