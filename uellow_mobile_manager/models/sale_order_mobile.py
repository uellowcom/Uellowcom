# -*- coding: utf-8 -*-
"""Add a mobile-cart token to sale.order for guest carts coming from
the Flutter app. The token lets a guest user keep their cart across
app restarts without needing an account; once they log in we transfer
the cart to their partner_id."""
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
