from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    whatsapp_sent = fields.Boolean('WhatsApp Confirmation Sent', default=False)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            try:
                config = self.env['uellow.whatsapp.config'].sudo().get_config()
                if config.active and config.send_order_confirm:
                    phone = order.partner_id.mobile or order.partner_id.phone
                    if phone:
                        msg = f'✅ طلبك #{order.name} تم تأكيده!\nالإجمالي: {order.amount_total:.3f} KD\nشكراً لك — Uellow'
                        ok = config.send_message(phone, msg)
                        self.env['uellow.whatsapp.log'].sudo().create({
                            'partner_id': order.partner_id.id,
                            'phone': phone, 'message': msg,
                            'trigger': 'order_confirm',
                            'status': 'sent' if ok else 'failed',
                            'order_id': order.id,
                        })
                        order.whatsapp_sent = ok
            except Exception as e:
                _logger.error('WhatsApp order confirm failed: %s', e)
        return res
