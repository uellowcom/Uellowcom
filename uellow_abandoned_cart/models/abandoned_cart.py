from odoo import models, fields, api, _
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)


class AbandonedCart(models.Model):
    """
    Tracks abandoned website.sale carts (sale orders in 'draft' with items).
    Sends recovery sequences automatically.
    """
    _name = 'uellow.abandoned.cart'
    _description = 'Abandoned Cart'
    _rec_name = 'partner_id'
    _order = 'abandoned_at desc'

    order_id = fields.Many2one(
        'sale.order', required=True, ondelete='cascade', index=True,
    )
    partner_id = fields.Many2one(
        related='order_id.partner_id', store=True,
    )
    cart_value = fields.Float(
        compute='_compute_cart_value', store=True, string='Cart Value',
    )
    currency_id = fields.Many2one(
        'res.currency', compute='_compute_cart_value', store=True,
    )

    @api.depends('order_id.amount_total', 'order_id.currency_id')
    def _compute_cart_value(self):
        for rec in self:
            rec.cart_value = rec.order_id.amount_total if rec.order_id else 0.0
            rec.currency_id = rec.order_id.currency_id if rec.order_id else False
    abandoned_at = fields.Datetime('Abandoned At', default=fields.Datetime.now)

    state = fields.Selection([
        ('pending',   'Pending'),
        ('step1_sent','Step 1 Sent'),
        ('step2_sent','Step 2 Sent'),
        ('step3_sent','Step 3 Sent'),
        ('recovered', 'Recovered'),
        ('expired',   'Expired'),
        ('excluded',  'Excluded'),
    ], default='pending', string='Status', index=True)

    reminders_sent = fields.Integer('Reminders Sent', default=0)
    last_reminder = fields.Datetime('Last Reminder Sent')
    recovered_at = fields.Datetime('Recovered At')
    recovery_order_id = fields.Many2one(
        'sale.order', string='Recovery Order', ondelete='set null',
    )

    discount_offered = fields.Float('Discount Offered (%)', default=0.0)
    discount_code = fields.Char('Discount Code')

    def action_mark_recovered(self):
        self.state = 'recovered'
        self.recovered_at = fields.Datetime.now()

    def action_exclude(self):
        self.state = 'excluded'

    @api.model
    def cron_detect_abandoned(self):
        """Hourly cron: find draft orders with items abandoned > 30 min."""
        cutoff = fields.Datetime.now() - timedelta(minutes=30)
        draft_orders = self.env['sale.order'].search([
            ('state', '=', 'draft'),
            ('website_id', '!=', False),
            ('write_date', '<', cutoff),
            ('order_line', '!=', False),
        ])
        config = self.env['uellow.cart.recovery.config'].get_config()
        for order in draft_orders:
            if not order.partner_id or order.partner_id.id == self.env.ref(
                    'base.public_partner', raise_if_not_found=False
            ).id if self.env.ref('base.public_partner', raise_if_not_found=False) else False:
                continue
            if order.amount_total < config.min_cart_value:
                continue
            existing = self.search([('order_id', '=', order.id)], limit=1)
            if not existing:
                self.create({
                    'order_id': order.id,
                    'abandoned_at': order.write_date,
                })

    @api.model
    def cron_send_recovery(self):
        """Hourly cron: send recovery messages based on step schedule."""
        config = self.env['uellow.cart.recovery.config'].get_config()
        if not config.active:
            return
        now = fields.Datetime.now()
        pending = self.search([('state', 'in', ('pending', 'step1_sent', 'step2_sent'))])

        for cart in pending:
            hours_since = (now - cart.abandoned_at).total_seconds() / 3600

            if cart.state == 'pending' and config.step1_enabled:
                if hours_since >= config.step1_delay_hours:
                    cart._send_recovery_message(1, config)
                    cart.state = 'step1_sent'
                    cart.reminders_sent += 1
                    cart.last_reminder = now

            elif cart.state == 'step1_sent' and config.step2_enabled:
                if hours_since >= config.step2_delay_hours:
                    cart._send_recovery_message(2, config)
                    cart.state = 'step2_sent'
                    cart.reminders_sent += 1
                    cart.last_reminder = now

            elif cart.state == 'step2_sent' and config.step3_enabled:
                if hours_since >= config.step3_delay_hours:
                    cart._send_recovery_message(3, config)
                    cart.state = 'step3_sent'
                    cart.reminders_sent += 1
                    cart.last_reminder = now

    def _send_recovery_message(self, step, config):
        """Log the recovery message (integrate with WhatsApp/SMS in production)."""
        self.ensure_one()
        messages = {
            1: config.step1_message,
            2: config.step2_message,
            3: config.step3_message,
        }
        msg = messages.get(step, '')
        _logger.info(
            'Cart Recovery Step %d: partner=%s, order=%s, message=%s',
            step, self.partner_id.name, self.order_id.name, msg,
        )
        # Log as chatter note on the order
        self.order_id.message_post(
            body=f'[Cart Recovery Step {step}] {msg}',
            message_type='note',
        )
