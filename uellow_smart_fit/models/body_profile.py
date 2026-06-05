from odoo import models, fields, api


class CustomerBodyProfile(models.Model):
    _name        = 'customer.body.profile'
    _description = 'Customer Body Measurements Profile'
    _rec_name    = 'partner_id'

    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        required=True, ondelete='cascade', index=True,
    )

    # ── Basic ─────────────────────────────────────────────────────────────────
    height     = fields.Float(string='الطول (cm)')
    weight     = fields.Float(string='الوزن (kg)')
    body_type  = fields.Selection([
        ('slim',     'Slim / نحيف'),
        ('regular',  'Regular / عادي'),
        ('athletic', 'Athletic / رياضي'),
        ('plus',     'Plus / بلس'),
    ], string='نوع الجسم', default='regular')
    gender     = fields.Selection([
        ('male',   'ذكر'),
        ('female', 'أنثى'),
    ], string='الجنس')
    age_range  = fields.Selection([
        ('teen',   '13-17'),
        ('young',  '18-30'),
        ('adult',  '31-50'),
        ('senior', '50+'),
    ], string='الفئة العمرية')

    # ── Upper body ────────────────────────────────────────────────────────────
    shoulder   = fields.Float(string='الكتف (cm)')
    chest      = fields.Float(string='الصدر (cm)')
    waist      = fields.Float(string='الوسط (cm)')
    hip        = fields.Float(string='الورك (cm)')
    arm_length = fields.Float(string='طول الذراع (cm)')

    # ── Lower body ────────────────────────────────────────────────────────────
    inseam     = fields.Float(string='الداخل (cm)')
    thigh      = fields.Float(string='الفخذ (cm)')

    # ── Shoe ─────────────────────────────────────────────────────────────────
    shoe_size_eu = fields.Float(string='مقاس الحذاء EU')
    shoe_size_us = fields.Float(string='مقاس الحذاء US')
    foot_length_cm = fields.Float(string='طول القدم (cm)',
        help='أدق من EU/US — يقاس من نهاية الكعب لرأس الإصبع الأطول.')
    shoe_width   = fields.Selection([
        ('narrow', 'ضيق'),
        ('normal', 'عادي'),
        ('wide',   'واسع'),
    ], string='عرض القدم', default='normal')

    # ── Fit preferences ───────────────────────────────────────────────────────
    preferred_fit = fields.Selection([
        ('slim',    'Slim Fit'),
        ('regular', 'Regular Fit'),
        ('loose',   'Loose Fit'),
    ], string='تفضيل القصة', default='regular')

    # v2.1.54 — measurement history: JSON list of snapshots appended on
    # every app save ({date, values{field: num}}), newest first, max 20.
    measure_history_json = fields.Text(default='[]')

    preferred_unit = fields.Selection([
        ('cm',   'Centimeters (cm)'),
        ('inch', 'Inches (in)'),
    ], string='Preferred unit', default='cm',
       help='How measurements are displayed to you. '
            'Storage stays in cm regardless.')

    # ── Virtual Try-On source photo ──────────────────────────────────────────
    tryon_photo          = fields.Binary(string='صورة Try-On', attachment=True)
    tryon_photo_filename = fields.Char(string='اسم ملف الصورة')
    tryon_photo_uploaded = fields.Datetime(string='تاريخ رفع الصورة')

    # ── Learning from history ─────────────────────────────────────────────────
    fit_history_ids = fields.One2many(
        'customer.fit.history', 'profile_id', string='سجل المقاسات'
    )
    profile_complete = fields.Boolean(
        compute='_compute_complete', store=True, string='الملف مكتمل'
    )
    completion_pct = fields.Integer(
        compute='_compute_complete', store=True, string='نسبة الاكتمال %'
    )

    @api.depends('height', 'weight', 'chest', 'waist', 'shoulder', 'shoe_size_eu')
    def _compute_complete(self):
        required = ['height', 'weight', 'chest', 'waist', 'shoulder']
        for rec in self:
            filled = sum(1 for f in required if getattr(rec, f, 0) > 0)
            rec.completion_pct  = int(filled / len(required) * 100)
            rec.profile_complete = rec.completion_pct >= 80

    def to_dict(self):
        return {
            'id':            self.id,
            'height':        self.height,
            'weight':        self.weight,
            'body_type':     self.body_type,
            'gender':        self.gender,
            'shoulder':      self.shoulder,
            'chest':         self.chest,
            'waist':         self.waist,
            'hip':           self.hip,
            'arm_length':    self.arm_length,
            'inseam':        self.inseam,
            'thigh':         self.thigh,
            'shoe_size_eu':  self.shoe_size_eu,
            'shoe_size_us':  self.shoe_size_us,
            'shoe_width':    self.shoe_width,
            'preferred_fit': self.preferred_fit,
            'complete':      self.profile_complete,
            'completion':    self.completion_pct,
            'has_tryon_photo': bool(self.tryon_photo),
        }


