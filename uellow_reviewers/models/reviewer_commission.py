from odoo import models, fields, api


class ReviewerCommission(models.Model):
    _name        = 'reviewer.commission'
    _description = 'Reviewer Commission Payout'
    _order       = 'create_date desc'

    reviewer_id  = fields.Many2one('reviewer.profile', required=True, ondelete='cascade')
    period_start = fields.Date(string='من')
    period_end   = fields.Date(string='إلى')
    amount       = fields.Float(string='المبلغ (KD)')
    state        = fields.Selection([
        ('pending', 'معلق'),
        ('paid',    'مدفوع'),
    ], default='pending')
    paid_date    = fields.Date(string='تاريخ الدفع')
    notes        = fields.Text()

    request_ids  = fields.Many2many(
        'review.request',
        'commission_request_rel',
        'commission_id', 'request_id',
        string='الجلسات',
    )
    request_count = fields.Integer(
        compute='_compute_request_count', string='عدد الجلسات'
    )

    @api.depends('request_ids')
    def _compute_request_count(self):
        for rec in self:
            rec.request_count = len(rec.request_ids)

    def action_mark_paid(self):
        self.write({'state': 'paid', 'paid_date': fields.Date.today()})
        # Deduct from wallet
        self.reviewer_id.wallet_balance -= self.amount


class ReviewerSettings(models.TransientModel):
    _name        = 'reviewer.settings'
    _description = 'Reviewer System Settings'

    # ── Master switch ─────────────────────────────────────────────────────────
    enabled = fields.Boolean(string='تفعيل نظام الريفيورز', default=True)

    # ── Session types ─────────────────────────────────────────────────────────
    allow_written = fields.Boolean(string='رأي مكتوب', default=True)
    allow_chat    = fields.Boolean(string='شات مباشر', default=True)
    allow_photo   = fields.Boolean(string='صورة + رأي', default=True)
    allow_video   = fields.Boolean(string='مكالمة فيديو', default=False)

    # ── Limits ────────────────────────────────────────────────────────────────
    max_reviewers_per_request = fields.Integer(string='الحد الأقصى للريفيورز', default=5)
    request_expiry_minutes    = fields.Integer(string='انتهاء صلاحية الطلب (دقيقة)', default=10)
    chat_duration_minutes     = fields.Integer(string='مدة الشات المباشر (دقيقة)', default=15)

    # ── Commission ────────────────────────────────────────────────────────────
    commission_written   = fields.Float(string='عمولة رأي مكتوب %', default=5.0)
    commission_chat      = fields.Float(string='عمولة شات مباشر %', default=8.0)
    commission_bonus_1h  = fields.Float(string='بونص شراء خلال ساعة %', default=2.0)
    commission_window_h  = fields.Integer(string='نافذة احتساب العمولة (ساعة)', default=24)
    min_payout           = fields.Float(string='الحد الأدنى للصرف (KD)', default=5.0)
    payout_cycle         = fields.Selection([
        ('weekly',  'أسبوعياً'),
        ('monthly', 'شهرياً'),
        ('manual',  'يدوي'),
    ], default='monthly', string='دورة الصرف')

    # ── Protection ────────────────────────────────────────────────────────────
    require_approval       = fields.Boolean(string='موافقة يدوية على الريفيورز الجدد', default=True)
    require_verified_purchase = fields.Boolean(string='اشتراط Verified Purchase', default=True)
    auto_suspend_complaints = fields.Integer(string='إيقاف تلقائي عند عدد الشكاوى', default=3)
    share_tryon_with_reviewer = fields.Boolean(string='مشاركة Try-On مع الريفيور', default=True)

    @api.model
    def _get_param(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param(
            f'uellow_reviewers.{key}', default
        )

    def _set_param(self, key, value):
        self.env['ir.config_parameter'].sudo().set_param(
            f'uellow_reviewers.{key}',
            str(value) if not isinstance(value, str) else value
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        p = self._get_param
        mapping = {
            'enabled':                    ('enabled', 'True'),
            'allow_written':              ('allow_written', 'True'),
            'allow_chat':                 ('allow_chat', 'True'),
            'allow_photo':                ('allow_photo', 'True'),
            'allow_video':                ('allow_video', 'False'),
            'max_reviewers_per_request':  ('max_reviewers', '5'),
            'request_expiry_minutes':     ('request_expiry', '10'),
            'chat_duration_minutes':      ('chat_duration', '15'),
            'commission_written':         ('commission_written', '5.0'),
            'commission_chat':            ('commission_chat', '8.0'),
            'commission_bonus_1h':        ('commission_bonus_1h', '2.0'),
            'commission_window_h':        ('commission_window_h', '24'),
            'min_payout':                 ('min_payout', '5.0'),
            'payout_cycle':               ('payout_cycle', 'monthly'),
            'require_approval':           ('require_approval', 'True'),
            'require_verified_purchase':  ('require_verified_purchase', 'True'),
            'auto_suspend_complaints':    ('auto_suspend_complaints', '3'),
            'share_tryon_with_reviewer':  ('share_tryon', 'True'),
        }
        for field, (param, default) in mapping.items():
            if field in fields_list:
                val = p(param, default)
                f   = self._fields[field]
                if f.type == 'boolean':
                    res[field] = val in ('True', '1', 'true')
                elif f.type in ('integer',):
                    try: res[field] = int(float(val))
                    except: res[field] = int(default) if default.isdigit() else 0
                elif f.type == 'float':
                    try: res[field] = float(val)
                    except: res[field] = 0.0
                else:
                    res[field] = val
        return res

    def execute(self):
        self._set_param('enabled',                   str(self.enabled))
        self._set_param('allow_written',             str(self.allow_written))
        self._set_param('allow_chat',                str(self.allow_chat))
        self._set_param('allow_photo',               str(self.allow_photo))
        self._set_param('allow_video',               str(self.allow_video))
        self._set_param('max_reviewers',             str(self.max_reviewers_per_request))
        self._set_param('request_expiry',            str(self.request_expiry_minutes))
        self._set_param('chat_duration',             str(self.chat_duration_minutes))
        self._set_param('commission_written',        str(self.commission_written))
        self._set_param('commission_chat',           str(self.commission_chat))
        self._set_param('commission_bonus_1h',       str(self.commission_bonus_1h))
        self._set_param('commission_window_h',       str(self.commission_window_h))
        self._set_param('min_payout',                str(self.min_payout))
        self._set_param('payout_cycle',              self.payout_cycle)
        self._set_param('require_approval',          str(self.require_approval))
        self._set_param('require_verified_purchase', str(self.require_verified_purchase))
        self._set_param('auto_suspend_complaints',   str(self.auto_suspend_complaints))
        self._set_param('share_tryon',               str(self.share_tryon_with_reviewer))
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'message': 'تم حفظ إعدادات الريفيورز ✓', 'type': 'success', 'sticky': False},
        }

    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}
