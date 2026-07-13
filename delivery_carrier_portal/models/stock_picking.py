# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    """Inventory-side delivery actions on outgoing pickings:

    1. `action_uellow_confirm_delivery` — mark the linked sale order DELIVERED
       (delivery_status='delivered') straight from Inventory, same end-state the
       driver app reaches via /api/driver/v1/orders/<id>/confirm.
    2. `action_uellow_complete_and_settle` — ONE click for the full close-out:
       confirm delivery → create & post the invoice → confirm payment (true
       'paid' via a settling bank journal entry reconciled to the receivable) →
       lock the order. Mirrors the order backfill flow ([[orders-backfill-paid]]).

    Needed because in this DB `delivery_status` is the carrier-flow field
    (compute detached); validating a picking no longer flips the order, so the
    customer kept seeing 'confirmed'."""
    _inherit = 'stock.picking'

    uellow_can_confirm_delivery = fields.Boolean(
        compute='_compute_uellow_delivery_btns')
    uellow_can_settle = fields.Boolean(
        compute='_compute_uellow_delivery_btns')
    uellow_is_delivered = fields.Boolean(
        compute='_compute_uellow_delivery_btns')
    uellow_is_settled = fields.Boolean(
        compute='_compute_uellow_delivery_btns')

    @api.depends('state', 'picking_type_code', 'sale_id',
                 'sale_id.delivery_status', 'sale_id.invoice_status',
                 'sale_id.invoice_ids.state', 'sale_id.invoice_ids.payment_state')
    def _compute_uellow_delivery_btns(self):
        ICP = self.env['ir.config_parameter'].sudo()
        confirm_on = ICP.get_param(
            'uellow_delivery.inventory_confirm_btn', 'True') == 'True'
        settle_on = ICP.get_param(
            'uellow_delivery.inventory_settle_btn', 'True') == 'True'
        SO = self.env['sale.order']
        has_ds = 'delivery_status' in SO._fields
        for pick in self:
            order = pick.sale_id
            is_out = bool(order and pick.picking_type_code == 'outgoing'
                          and has_ds)
            delivered = bool(is_out and order.delivery_status == 'delivered')
            # "settled" = truly finished: delivered + fully invoiced + paid.
            # NOT based on `locked` — this DB auto-locks every confirmed order
            # ("Lock Confirmed Sales"), so lock means nothing here.
            posted_invs = order.invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice' and m.state == 'posted') \
                if is_out else SO.env['account.move']
            paid = bool(posted_invs) and all(
                m.payment_state == 'paid' for m in posted_invs)
            settled = bool(delivered and order.invoice_status == 'invoiced'
                           and paid)
            base = bool(is_out and pick.state != 'cancel'
                        and order.state in ('sale', 'done'))
            pick.uellow_is_delivered = delivered
            pick.uellow_is_settled = settled
            pick.uellow_can_confirm_delivery = bool(
                base and confirm_on and not delivered and not settled)
            # settle button stays available until the order is truly settled
            pick.uellow_can_settle = bool(base and settle_on and not settled)

    # ── shared helpers ───────────────────────────────────────────────
    def _uellow_validate_picking(self):
        """Force-validate this picking if still open (best-effort)."""
        self.ensure_one()
        if self.state in ('done', 'cancel'):
            return
        try:
            for ml in self.move_ids:
                if ml.state not in ('done', 'cancel'):
                    ml.quantity = ml.product_uom_qty
                    if 'picked' in ml._fields:
                        ml.picked = True
            res = self.button_validate()
            if isinstance(res, dict) and res.get('res_model') == \
                    'stock.backorder.confirmation':
                wiz = self.env['stock.backorder.confirmation'] \
                    .with_context(res.get('context') or {}).create(
                        {'pick_ids': [(6, 0, self.ids)]})
                wiz.process()
        except Exception:
            pass

    def _uellow_mark_delivered(self, order, now):
        """Flip the order to delivered + sync trip line + chatter + push."""
        if not order or order.delivery_status == 'delivered':
            return
        vals = {'delivery_status': 'delivered'}
        if 'delivery_date_actual' in order._fields:
            vals['delivery_date_actual'] = now
        if order.payment_method_type == 'cash' and \
                'cash_collection_status' in order._fields:
            vals['cash_collection_status'] = 'collected'
        order.sudo().with_context(skip_push=True).write(vals)
        try:
            Line = self.env['delivery.trip.line'].sudo()
            lines = Line.search([('sale_order_id', '=', order.id)])
            lvals = {'delivery_status': 'delivered'}
            if 'delivery_date_actual' in Line._fields:
                lvals['delivery_date_actual'] = now
            lines.write(lvals)
        except Exception:
            pass
        try:
            order.message_post(body=_(
                '✅ Delivery confirmed from Inventory by %s.\n'
                'تم تأكيد التوصيل من المخزون بواسطة %s.') % (
                self.env.user.name, self.env.user.name))
        except Exception:
            pass
        try:
            Eng = self.env.get('mobile.customer.notification')
            if Eng is not None and order.partner_id:
                Eng.sudo().push_event(
                    order.partner_id, 'order_delivered',
                    'Delivered ✅', 'تم تسليم طلبك ✅',
                    'Your order %s has been delivered. Thank you!' % order.name,
                    'تم تسليم طلبك %s بنجاح. شكراً لك!' % order.name,
                    {'type': 'order', 'id': order.id})
        except Exception:
            pass

    def _uellow_settle_invoice(self, move, order, today):
        """Mark a posted invoice as truly PAID by posting a bank journal entry
        (Dr bank / Cr receivable) and reconciling it with the invoice
        receivable — yields payment_state='paid' (register-payment alone only
        gives 'in_payment'). Skips if already paid / nothing owed."""
        if move.state != 'posted' or move.payment_state in ('paid', 'in_payment', 'reversed'):
            return False
        rec = move.line_ids.filtered(
            lambda l: l.account_id.account_type == 'asset_receivable'
            and not l.reconciled)
        if not rec:
            return False
        amt = sum(rec.mapped('debit')) - sum(rec.mapped('credit'))
        if amt <= 0:
            return False
        acct = rec[0].account_id
        AJ = self.env['account.journal'].sudo()
        bank_j = AJ.search([('type', '=', 'bank'),
                            ('company_id', '=', order.company_id.id)], limit=1) \
            or AJ.browse(14)
        bank_acct = bank_j.default_account_id \
            or self.env['account.account'].sudo().browse(188)
        je = self.env['account.move'].sudo().create({
            'move_type': 'entry', 'journal_id': bank_j.id, 'date': today,
            'ref': _('Payment %s') % (move.name or order.name),
            'line_ids': [
                (0, 0, {'account_id': bank_acct.id, 'debit': amt, 'credit': 0.0,
                        'partner_id': order.partner_id.id,
                        'name': _('Payment %s') % (move.name or order.name)}),
                (0, 0, {'account_id': acct.id, 'debit': 0.0, 'credit': amt,
                        'partner_id': order.partner_id.id,
                        'name': _('Payment %s') % (move.name or order.name)}),
            ]})
        je.action_post()
        (rec + je.line_ids.filtered(
            lambda l: l.account_id.id == acct.id)).reconcile()
        return True

    # ── button 1: confirm delivery only ──────────────────────────────
    def action_uellow_confirm_delivery(self):
        now = fields.Datetime.now()
        if 'delivery_status' not in self.env['sale.order']._fields:
            raise UserError(_('Delivery flow module not installed.\n'
                              'وحدة تدفّق التوصيل غير مثبّتة.'))
        for pick in self:
            order = pick.sale_id
            if not order or pick.picking_type_code != 'outgoing':
                continue
            pick._uellow_validate_picking()
            pick._uellow_mark_delivered(order, now)
        return True

    # ── button 2: deliver + invoice + pay + settle + lock ────────────
    def action_uellow_complete_and_settle(self):
        now = fields.Datetime.now()
        today = fields.Date.context_today(self)
        SO = self.env['sale.order']
        if 'delivery_status' not in SO._fields:
            raise UserError(_('Delivery flow module not installed.\n'
                              'وحدة تدفّق التوصيل غير مثبّتة.'))
        done = []
        skipped = []
        for pick in self:
            order = pick.sale_id
            if not order or pick.picking_type_code != 'outgoing':
                continue
            # 1) deliver
            pick._uellow_validate_picking()
            pick._uellow_mark_delivered(order, now)
            # 2) invoice
            order.invalidate_recordset(['invoice_status'])
            inv = order.invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice' and m.state != 'cancel')
            if not inv:
                try:
                    inv = order._create_invoices()
                except Exception as e:
                    skipped.append('%s (لا يوجد ما يُفوتَر / %s)' % (
                        order.name, str(e).split('\n')[0][:60]))
                    inv = self.env['account.move']
            paid_ok = True
            for m in inv:
                try:
                    if m.state == 'draft':
                        m.write({'invoice_date': today, 'date': today})
                        m.action_post()
                except Exception as e:
                    paid_ok = False
                    skipped.append('%s (فاتورة %s)' % (
                        order.name, str(e).split('\n')[0][:60]))
                    continue
                # 3) pay + settle
                try:
                    self._uellow_settle_invoice(m, order, today)
                except Exception as e:
                    paid_ok = False
                    skipped.append('%s (دفع %s)' % (
                        order.name, str(e).split('\n')[0][:60]))
            # 4) lock the record (close it) — only if fully settled
            order.invalidate_recordset(['invoice_status', 'delivery_status'])
            posted = order.invoice_ids.filtered(
                lambda m: m.move_type == 'out_invoice' and m.state == 'posted')
            fully_paid = bool(posted) and all(
                m.payment_state == 'paid' for m in posted)
            try:
                if fully_paid and not order.locked and hasattr(order, 'action_lock'):
                    order.action_lock()
            except Exception:
                pass
            # classify by the REAL end-state, not by "we ran the steps"
            if order.delivery_status == 'delivered' and \
                    order.invoice_status == 'invoiced' and fully_paid:
                done.append(order.name)
            elif order.name not in [s.split(' ')[0] for s in skipped]:
                skipped.append('%s (%s)' % (order.name, _(
                    'delivered, invoicing/payment incomplete')
                    if order.delivery_status == 'delivered'
                    else _('not fully completed')))
        # user feedback
        msg = _('Completed & settled: %s') % (', '.join(done) or '—')
        if skipped:
            msg += _('\nNeeds attention: %s') % '; '.join(skipped)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Delivery & Settlement'),
                'message': msg,
                'type': 'warning' if skipped else 'success',
                'sticky': bool(skipped),
            },
        }
