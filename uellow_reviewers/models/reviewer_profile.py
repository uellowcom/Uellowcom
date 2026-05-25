from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ReviewerProfile(models.Model):
    _name        = 'reviewer.profile'
    _description = 'Uellow Reviewer Profile'
    _rec_name    = 'display_name'
    _order       = 'rating desc, review_count desc'

    # ── Partner link ──────────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Partner', required=True,
        ondelete='cascade', index=True,
    )


    # ── Identity ──────────────────────────────────────────────────────────────
    display_name  = fields.Char(string='الاسم المعروض', required=True)
    bio           = fields.Text(string='نبذة مختصرة')
    avatar        = fields.Image(string='الصورة', max_width=256, max_height=256)

    # ── Specialties ───────────────────────────────────────────────────────────
    specialty_ids = fields.Many2many(
        'product.category',
        'reviewer_specialty_rel',
        'reviewer_id', 'categ_id',
        string='التخصصات',
    )
    specialty_text = fields.Char(
        string='تخصصات (نص حر)',
        help='مثال: موضة رجالي، إلكترونيات',
    )

    # ── Status ────────────────────────────────────────────────────────────────
    state = fields.Selection([
        ('pending',  'بانتظار الموافقة'),
        ('approved', 'معتمد'),
        ('suspended','موقوف'),
        ('rejected', 'مرفوض'),
    ], default='pending', string='الحالة', index=True)

    is_online    = fields.Boolean(string='أونلاين', default=False, index=True)
    verified     = fields.Boolean(string='محقق الهوية', default=False)
    verified_purchase = fields.Boolean(
        string='اشترى من Uellow', default=False,
        help='يجب أن يكون قد اشترى قبل التسجيل كريفيور',
    )

    # ── Level ─────────────────────────────────────────────────────────────────
    level = fields.Selection([
        ('starter', '⭐ Starter'),
        ('regular', '⭐⭐ Regular'),
        ('expert',  '⭐⭐⭐ Expert'),
        ('elite',   '⭐⭐⭐⭐ Elite'),
    ], compute='_compute_level', store=True, string='المستوى')

    # ── Stats ─────────────────────────────────────────────────────────────────
    review_count    = fields.Integer(string='عدد المراجعات', default=0)
    purchase_count  = fields.Integer(string='عدد المشتريات بعد الرأي', default=0)
    rating          = fields.Float(string='التقييم', default=5.0, digits=(3, 2))
    conversion_rate = fields.Float(
        string='معدل التحويل %',
        compute='_compute_conversion_rate', store=True,
    )

    # ── Pricing ───────────────────────────────────────────────────────────────
    price_written = fields.Float(string='سعر الرأي المكتوب (KD)', default=0.5)
    price_chat    = fields.Float(string='سعر الشات المباشر (KD)', default=0.75)

    # ── Allowed session types ─────────────────────────────────────────────────
    allow_written = fields.Boolean(string='رأي مكتوب', default=True)
    allow_chat    = fields.Boolean(string='شات مباشر', default=True)
    allow_photo   = fields.Boolean(string='صورة + رأي', default=True)
    allow_video   = fields.Boolean(string='مكالمة فيديو', default=False)

    # ── Commission wallet ─────────────────────────────────────────────────────
    wallet_balance  = fields.Float(string='رصيد المحفظة (KD)', default=0.0)
    total_earned    = fields.Float(string='إجمالي المكتسب (KD)', default=0.0)

    # ── Complaint tracking ────────────────────────────────────────────────────
    complaint_count = fields.Integer(string='عدد الشكاوى', default=0)

    # ── Active requests ───────────────────────────────────────────────────────
    request_ids = fields.One2many('review.request', 'reviewer_id', string='الطلبات')

    # ── Computed ──────────────────────────────────────────────────────────────
    @api.depends('review_count')
    def _compute_level(self):
        for rec in self:
            if rec.review_count >= 200:
                rec.level = 'elite'
            elif rec.review_count >= 51:
                rec.level = 'expert'
            elif rec.review_count >= 11:
                rec.level = 'regular'
            else:
                rec.level = 'starter'

    @api.depends('review_count', 'purchase_count')
    def _compute_conversion_rate(self):
        for rec in self:
            if rec.review_count > 0:
                rec.conversion_rate = round(
                    (rec.purchase_count / rec.review_count) * 100, 1
                )
            else:
                rec.conversion_rate = 0.0

    # ── Auto-check verified purchase ─────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.partner_id:
                orders = self.env['sale.order'].sudo().search_count([
                    ('partner_id', '=', rec.partner_id.id),
                    ('state', 'in', ['sale', 'done']),
                ])
                rec.verified_purchase = orders > 0
        return records

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_suspend(self):
        self.write({'state': 'suspended', 'is_online': False})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def toggle_online(self):
        if self.state != 'approved':
            raise ValidationError('يجب أن يكون الريفيور معتمداً أولاً')
        self.is_online = not self.is_online

    def to_dict(self):
        """Serialize for JSON API."""
        return {
            'id':            self.id,
            'name':          self.display_name,
            'bio':           self.bio or '',
            'level':         self.level,
            'level_label':   dict(self._fields['level'].selection).get(self.level, ''),
            'rating':        round(self.rating, 1),
            'review_count':  self.review_count,
            'conversion':    self.conversion_rate,
            'is_online':     self.is_online,
            'verified':      self.verified,
            'verified_purchase': self.verified_purchase,
            'allow_written': self.allow_written,
            'allow_chat':    self.allow_chat,
            'allow_photo':   self.allow_photo,
            'allow_video':   self.allow_video,
            'price_written': self.price_written,
            'price_chat':    self.price_chat,
            'specialties':   [c.name for c in self.specialty_ids],
            'specialty_text': self.specialty_text or '',
            'avatar_url':    f'/web/image/reviewer.profile/{self.id}/avatar/64x64',
        }
