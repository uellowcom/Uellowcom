from odoo import models, fields, api


class MobileApiSettings(models.TransientModel):
    _name        = 'mobile.api.settings'
    _description = 'Uellow Mobile API Settings'

    # ── General ───────────────────────────────────────────────────────────────
    enabled          = fields.Boolean(string='تفعيل الـ API', default=True)
    api_version      = fields.Char(string='إصدار الـ API', default='v1', readonly=True)
    token_ttl_days   = fields.Integer(string='مدة صلاحية التوكن (يوم)', default=30)
    max_products_per_page = fields.Integer(string='أقصى عدد منتجات في الصفحة', default=50)

    # ── Authentication ────────────────────────────────────────────────────────
    allow_register   = fields.Boolean(string='السماح بالتسجيل من التطبيق', default=True)
    require_email_verify = fields.Boolean(string='التحقق من الإيميل عند التسجيل', default=False)
    welcome_points   = fields.Boolean(string='نقاط ترحيبية عند التسجيل', default=True)

    # ── Push Notifications ────────────────────────────────────────────────────
    fcm_server_key   = fields.Char(string='FCM Server Key (Firebase)')
    push_order_confirm = fields.Boolean(string='إشعار عند تأكيد الطلب', default=True)
    push_order_shipped = fields.Boolean(string='إشعار عند الشحن', default=True)
    push_order_delivered = fields.Boolean(string='إشعار عند التسليم', default=True)
    push_promo       = fields.Boolean(string='إشعارات العروض والخصومات', default=True)
    push_reviewer    = fields.Boolean(string='إشعار رد الريفيور', default=True)
    push_loyalty     = fields.Boolean(string='إشعار نقاط الولاء', default=True)

    # ── CORS & Security ───────────────────────────────────────────────────────
    cors_origins     = fields.Char(
        string='CORS Origins المسموح بها',
        default='*',
        help='* للسماح بالكل، أو ضع الـ domains مفصولة بفاصلة',
    )
    rate_limit_enabled = fields.Boolean(string='تفعيل Rate Limiting', default=False)
    rate_limit_per_min = fields.Integer(string='الحد الأقصى للطلبات/دقيقة', default=60)

    # ── App Config ────────────────────────────────────────────────────────────
    app_store_url    = fields.Char(string='رابط App Store')
    play_store_url   = fields.Char(string='رابط Play Store')
    min_app_version  = fields.Char(string='أدنى إصدار مدعوم', default='1.0.0')
    maintenance_mode = fields.Boolean(string='وضع الصيانة', default=False)
    maintenance_msg  = fields.Char(
        string='رسالة الصيانة',
        default='التطبيق في وضع الصيانة، يرجى المحاولة لاحقاً',
    )

    # ── Home Screen ───────────────────────────────────────────────────────────
    home_new_arrivals_count = fields.Integer(string='عدد الوصول الجديد في الرئيسية', default=10)
    home_best_sellers_count = fields.Integer(string='عدد الأكثر مبيعاً في الرئيسية', default=10)
    home_categories_count   = fields.Integer(string='عدد الفئات في الرئيسية', default=8)

    # ── Active tokens count (readonly) ───────────────────────────────────────
    active_tokens_count = fields.Integer(
        string='التوكنات النشطة',
        compute='_compute_active_tokens',
    )

    @api.depends()
    def _compute_active_tokens(self):
        for rec in self:
            count = self.env['ir.config_parameter'].sudo().search_count(
                [('key', 'like', 'mobile_token_')]
            )
            rec.active_tokens_count = count

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _get(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param(
            f'uellow_mobile_api.{key}', default
        )

    def _set(self, key, value):
        self.env['ir.config_parameter'].sudo().set_param(
            f'uellow_mobile_api.{key}',
            str(value) if not isinstance(value, str) else value
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        p = self._get
        mapping = {
            'enabled':              ('enabled',              'True'),
            'token_ttl_days':       ('token_ttl_days',       '30'),
            'max_products_per_page':('max_products_per_page','50'),
            'allow_register':       ('allow_register',       'True'),
            'require_email_verify': ('require_email_verify', 'False'),
            'welcome_points':       ('welcome_points',       'True'),
            'fcm_server_key':       ('fcm_server_key',       ''),
            'push_order_confirm':   ('push_order_confirm',   'True'),
            'push_order_shipped':   ('push_order_shipped',   'True'),
            'push_order_delivered': ('push_order_delivered', 'True'),
            'push_promo':           ('push_promo',           'True'),
            'push_reviewer':        ('push_reviewer',        'True'),
            'push_loyalty':         ('push_loyalty',         'True'),
            'cors_origins':         ('cors_origins',         '*'),
            'rate_limit_enabled':   ('rate_limit_enabled',   'False'),
            'rate_limit_per_min':   ('rate_limit_per_min',   '60'),
            'app_store_url':        ('app_store_url',        ''),
            'play_store_url':       ('play_store_url',       ''),
            'min_app_version':      ('min_app_version',      '1.0.0'),
            'maintenance_mode':     ('maintenance_mode',     'False'),
            'maintenance_msg':      ('maintenance_msg',      'التطبيق في وضع الصيانة'),
            'home_new_arrivals_count': ('home_new_arrivals', '10'),
            'home_best_sellers_count': ('home_best_sellers', '10'),
            'home_categories_count':   ('home_categories',   '8'),
        }
        for field, (param, default) in mapping.items():
            if field in fields_list:
                val = p(param, default)
                f   = self._fields[field]
                if f.type == 'boolean':
                    res[field] = val in ('True', '1', 'true')
                elif f.type == 'integer':
                    try: res[field] = int(val)
                    except: res[field] = 0
                else:
                    res[field] = val
        return res

    def execute(self):
        self._set('enabled',              str(self.enabled))
        self._set('token_ttl_days',       str(self.token_ttl_days))
        self._set('max_products_per_page',str(self.max_products_per_page))
        self._set('allow_register',       str(self.allow_register))
        self._set('require_email_verify', str(self.require_email_verify))
        self._set('welcome_points',       str(self.welcome_points))
        self._set('fcm_server_key',       self.fcm_server_key or '')
        self._set('push_order_confirm',   str(self.push_order_confirm))
        self._set('push_order_shipped',   str(self.push_order_shipped))
        self._set('push_order_delivered', str(self.push_order_delivered))
        self._set('push_promo',           str(self.push_promo))
        self._set('push_reviewer',        str(self.push_reviewer))
        self._set('push_loyalty',         str(self.push_loyalty))
        self._set('cors_origins',         self.cors_origins or '*')
        self._set('rate_limit_enabled',   str(self.rate_limit_enabled))
        self._set('rate_limit_per_min',   str(self.rate_limit_per_min))
        self._set('app_store_url',        self.app_store_url or '')
        self._set('play_store_url',       self.play_store_url or '')
        self._set('min_app_version',      self.min_app_version or '1.0.0')
        self._set('maintenance_mode',     str(self.maintenance_mode))
        self._set('maintenance_msg',      self.maintenance_msg or '')
        self._set('home_new_arrivals',    str(self.home_new_arrivals_count))
        self._set('home_best_sellers',    str(self.home_best_sellers_count))
        self._set('home_categories',      str(self.home_categories_count))
        return {
            'type':   'ir.actions.client',
            'tag':    'display_notification',
            'params': {
                'message': 'تم حفظ إعدادات Mobile API بنجاح ✓',
                'type':    'success',
                'sticky':  False,
            },
        }

    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_revoke_all_tokens(self):
        """Revoke all active mobile tokens."""
        params = self.env['ir.config_parameter'].sudo().search(
            [('key', 'like', 'mobile_token_')]
        )
        count = len(params)
        params.unlink()
        return {
            'type':   'ir.actions.client',
            'tag':    'display_notification',
            'params': {
                'message': f'تم إلغاء {count} توكن نشط',
                'type':    'warning',
                'sticky':  False,
            },
        }

    def action_test_push(self):
        """Send a test push notification to the current user."""
        partner_id = self.env.user.partner_id.id
        key        = f'push_token_{partner_id}'
        token      = self.env['ir.config_parameter'].sudo().get_param(key)
        if not token:
            return {
                'type':   'ir.actions.client',
                'tag':    'display_notification',
                'params': {'message': 'لا يوجد device مسجّل لهذا الحساب', 'type': 'warning', 'sticky': False},
            }
        # Import and call helper
        try:
            from odoo.addons.uellow_mobile_api.controllers.api_controller import _send_push_notification
            sent = _send_push_notification(
                self.env, partner_id,
                'Beena 🐝 — اختبار الإشعارات',
                'الإشعارات تعمل بنجاح! 🎉',
                {'type': 'test'},
            )
            msg = 'تم إرسال الإشعار بنجاح ✓' if sent else 'FCM Key غير محدد'
        except Exception as e:
            msg = str(e)
        return {
            'type':   'ir.actions.client',
            'tag':    'display_notification',
            'params': {'message': msg, 'type': 'success', 'sticky': False},
        }
