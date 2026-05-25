from odoo import models, fields


class PushLog(models.Model):
    _name = 'uellow.push.log'
    _description = 'Push Notification Log'
    _order = 'id desc'

    title = fields.Char()
    body = fields.Text()
    trigger = fields.Char()
    recipients = fields.Integer('Recipients')
    status = fields.Selection([('sent','Sent'),('failed','Failed')], default='sent')
    sent_at = fields.Datetime(default=fields.Datetime.now)
