# -*- coding: utf-8 -*-
"""Add a mobile-cart token to sale.order for guest carts coming from
the Flutter app. The token lets a guest user keep their cart across
app restarts without needing an account; once they log in we transfer
the cart to their partner_id."""
from markupsafe import Markup

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mobile_cart_token = fields.Char(
        string='Mobile Cart Token', index=True, copy=False,
        help='Identifies a guest cart from the Flutter app. Set on first '
             'add-to-cart; cleared on order confirmation or once a real '
             'partner is attached at login.',
    )
    is_mobile_app_order = fields.Boolean(
        string='Created via Mobile App', default=False, copy=False,
    )
    mobile_session_id = fields.Many2one(
        'mobile.session', string='Mobile Session', index=True, copy=False,
    )

    # ── selective checkout (v2.1.65) ─────────────────────────────────
    # The customer checks SOME cart lines and pays for only those. At
    # confirm time the unselected lines move to a fresh draft order that
    # becomes the new cart; the original order (selected lines) carries
    # this flag while it waits for online payment so an abandoned payment
    # can be detected and its lines merged back into the live cart.
    mobile_checkout_split = fields.Boolean(
        string='Selective Checkout Split', default=False, copy=False,
        index=True,
        help='This order was carved out of a mobile cart via selective '
             'checkout and is awaiting payment/confirmation.')
    mobile_split_token = fields.Char(
        string='Origin Cart Token', copy=False,
        help='Guest cart token of the cart this selective-checkout order '
             'was split from (used to reclaim lines if payment is '
             'abandoned).')

    # ── customer cancellation (v2.1.42) ─────────────────────────────
    # Unpaid draft/confirmed orders cancel instantly from the app; PAID
    # orders raise a request that an admin approves/rejects here.
    cancel_request = fields.Boolean(
        string='Cancellation Requested', default=False, copy=False,
        index=True,
        help='The customer asked to cancel this PAID order from the app. '
             'Approve to cancel (handle the refund separately) or reject.')
    cancel_request_date = fields.Datetime(copy=False)
    cancel_request_reason = fields.Char(copy=False,
        string='Cancellation Reason')

    def action_approve_cancel_request(self):
        for o in self:
            try:
                o.with_context(disable_cancel_warning=True).action_cancel()
            except Exception:
                o.state = 'cancel'
            o.cancel_request = False
            o.message_post(body='✅ Customer cancellation request APPROVED '
                                '— order cancelled. Remember the refund if '
                                'a payment was captured.')

    def action_reject_cancel_request(self):
        for o in self:
            o.cancel_request = False
            o.message_post(body='🚫 Customer cancellation request rejected '
                                '— order continues normally.')

    # ── full order + payment snapshot in the chatter (2026-06-26) ────
    def _post_app_order_summary(self, event='Order confirmed'):
        """Post one complete order + payment + shipping snapshot to the
        order chatter so the whole picture is visible in one place for
        every order (items, amounts, payment method & status, carrier,
        address, and the app/device source)."""
        for o in self:
            try:
                cur = o.currency_id.symbol or o.currency_id.name or ''
                prod_total = ship_total = 0.0
                rows = []
                for l in o.order_line:
                    if l.display_type:
                        continue
                    if l.is_delivery:
                        ship_total += l.price_total
                        continue
                    prod_total += l.price_total
                    rows.append(Markup('• %s ×%s = %.3f %s') % (
                        (l.product_id.display_name or l.name or '')[:60],
                        ('%g' % (l.product_uom_qty or 0)),
                        l.price_total, cur))
                # payment method + status
                pmt = (o.payment_method_type or '').lower()
                if getattr(o, 'upayments_paid', False):
                    pay = '✅ PAID online (UPayments)'
                elif pmt == 'cash':
                    pay = '💵 Cash on delivery — collect %.3f %s on delivery' % (
                        o.amount_total, cur)
                elif o.invoice_ids.filtered(
                        lambda i: i.payment_state in ('paid', 'in_payment')):
                    pay = '✅ Invoice paid'
                else:
                    pay = '⏳ Payment pending'
                txs = [Markup('%s %.3f %s (%s)') % (
                    t.provider_id.name or '', t.amount, cur, t.state)
                    for t in o.transaction_ids]
                ship = o.partner_shipping_id
                addr = ', '.join(filter(None, [
                    ship.street, ship.street2, ship.city,
                    ship.country_id.name if ship.country_id else '']))
                carrier = (getattr(o, 'delivery_carrier_company_id', False)
                           and o.delivery_carrier_company_id.name) \
                    or (o.carrier_id.name if o.carrier_id else '—')
                drv = getattr(o, 'delivery_driver_id', False)
                sess = getattr(o, 'mobile_session_id', False)
                src = o.website_id.name or 'Backend'
                if sess:
                    src += ' · %s · app %s' % (
                        sess.device_name or sess.platform or '',
                        sess.app_version or '')
                items_html = Markup('<br/>').join(rows) if rows else Markup('—')
                tx_html = (Markup('<br/><b>Transactions:</b> ')
                           + Markup('; ').join(txs)) if txs else Markup('')
                drv_html = (Markup(' · driver: %s') % drv.name) if drv \
                    else Markup('')
                body = Markup(
                    '<b>📦 %s — %s</b>'
                    '<br/><b>Customer:</b> %s · %s'
                    '<br/><b>Items:</b><br/>%s'
                    '<br/><b>Products:</b> %.3f %s · <b>Shipping:</b> %.3f %s'
                    ' · <b>Total:</b> %.3f %s'
                    '<br/><b>Payment:</b> %s%s'
                    '<br/><b>Delivery:</b> %s%s'
                    '<br/><b>Address:</b> %s'
                    '<br/><b>Source:</b> %s'
                ) % (
                    o.name or '', event,
                    o.partner_id.name or '',
                    o.partner_id.phone or o.partner_id.mobile or '—',
                    items_html,
                    prod_total, cur, ship_total, cur, o.amount_total, cur,
                    pay, tx_html,
                    carrier, drv_html,
                    addr or '—', src,
                )
                o.message_post(body=body, subtype_xmlid='mail.mt_note')
            except Exception:
                # Never let logging block confirmation/capture.
                pass

    def action_confirm(self):
        res = super().action_confirm()
        # Snapshot every order on confirmation (app, web, POS, backend).
        try:
            self._post_app_order_summary('Order confirmed')
        except Exception:
            pass
        return res

    @api.model
    def merge_mobile_cart_into_partner(self, partner_id, cart_token):
        """At login time, if a guest cart token was active, move its
        lines into the freshly-authenticated partner's draft cart."""
        if not cart_token or not partner_id:
            return False
        guest = self.sudo().search([
            ('mobile_cart_token', '=', cart_token),
            ('state', '=', 'draft'),
        ], limit=1)
        if not guest or not guest.order_line:
            return False
        existing = self.sudo().search([
            ('partner_id', '=', partner_id),
            ('state', '=', 'draft'),
        ], limit=1, order='id desc')
        if not existing:
            guest.write({'partner_id': partner_id, 'mobile_cart_token': False})
            return guest.id
        # Move lines and drop the guest cart
        for line in guest.order_line:
            same = existing.order_line.filtered(
                lambda l: l.product_id == line.product_id and not l.is_reward_line)
            if same:
                same[0].product_uom_qty += line.product_uom_qty
            else:
                line.order_id = existing.id
        guest.unlink()
        return existing.id
