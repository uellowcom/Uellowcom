from odoo import models, fields, api


class ReturnConfig(models.Model):
    _name = 'uellow.return.config'
    _description = 'Return Policy Configuration'

    name = fields.Char(default='Return Policy')
    return_window_days = fields.Integer('Return Window (days)', default=7)
    require_photo = fields.Boolean('Require Photo', default=True)
    auto_approve_threshold = fields.Float('Auto-approve if order < (KD)', default=10.0)
    restocking_fee_pct = fields.Float('Restocking Fee (%)', default=0.0)
    refund_method = fields.Selection([
        ('wallet',   'Store Wallet'),
        ('original', 'Original Payment Method'),
        ('voucher',  'Voucher'),
    ], default='wallet')
    non_returnable_categories = fields.Many2many('product.category', string='Non-returnable Categories')

    @api.model
    def get_config(self):
        cfg = self.search([], limit=1)
        if not cfg:
            cfg = self.create({})
        return cfg
