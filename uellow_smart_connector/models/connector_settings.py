from odoo import models, fields, api, _


class ConnectorSettings(models.TransientModel):
    """
    Global Smart Connector settings stored via ir.config_parameter.
    Accessed via res.config.settings extension.
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
        res['anthropic_api_key'] = ICPSudo.get_param('uellow.sc.anthropic_key', '')
        res['default_warranty_text'] = ICPSudo.get_param(
            'uellow.sc.warranty',
            'ضمان Uellow سنة كاملة — توصيل خلال 24 ساعة')
        res['default_price_variance'] = float(
            ICPSudo.get_param('uellow.sc.price_variance', '20'))
        res['price_check_enabled'] = (
            ICPSudo.get_param('uellow.sc.price_check', 'True') == 'True')
        res['dead_stock_days'] = int(
            ICPSudo.get_param('uellow.sc.dead_stock_days', '30'))
        return res

    @api.model
    def get_settings(self):
        """Return settings dict from ir.config_parameter."""
        ICPSudo = self.env['ir.config_parameter'].sudo()
        return {
            'anthropic_api_key': ICPSudo.get_param('uellow.sc.anthropic_key', ''),
            'default_warranty': ICPSudo.get_param(
                'uellow.sc.warranty',
                'ضمان Uellow سنة كاملة — توصيل خلال 24 ساعة',
            ),
            'price_variance': float(ICPSudo.get_param('uellow.sc.price_variance', '20')),
            'price_check_enabled': ICPSudo.get_param('uellow.sc.price_check', 'True') == 'True',
            'dead_stock_days': int(ICPSudo.get_param('uellow.sc.dead_stock_days', '30')),
        }

    def action_save(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param('uellow.sc.anthropic_key', self.anthropic_api_key or '')
        ICPSudo.set_param('uellow.sc.warranty', self.default_warranty_text or '')
        ICPSudo.set_param('uellow.sc.price_variance', str(self.default_price_variance))
        ICPSudo.set_param('uellow.sc.price_check', str(self.price_check_enabled))
        ICPSudo.set_param('uellow.sc.dead_stock_days', str(self.dead_stock_days))
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'message': _('تم الحفظ'), 'type': 'success'}}
