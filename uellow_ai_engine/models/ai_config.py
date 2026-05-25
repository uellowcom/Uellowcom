from odoo import models, fields, api


class AiConfig(models.TransientModel):
    _name = 'ai.config.settings'
    _description = 'Beena AI Settings'

    # ── Identity ──────────────────────────────────────────
    ai_enabled = fields.Boolean(string='تفعيل Beena', default=True)
    ai_assistant_name = fields.Char(string='اسم المساعد', default='Beena')
    ai_assistant_subtitle = fields.Char(string='العنوان التوضيحي', default='مساعدة Uellow الذكية')
    ai_welcome_message = fields.Char(
        string='رسالة الترحيب',
        default='أهلاً! أنا Beena 🐝 كيف أقدر أساعدك اليوم؟',
    )
    ai_button_color = fields.Char(string='لون الزر', default='#F5C320')

    # ── Claude API ────────────────────────────────────────
    ai_claude_api_key = fields.Char(string='Claude API Key')
    ai_claude_model = fields.Selection([
        ('claude-sonnet-4-6',          'Claude Sonnet 4.6 (موصى به)'),
        ('claude-opus-4-6',            'Claude Opus 4.6 (أقوى)'),
        ('claude-haiku-4-5-20251001',  'Claude Haiku 4.5 (أسرع)'),
    ], string='نموذج Claude', default='claude-sonnet-4-6')
    ai_max_tokens = fields.Integer(string='Max Tokens', default=1024)

    # ── Behaviour ─────────────────────────────────────────
    ai_float_button = fields.Boolean(string='زر Float في كل الصفحات', default=True)
    ai_buy_with_ai = fields.Boolean(string='زر Buy with AI', default=True)
    ai_proactive_nudge = fields.Boolean(string='Proactive Nudge', default=True)
    ai_nudge_delay = fields.Integer(string='تأخير Nudge (ثانية)', default=30)
    ai_default_language = fields.Selection([
        ('auto', 'تلقائي حسب العميل'),
        ('ar',   'عربي دائماً'),
        ('en',   'إنجليزي دائماً'),
    ], string='لغة الرد', default='auto')
    ai_session_ttl = fields.Integer(string='مدة حفظ الجلسة (ساعة)', default=24)
    ai_max_upsell = fields.Integer(string='حد الـ Upsell', default=3)

    # ── Web Search ────────────────────────────────────────
    ai_web_search_enabled = fields.Boolean(string='تفعيل Web Search', default=False)
    ai_cod_enabled = fields.Boolean(string='الدفع عند الاستلام (COD)', default=True)
    ai_brave_api_key = fields.Char(string='Brave Search API Key')

    # ── Helpers ───────────────────────────────────────────
    @api.model
    def _get_param(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param(
            f'uellow_ai.{key}', default
        )

    def _set_param(self, key, value):
        self.env['ir.config_parameter'].sudo().set_param(
            f'uellow_ai.{key}', str(value) if not isinstance(value, str) else value
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        p = self._get_param
        mapping = {
            'ai_enabled':            ('enabled',           True),
            'ai_assistant_name':     ('assistant_name',    'Beena'),
            'ai_assistant_subtitle': ('assistant_subtitle','مساعدة Uellow الذكية'),
            'ai_welcome_message':    ('welcome_message',   'أهلاً! أنا Beena 🐝'),
            'ai_button_color':       ('button_color',      '#F5C320'),
            'ai_claude_api_key':     ('claude_api_key',    ''),
            'ai_claude_model':       ('claude_model',      'claude-sonnet-4-6'),
            'ai_max_tokens':         ('max_tokens',        '1024'),
            'ai_float_button':       ('float_button',      True),
            'ai_buy_with_ai':        ('buy_with_ai',       True),
            'ai_proactive_nudge':    ('proactive_nudge',   True),
            'ai_nudge_delay':        ('nudge_delay',       '30'),
            'ai_default_language':   ('default_language',  'auto'),
            'ai_session_ttl':        ('session_ttl',       '24'),
            'ai_web_search_enabled': ('web_search_enabled',False),
            'ai_cod_enabled':        ('cod_enabled',         True),
            'ai_brave_api_key':      ('brave_api_key',     ''),
        }
        for field, (param, default) in mapping.items():
            if field in fields_list:
                val = p(param, str(default) if not isinstance(default, str) else default)
                # Cast booleans
                if isinstance(default, bool):
                    res[field] = val in ('True', '1', 'true', True)
                elif isinstance(default, int) or field in ('ai_max_tokens', 'ai_nudge_delay', 'ai_session_ttl'):
                    try:
                        res[field] = int(val)
                    except Exception:
                        res[field] = default
                else:
                    res[field] = val
        return res

    def execute(self):
        self._set_param('enabled',            str(self.ai_enabled))
        self._set_param('assistant_name',     self.ai_assistant_name or 'Beena')
        self._set_param('assistant_subtitle', self.ai_assistant_subtitle or '')
        self._set_param('welcome_message',    self.ai_welcome_message or '')
        self._set_param('button_color',       self.ai_button_color or '#F5C320')
        self._set_param('claude_api_key',     self.ai_claude_api_key or '')
        self._set_param('claude_model',       self.ai_claude_model or 'claude-sonnet-4-6')
        self._set_param('max_tokens',         str(self.ai_max_tokens or 1024))
        self._set_param('float_button',       str(self.ai_float_button))
        self._set_param('buy_with_ai',        str(self.ai_buy_with_ai))
        self._set_param('proactive_nudge',    str(self.ai_proactive_nudge))
        self._set_param('nudge_delay',        str(self.ai_nudge_delay or 30))
        self._set_param('default_language',   self.ai_default_language or 'auto')
        self._set_param('session_ttl',        str(self.ai_session_ttl or 24))
        self._set_param('web_search_enabled', str(self.ai_web_search_enabled))
        self._set_param('cod_enabled',         str(self.ai_cod_enabled))
        self._set_param('brave_api_key',      self.ai_brave_api_key or '')
        return {
            'type':  'ir.actions.client',
            'tag':   'display_notification',
            'params': {
                'message': 'تم حفظ إعدادات Beena بنجاح ✓',
                'type':    'success',
                'sticky':  False,
            },
        }

    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}
