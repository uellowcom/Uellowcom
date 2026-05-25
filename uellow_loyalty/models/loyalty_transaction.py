from odoo import models, fields, api


class LoyaltyTransaction(models.Model):
    _name        = 'loyalty.transaction'
    _description = 'Loyalty Points Transaction'
    _order       = 'create_date desc'

    account_id = fields.Many2one('loyalty.account', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one(related='account_id.partner_id', store=True)

    points    = fields.Integer(string='النقاط')  # positive=earn, negative=spend
    type      = fields.Selection([
        ('earn',   'كسب'),
        ('spend',  'صرف'),
        ('expire', 'انتهاء'),
        ('adjust', 'تعديل'),
    ], string='النوع', required=True)

    reason    = fields.Char(string='السبب')
    reference = fields.Char(string='المرجع')
    order_id  = fields.Many2one('sale.order', string='الطلب')

    def to_dict(self):
        return {
            'id':        self.id,
            'points':    self.points,
            'type':      self.type,
            'reason':    self.reason,
            'reference': self.reference,
            'date':      str(self.create_date)[:16] if self.create_date else '',
        }