class CustomerFitHistory(models.Model):
    _name        = 'customer.fit.history'
    _description = 'Customer Fit Feedback History'
    _order       = 'create_date desc'

    profile_id  = fields.Many2one('customer.body.profile', ondelete='cascade')
    partner_id  = fields.Many2one('res.partner', related='profile_id.partner_id',
                                  store=True, index=True)
    product_id  = fields.Many2one('product.template', string='المنتج', index=True)
    size_chosen = fields.Char(string='المقاس المختار')

    fit_result  = fields.Selection([
        ('perfect',   'مناسب تماماً'),
        ('too_small', 'ضيق'),
        ('too_large', 'واسع'),
        ('too_long',  'طويل'),
        ('too_short', 'قصير'),
    ], string='نتيجة القصة')

    # ── Per-area verdict (computed snapshot at the time of the check) ────
    AREA_VALUES = [
        ('tight',       'ضيق'),
        ('comfortable', 'مريح'),
        ('loose',       'واسع'),
        ('unknown',     'غير معروف'),
    ]
    chest_fit    = fields.Selection(AREA_VALUES, string='الصدر')
    waist_fit    = fields.Selection(AREA_VALUES, string='الوسط')
    hip_fit      = fields.Selection(AREA_VALUES, string='الورك')
    shoulder_fit = fields.Selection(AREA_VALUES, string='الكتف')
    length_fit   = fields.Selection(AREA_VALUES, string='الطول')
    sleeve_fit   = fields.Selection(AREA_VALUES, string='الكم')
    inseam_fit   = fields.Selection(AREA_VALUES, string='الساق')

    chest_diff_cm    = fields.Float(string='فرق الصدر (cm)')
    waist_diff_cm    = fields.Float(string='فرق الوسط (cm)')
    hip_diff_cm      = fields.Float(string='فرق الورك (cm)')
    shoulder_diff_cm = fields.Float(string='فرق الكتف (cm)')
    length_diff_cm   = fields.Float(string='فرق الطول (cm)')
    sleeve_diff_cm   = fields.Float(string='فرق الكم (cm)')
    inseam_diff_cm   = fields.Float(string='فرق الساق (cm)')

    overall_match_pct = fields.Integer(string='نسبة التوافق %')

    # ── Source/category metadata ─────────────────────────────────────────
    category    = fields.Char(string='فئة المنتج')
    source      = fields.Selection([
        ('beena_check', 'فحص بينا'),
        ('purchase',    'بعد الشراء'),
        ('manual',      'يدوي'),
    ], default='beena_check')

    details_json = fields.Text(string='تفاصيل (JSON)',
                               help='Per-area diffs + raw analyzer output snapshot.')

    notes       = fields.Text(string='ملاحظات')
    order_id    = fields.Many2one('sale.order', string='الطلب')
