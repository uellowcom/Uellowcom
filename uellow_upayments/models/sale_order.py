import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

_logger = logging.getLogger(__name__)

_DEFAULT_BASE = 'https://sandboxapi.upayments.com/api/v1'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    upayments_link = fields.Char('UPayments link', readonly=True, copy=False)
    upayments_track_id = fields.Char('UPayments track id', readonly=True, copy=False)
    upayments_paid = fields.Boolean('Paid via UPayments', readonly=True, copy=False)
    # Shipping rate captured at checkout (the draft order has no delivery line
    # until payment succeeds; the webhook uses this to add it on confirm).
    upayments_ship_rate = fields.Float('Pending shipping rate', readonly=True, copy=False)
    # v2.1.96 — cash-first pricing: the zone COD surcharge included inside
    # ship_rate. Online payers get THIS amount back in their wallet on capture.
    upayments_cod_surcharge = fields.Float(
        'COD surcharge (refund if online)', readonly=True, copy=False)

    # ── ship-guard on confirm (2026-07-01, triggered by S06427) ──────────
    def action_confirm(self):
        """Safety net for online orders confirmed OUTSIDE the UPayments
        capture path.

        Online orders stay a draft cart with NO delivery line; the shipping
        line is normally added by ``_upayments_mark_paid`` at payment
        capture. If such an order is confirmed some other way (a manual
        backend confirm, an admin action, a reconcile) BEFORE/without capture,
        the deferred line is never added and the order ships free by accident
        (this is exactly what happened to S06427). After the standard confirm
        we re-add the pending shipping line so shipping is never silently 0."""
        res = super().action_confirm()
        for order in self:
            try:
                order._upayments_ship_guard_on_confirm()
            except Exception:
                _logger.exception(
                    'UPayments ship-guard on confirm failed for %s', order.id)
        return res

    def _upayments_ship_guard_on_confirm(self):
        self.ensure_one()
        if self.state not in ('sale', 'done'):
            return
        # only online orders are at risk (COD adds its line at confirm time)
        if getattr(self, 'payment_method_type', '') != 'online':
            return
        if not self.carrier_id:
            return
        # already has a delivery line → nothing to do (normal captured flow
        # adds it while still draft, so this is the common no-op path)
        if self.order_line.filtered(lambda l: getattr(l, 'is_delivery', False)):
            return
        # Only act on a KNOWN positive pending rate. If the rate is 0/unset we
        # do NOT invent one — that could over-charge an order that genuinely
        # qualified for free shipping. The pending rate stored at checkout is
        # already the engine-adjusted final price (free = 0), so a positive
        # value means real shipping that never got applied.
        rate = self.upayments_ship_rate or 0.0
        if rate <= 0:
            # Still surface the anomaly for an online order confirmed without a
            # captured payment, so ops can see it (non-breaking).
            self._upayments_flag_unpaid_confirm()
            return
        try:
            self.sudo().set_delivery_line(self.carrier_id, rate)
            self.sudo().message_post(body=_(
                '⚠️ Shipping line auto-added on confirm (%.3f KD). This order '
                'was confirmed outside the UPayments capture path, so the '
                'deferred shipping line was missing and would have shipped '
                'free.') % rate)
        except Exception:
            _logger.exception(
                'ship-guard set_delivery_line failed for %s', self.id)
        self._upayments_flag_unpaid_confirm()

    def _upayments_flag_unpaid_confirm(self):
        """Post a one-time chatter warning when an online UPayments order is
        confirmed while its payment was never captured (initiated → track id
        present, but upayments_paid is still False). Visibility only."""
        self.ensure_one()
        try:
            if (self.upayments_track_id and not self.upayments_paid
                    and getattr(self, 'payment_method_type', '') == 'online'):
                self.sudo().message_post(body=_(
                    '⚠️ Confirmed while the UPayments payment was NOT captured '
                    '(upayments_paid = False). Verify the payment before '
                    'fulfilment. / تم التأكيد دون تحصيل دفعة UPayments — تحقّق '
                    'من الدفع قبل التجهيز.'))
        except Exception:
            pass

    def _upayments_config(self):
        ICP = self.env['ir.config_parameter'].sudo()
        base = (ICP.get_param('uellow_upayments.base_url') or _DEFAULT_BASE).rstrip('/')
        token = (ICP.get_param('uellow_upayments.token') or '').strip()
        return base, token

    def _upayments_create_charge(self, return_url, cancel_url, notify_url,
                                 lang='en', gateway=None, amount=None):
        """Create a UPayments charge and return the hosted payment link.
        `amount` overrides the charged total (used to include shipping, since
        the draft order has no delivery line yet)."""
        self.ensure_one()
        if requests is None:
            raise UserError(_('The Python "requests" library is missing.'))
        base, token = self._upayments_config()
        if not token:
            raise UserError(_('UPayments is not configured (missing API token).'))
        p = self.partner_id
        lines = self.order_line.filtered(
            lambda l: not l.display_type and not l.is_reward_line
            and not getattr(l, 'is_delivery', False))
        charge_total = round(amount if amount is not None else (self.amount_total or 0.0), 3)
        payload = {
            'order': {
                'id': (self.name or str(self.id))[:40],
                'description': ('Order %s' % (self.name or self.id))[:500],
                'currency': (self.currency_id.name or 'KWD')[:3],
                'amount': charge_total,
            },
            'language': 'ar' if (lang or 'en').startswith('ar') else 'en',
            'reference': {'id': str(self.id)[:35]},
            'returnUrl': (return_url or '')[:250],
            'cancelUrl': (cancel_url or '')[:250],
            'notificationUrl': (notify_url or '')[:250],
        }
        # Customer (optional) — only include a mobile that looks valid
        # (UPayments rejects malformed mobiles), and only attach customer at all
        # when we have something meaningful.
        customer = {
            'uniqueId': str(p.id)[:50],
            'name': (p.name or 'Customer')[:50],
            'email': (p.email or 'guest@uellow.com')[:50],
        }
        raw_mobile = (p.mobile or p.phone or '').strip()
        digits = ''.join(ch for ch in raw_mobile if ch.isdigit())
        if len(digits) >= 8:
            customer['mobile'] = ('+' + digits)[:15]
        payload['customer'] = customer
        # Products are OPTIONAL — only send well-formed line items (name +
        # positive price + quantity). A malformed/zero-price line makes
        # UPayments reject the whole charge ("check product name/quantity/
        # price"), so skip anything that doesn't qualify and omit the array
        # entirely if none qualify (the charge still runs on order.amount).
        products = []
        for l in lines:
            name = (l.product_id.display_name or '').strip()
            price = round(l.price_unit or 0.0, 3)
            qty = int(l.product_uom_qty or 0)
            if name and price > 0 and qty > 0:
                products.append({'name': name[:255], 'description': name[:255],
                                 'price': price, 'quantity': qty})
        if products:
            payload['products'] = products[:50]
        if gateway:
            payload['paymentGateway'] = {'src': gateway}
        try:
            r = requests.post(
                base + '/charge',
                headers={'Authorization': 'Bearer %s' % token,
                         'Content-Type': 'application/json',
                         'Accept': 'application/json'},
                json=payload, timeout=30)
            data = r.json()
        except Exception as e:
            _logger.exception('UPayments charge request failed')
            raise UserError(_('Could not reach UPayments: %s') % e)
        if not data.get('status'):
            raise UserError(data.get('message') or _('UPayments rejected the charge.'))
        dobj = data.get('data') or {}
        link = dobj.get('link')
        if not link:
            raise UserError(_('UPayments did not return a payment link.'))
        vals = {'upayments_link': link}
        # Store the track id NOW (the /charge response returns it) so the
        # order can be reconciled later via the status API even if the
        # capture webhook never fires (the S06360 failure mode).
        tid = dobj.get('trackId') or dobj.get('track_id') or dobj.get('track')
        if tid:
            vals['upayments_track_id'] = str(tid)
        self.sudo().write(vals)
        return link

    def _upayments_result_readonly(self):
        """Return UPayments' live result string for this order's charge
        (e.g. 'CAPTURED') WITHOUT mutating the order. '' on any failure."""
        self.ensure_one()
        if requests is None:
            return ''
        track = (self.upayments_track_id or '').strip()
        if not track:
            return ''
        base, token = self._upayments_config()
        if not token:
            return ''
        try:
            r = requests.get(
                '%s/get-payment-status/%s' % (base.rstrip('/'), track),
                headers={'Authorization': 'Bearer %s' % token,
                         'Accept': 'application/json'}, timeout=20)
            data = r.json()
            if not data.get('status'):
                return ''
            return (((data.get('data') or {}).get('transaction') or {})
                    .get('result') or '').upper()
        except Exception as e:
            _logger.warning('UPayments readonly status failed for %s: %s',
                            self.id, e)
            return ''

    @api.model
    def _cron_upayments_reconcile(self, days=7, limit=300):
        """Heal UPayments orders whose capture webhook never arrived.

        Scans initiated-but-unpaid orders (track id present, upayments_paid
        False) from the last `days`, INCLUDING cancelled ones — S06427 was a
        genuinely-CAPTURED order that got cancelled while it looked unpaid, so
        the money was received but the order was dead and no reconcile touched
        it. For a cancelled order we FIRST confirm CAPTURED via a read-only
        status call, and only then resurrect it (draft → heal) so we never
        revive a genuinely abandoned cart."""
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(days=days)
        orders = self.sudo().search([
            ('upayments_track_id', '!=', False),
            ('upayments_paid', '=', False),
            ('state', 'in', ('draft', 'sent', 'cancel')),
            ('create_date', '>=', cutoff),
        ], limit=limit)
        healed = 0
        for o in orders:
            try:
                if o.state == 'cancel':
                    if o._upayments_result_readonly() not in (
                            'CAPTURED', 'SUCCESS', 'SUCCESSFUL', 'AUTHORIZED'):
                        continue  # genuinely unpaid → leave cancelled
                    o.action_draft()
                    o.message_post(body=_(
                        '♻️ Auto-recovered by reconcile: the UPayments payment '
                        'was CAPTURED but the order had been cancelled — '
                        'restoring, marking paid and adding shipping. / '
                        'استُرجع الطلب: الدفع مؤكّد لكنه كان ملغى.'))
                if o._upayments_verify_status():
                    healed += 1
                    o._upayments_alert_admins_recovered()
                    self.env.cr.commit()
            except Exception:
                _logger.exception(
                    'UPayments reconcile failed for %s', o.id)
                self.env.cr.rollback()
        if healed:
            _logger.warning(
                'UPayments reconcile: recovered %s missed-webhook order(s).',
                healed)
        return healed

    def _upayments_alert_admins_recovered(self):
        """Notify admins that the reconcile cron caught a captured payment
        whose webhook was missed (push + app-inbox row). Best-effort."""
        self.ensure_one()
        try:
            CN = self.env.get('mobile.customer.notification')
            if CN is None or not hasattr(CN, 'push_admins'):
                return
            amt = self.amount_total or 0.0
            cur = (self.currency_id.name or 'KWD')
            # toggle_field is optional on the settings model — a name that
            # doesn't exist defaults to True, so this always fires (still
            # gated by the master push switch).
            CN.sudo().push_admins(
                'notify_payment_reconcile',
                title_en='Payment recovered',
                title_ar='تم استرجاع دفعة',
                body_en=('Order %s — a captured payment whose webhook was '
                         'missed was auto-reconciled (%.3f %s).'
                         % (self.name, amt, cur)),
                body_ar=('الطلب %s — استُرجعت دفعة مؤكّدة فات إشعار الـ webhook '
                         'الخاص بها تلقائياً (%.3f %s).' % (self.name, amt, cur)),
                data={'type': 'order', 'order_id': self.id,
                      'order_name': self.name})
        except Exception:
            _logger.debug('reconcile admin alert failed for %s',
                          self.id, exc_info=True)

    def _upayments_verify_status(self):
        """Ask UPayments for the live status of this order's charge and
        capture it when CAPTURED. Returns True when the order is (now) paid.

        Idempotent — `_upayments_mark_paid` guards against double credit — so
        it is safe to call from the return handler, an admin reconcile action
        or a cron. This heals a missed/failed capture webhook: the payment
        succeeded at the gateway but Odoo never heard about it (S06360)."""
        self.ensure_one()
        if self.upayments_paid:
            return True
        if requests is None:
            return False
        track = (self.upayments_track_id or '').strip()
        if not track:
            return False
        base, token = self._upayments_config()
        if not token:
            return False
        url = '%s/get-payment-status/%s' % (base.rstrip('/'), track)
        try:
            r = requests.get(
                url, headers={'Authorization': 'Bearer %s' % token,
                              'Accept': 'application/json'}, timeout=20)
            data = r.json()
        except Exception as e:
            _logger.warning('UPayments status check failed for %s: %s',
                            self.id, e)
            return False
        try:
            res = (((data.get('data') or {}).get('transaction') or {})
                   .get('result') or '').upper()
        except Exception:
            res = ''
        if data.get('status') and res in ('CAPTURED', 'SUCCESS',
                                          'SUCCESSFUL', 'AUTHORIZED'):
            self._upayments_mark_paid(track_id=track)
            return True
        return False

    def _upayments_mark_paid(self, track_id=None, payment_id=None):
        """Flag the order paid + confirm it (called from the webhook on
        CAPTURED). Online orders stay a draft cart at checkout, so a successful
        payment is what actually confirms them."""
        self.ensure_one()
        vals = {'upayments_paid': True}
        if track_id:
            vals['upayments_track_id'] = track_id
        self.sudo().write(vals)
        # Add the shipping (delivery) line now — it was kept off the draft cart.
        try:
            if (self.carrier_id and self.state in ('draft', 'sent')
                    and not self.order_line.filtered(
                        lambda l: getattr(l, 'is_delivery', False))):
                self.sudo().set_delivery_line(self.carrier_id,
                                              self.upayments_ship_rate or 0.0)
        except Exception:
            _logger.exception('UPayments: set_delivery_line on capture failed for %s', self.id)
        try:
            if self.state in ('draft', 'sent'):
                self.sudo().action_confirm()
        except Exception:
            _logger.exception('UPayments: confirm-on-capture failed for %s', self.id)
        try:
            self.sudo().message_post(body=_(
                'UPayments payment captured (track: %s, payment_id: %s).')
                % (track_id or '-', payment_id or '-'))
        except Exception:
            pass
        # v2.1.96 — cash-first pricing: the delivery amount charged included
        # the zone COD surcharge; an ONLINE payer doesn't owe it — refund it
        # straight into the wallet (idempotent).
        try:
            sur = float(self.upayments_cod_surcharge or 0.0)
            Tx = self.env.get('uellow.customer.wallet.tx')
            ref = 'CODSUR-REFUND-%s' % self.id
            if (sur > 0 and Tx is not None and self.partner_id
                    and not Tx.sudo().search([('reference', '=', ref)], limit=1)):
                Tx.sudo().credit(
                    self.partner_id, sur, tx_type='refund',
                    description='Cash-fee refund (paid online) — %s / '
                                'استرداد رسوم الدفع نقداً' % self.name,
                    reference=ref, order_id=self.id)
                self.sudo().message_post(body=_(
                    'COD surcharge %s refunded to wallet (paid online).') % sur)
        except Exception:
            _logger.exception('COD-surcharge refund failed for order %s', self.id)
        # v2.1.21 — online-payment cashback: credit the customer's wallet
        # on capture (idempotent — webhooks can fire more than once).
        try:
            Setting = self.env['mobile.app.setting'].sudo()
            setting = (Setting.search(
                [('website_id', '=', self.website_id.id)], limit=1)
                or Setting.search([], limit=1))
            cb = setting.cashback_for(self.amount_total or 0.0) \
                if setting and hasattr(setting, 'cashback_for') else 0.0
            Tx = self.env.get('uellow.customer.wallet.tx')
            ref = 'CASHBACK-%s' % self.id
            if (cb > 0 and Tx is not None and self.partner_id
                    and not Tx.sudo().search([('reference', '=', ref)], limit=1)):
                Tx.sudo().credit(
                    self.partner_id, cb, tx_type='cashback',
                    description='Online payment cashback — %s' % self.name,
                    reference=ref, order_id=self.id)
                self.sudo().message_post(body=_(
                    'Wallet cashback credited: %s (online payment).') % cb)
        except Exception:
            _logger.exception('Cashback credit failed for order %s', self.id)
