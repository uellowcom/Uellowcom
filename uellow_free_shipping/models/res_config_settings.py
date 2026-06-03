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
