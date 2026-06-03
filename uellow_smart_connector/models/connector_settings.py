from odoo import models, fields, api, _

# Centralised list of (field, ICP key, default, type) tuples — single source
# of truth so default_get / get_settings / action_save can't drift.
_PARAMS = [
    # field name              ICP key                          default                                  type
    ('anthropic_api_key',     'uellow.sc.anthropic_key',       '',                                       str),
    ('default_warranty_text', 'uellow.sc.warranty',            'ضمان Uellow سنة كاملة — توصيل خلال 24 ساعة', str),
    ('default_price_variance','uellow.sc.price_variance',      20.0,                                     float),
    ('enable_ai_default',     'uellow.sc.enable_ai_default',   True,                                     bool),
    ('max_products_default',  'uellow.sc.max_products_default',500,                                      int),
    ('price_check_enabled',   'uellow.sc.price_check',         True,                                     bool),
    ('internal_price_watch',  'uellow.sc.internal_price_watch',True,                                     bool),
    ('price_check_sources',   'uellow.sc.price_sources',       '',                                       str),
    ('dead_stock_days',       'uellow.sc.dead_stock_days',     30,                                       int),
    ('dead_stock_alert_email','uellow.sc.dead_stock_email',    True,                                     bool),
]


def _coerce(val, typ, default):
    """Parse an ICP string into the target python type, falling back to default."""
    if val in (None, ''):
        return default
    try:
        if typ is bool:
            return str(val).strip().lower() in ('1', 'true', 'yes', 'on')
        if typ is int:
            return int(val)
        if typ is float:
            return float(val)
        return str(val)
    except (TypeError, ValueError):
        return default


class ConnectorSettings(models.TransientModel):
    """
    Global Smart Connector settings stored via ir.config_parameter.

    Bugfix history:
      - A11: `default_get` ignored 4 fields and `action_save` ignored the
        same 4; they're now driven from `_PARAMS` so adding a setting needs
        one line, not three.
      - D11: form wouldn't close after save; we now return an action_close.
    """
    _name = 'uellow.connector.settings'
    _description = 'إعدادات Smart Connector'

    anthropic_api_key = fields.Char('Anthropic API Key')
    default_warranty_text = fields.Char(
        'نص الضمان الافتراضي',
        default='ضمان Uellow سنة كاملة — توصيل خلال 24 ساعة',
    )
    default_price_variance = fields.Float('حد تغير السعر الافتراضي (%)', default=20.0)
    enable_ai_default = fields.Boolean('تفعيل AI بشكل افتراضي', default=True)
    max_products_default = fields.Integer('أقصى عدد منتجات افتراضي', default=500)

    # Price Intelligence settings
    price_check_enabled = fields.Boolean('تفعيل مراقبة الأسعار', default=True)
    internal_price_watch = fields.Boolean('مراقبة أسعارنا الداخلية (سجل + مؤشرات)', default=True)
    price_check_sources = fields.Char(
        'مصادر المقارنة (URLs مفصولة بفاصلة)',
    )

    # Dead stock settings
    dead_stock_days = fields.Integer('أيام الركود للتحذير', default=30)
    dead_stock_alert_email = fields.Boolean('إرسال تنبيه بريد إلكتروني', default=True)

    @api.model
    def default_get(self, fields_list):
        """Pre-fill form with current saved values."""
        res = super().default_get(fields_list)
        ICPSudo = self.env['ir.config_parameter'].sudo()
        for field_name, key, default, typ in _PARAMS:
            res[field_name] = _coerce(ICPSudo.get_param(key), typ, default)
        return res

    @api.model
    def get_settings(self):
        """Return current settings as a plain dict (used by other models)."""
        ICPSudo = self.env['ir.config_parameter'].sudo()
        return {
            field_name: _coerce(ICPSudo.get_param(key), typ, default)
            for field_name, key, default, typ in _PARAMS
        }

    def action_save(self):
        """Persist every setting to ir_config_parameter and close the dialog."""
        ICPSudo = self.env['ir.config_parameter'].sudo()
        for field_name, key, _default, typ in _PARAMS:
            val = getattr(self, field_name, None)
            if typ is bool:
                ICPSudo.set_param(key, '1' if val else '0')
            elif val is False or val is None:
                ICPSudo.set_param(key, '')
            else:
                ICPSudo.set_param(key, str(val))
        # Notify + close — D11 fix.
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('تم الحفظ'),
                'message': _('تم حفظ إعدادات Smart Connector.'),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
