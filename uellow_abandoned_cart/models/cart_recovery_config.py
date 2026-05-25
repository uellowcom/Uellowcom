from odoo import models, fields, api, _


class CartRecoveryConfig(models.Model):
    """Global config for abandoned cart recovery sequences."""
    _name = 'uellow.cart.recovery.config'
    _description = 'Cart Recovery Configuration'
    _rec_name = 'name'

    name = fields.Char(default='Cart Recovery Settings')
    active = fields.Boolean(default=True)

    # Step 1
    step1_enabled = fields.Boolean('Step 1 Enabled', default=True)
    step1_delay_hours = fields.Integer('Step 1 Delay (hours)', default=1)
    step1_channel = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Email'),
    ], default='whatsapp', string='Step 1 Channel')
    step1_message = fields.Text(
        'Step 1 Message',
        default='لا تزال منتجاتك تنتظرك! أكمل طلبك الآن.',
    )
    step1_offer_discount = fields.Boolean('Offer Discount in Step 1', default=False)
    step1_discount_pct = fields.Float('Step 1 Discount (%)', default=0.0)

    # Step 2
    step2_enabled = fields.Boolean('Step 2 Enabled', default=True)
    step2_delay_hours = fields.Integer('Step 2 Delay (hours)', default=24)
    step2_channel = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Email'),
    ], default='email', string='Step 2 Channel')
    step2_message = fields.Text(
        'Step 2 Message',
        default='منتجاتك لا تزال هنا! خصم خاص 5% لك.',
    )
    step2_offer_discount = fields.Boolean('Offer Discount in Step 2', default=True)
    step2_discount_pct = fields.Float('Step 2 Discount (%)', default=5.0)

    # Step 3
    step3_enabled = fields.Boolean('Step 3 Enabled', default=True)
    step3_delay_hours = fields.Integer('Step 3 Delay (hours)', default=48)
    step3_channel = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Email'),
    ], default='whatsapp', string='Step 3 Channel')
    step3_message = fields.Text(
        'Step 3 Message',
        default='آخر فرصة! المخزون أوشك على النفاد.',
    )
    step3_offer_discount = fields.Boolean('Offer Discount in Step 3', default=True)
    step3_discount_pct = fields.Float('Step 3 Discount (%)', default=10.0)

    # Limits
    max_reminders = fields.Integer('Max Reminders per Cart', default=3)
    exclude_converted = fields.Boolean('Exclude Converted Customers', default=True)
    min_cart_value = fields.Float('Minimum Cart Value (KD)', default=5.0)

    @api.model
    def get_config(self):
        cfg = self.search([], limit=1)
        if not cfg:
            cfg = self.create({'name': 'Cart Recovery Settings'})
        return cfg
