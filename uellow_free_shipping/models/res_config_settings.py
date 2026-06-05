from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    free_shipping_threshold_kwd = fields.Float(
        string='Global free-shipping threshold (KWD)',
        config_parameter='uellow_free_shipping.threshold_kwd',
        help='Orders whose subtotal is greater-equal this amount ship '
             'free regardless of product-level flags. 0 disables.',
    )
    free_shipping_badge_label_en = fields.Char(
        string='Badge label (EN)',
        config_parameter='uellow_free_shipping.badge_label_en',
        default='Free shipping',
    )
    free_shipping_badge_label_ar = fields.Char(
        string='Badge label (AR)',
        config_parameter='uellow_free_shipping.badge_label_ar',
        default='شحن مجاني',
    )
    free_shipping_express_excluded = fields.Boolean(
        string='Exclude EXPRESS delivery from free shipping',
        config_parameter='uellow_free_shipping.express_excluded',
        default=True,
        help='When ON, express carriers (flagged "Express Service" on the '
             'delivery method, or auto-detected by name) ALWAYS keep their '
             'price — free-shipping flags, thresholds, coupons and the cart '
             'progress bar apply to standard delivery only.',
    )
    free_shipping_product_rule = fields.Selection([
        ('any', 'ANY flagged product in the cart → free shipping'),
        ('all', 'ALL cart products must be flagged → free shipping'),
        ('off', 'Product flags affect badges only (no free delivery)'),
    ], string='Product-flag rule',
        config_parameter='uellow_free_shipping.product_rule',
        default='any',
        help='How product-level free-shipping flags translate into a free '
             'delivery at checkout.',
    )
