from odoo import models, fields


class WhatsAppLog(models.Model):
    _name = 'uellow.whatsapp.log'
    _description = 'WhatsApp Message Log'
    _order = 'id desc'

    partner_id = fields.Many2one('res.partner', ondelete='set null')
    phone = fields.Char('Phone')
    message = fields.Text('Message')
    trigger = fields.Char('Trigger')
    status = fields.Selection([('sent','Sent'),('failed','Failed')], default='sent')
    sent_at = fields.Datetime(default=fields.Datetime.now)
    order_id = fields.Many2one('sale.order', ondelete='set null')
