# -*- coding: utf-8 -*-
"""Order-side hook: forward dropship lines to the provider after the sale is
confirmed & paid.

SAFETY: this NEVER interferes with a normal Uellow order. It only looks at lines
whose product is ``is_dropship``; if there are none it returns immediately. The
provider call is wrapped so a provider outage can never block order confirmation.
Placement is off by default (setting ``auto_place_order``).
"""
import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    dropship_order_ref = fields.Char(
        string="Provider Order Ref", copy=False, readonly=True,
        help="Reference returned by the dropshipping provider (e.g. AliExpress).")
    dropship_status = fields.Char(string="Dropship Status", copy=False, readonly=True)
    dropship_tracking = fields.Char(string="Tracking No.", copy=False, readonly=True)
    dropship_carrier = fields.Char(string="Provider Carrier", copy=False, readonly=True)
    dropship_synced = fields.Datetime(string="Last Tracking Sync", copy=False, readonly=True)
    is_dropship_order = fields.Boolean(
        string="Has Dropship Lines", compute='_compute_is_dropship_order',
        store=True, help="True when any line is a Uellow World / dropship product.")

    dropship_cost = fields.Monetary(
        string="Dropship Cost", compute='_compute_dropship_profit',
        currency_field='currency_id', store=True,
        help="Estimated provider (AliExpress) cost of the dropship lines.")
    dropship_profit = fields.Monetary(
        string="Dropship Profit", compute='_compute_dropship_profit',
        currency_field='currency_id', store=True,
        help="Dropship revenue minus provider cost (approximate — provider "
             "cost is in the provider currency).")
    dropship_margin = fields.Float(
        string="Dropship Margin %", compute='_compute_dropship_profit', store=True)

    @api.depends('order_line.product_id.is_dropship')
    def _compute_is_dropship_order(self):
        for order in self:
            order.is_dropship_order = any(
                l.product_id.is_dropship for l in order.order_line)

    @api.depends('order_line.price_subtotal', 'order_line.product_uom_qty',
                 'order_line.product_id')
    def _compute_dropship_profit(self):
        for order in self:
            cost = revenue = 0.0
            for line in order.order_line:
                if not line.product_id.is_dropship:
                    continue
                ds = line.product_id.product_tmpl_id.dropship_product_id
                cost += (ds.base_cost or line.product_id.standard_price or 0.0) \
                    * line.product_uom_qty
                revenue += line.price_subtotal
            order.dropship_cost = cost
            order.dropship_profit = revenue - cost
            order.dropship_margin = round(
                (order.dropship_profit * 100.0 / revenue), 1) if revenue else 0.0

    def _has_dropship_lines(self):
        return any(l.product_id.is_dropship for l in self.order_line)

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order._has_dropship_lines():
                order._maybe_place_dropship_order()
                # credit any live A/B title test to the currently-serving variant
                for line in order.order_line.filtered(
                        lambda l: l.product_id.is_dropship):
                    ds = line.product_id.product_tmpl_id.dropship_product_id
                    if ds and ds.ab_active:
                        ds.sudo().record_ab_order()
        return res

    def action_fulfill_dropship(self):
        """Manual button: place the provider (AliExpress) order NOW with the
        customer's shipping data auto-filled, even if auto-placement is off.
        Idempotent — won't double-order."""
        placed = 0
        errors = []
        for order in self:
            if not order._has_dropship_lines():
                continue
            if order.dropship_order_ref:
                continue
            errors += order._maybe_place_dropship_order(force=True) or []
            if order.dropship_order_ref:
                placed += 1
        # surface the provider's real reason (e.g. bad zip) as a clear dialog
        # instead of a vague "nothing to place".
        if not placed and errors:
            raise UserError(_(
                "AliExpress could not accept the order:\n\n• %s\n\n"
                "Fix the customer's shipping address (a valid numeric zip code "
                "is required) and try again.") % '\n• '.join(errors))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Fulfillment',
                'message': '%d order(s) placed with the provider.' % placed
                           if placed else 'Nothing to place (already fulfilled '
                           'or no dropship lines).',
                'type': 'success' if placed else 'warning',
                'sticky': False,
            },
        }

    def action_sync_dropship_tracking(self):
        """Pull the latest tracking number/carrier from the provider."""
        for order in self:
            if not order.dropship_order_ref:
                continue
            provider = self.env['dropship.provider'].sudo().search([
                ('code', '=', 'aliexpress'), ('state', '=', 'connected')], limit=1)
            if not provider:
                continue
            ref = order.dropship_order_ref.split(',')[0].strip()
            try:
                info = provider._adapter().get_tracking(ref) or {}
            except Exception as e:  # noqa: BLE001
                _logger.info("tracking sync failed for %s: %s", order.name, e)
                continue
            vals = {'dropship_synced': fields.Datetime.now()}
            if info.get('tracking_number') or info.get('mail_no'):
                vals['dropship_tracking'] = info.get('tracking_number') or info.get('mail_no')
            if info.get('carrier') or info.get('logistics_service'):
                vals['dropship_carrier'] = info.get('carrier') or info.get('logistics_service')
            if info.get('status'):
                vals['dropship_status'] = info.get('status')
            order.write(vals)
        return True

    @api.model
    def _cron_sync_tracking(self):
        """Keep tracking fresh for fulfilled-but-not-delivered dropship orders.
        Bounded per run. Gated on the module being enabled."""
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.enabled') not in ('True', '1', 'true'):
            return
        limit = int(ICP.get_param('uellow_dropship.tracking_sync_batch', 100) or 100)
        orders = self.search([
            ('dropship_order_ref', '!=', False),
            ('state', 'in', ('sale', 'done')),
        ], order='dropship_synced asc nulls first', limit=limit)
        for order in orders:
            try:
                order.action_sync_dropship_tracking()
                self.env.cr.commit()
            except Exception:  # noqa: BLE001
                self.env.cr.rollback()
        return True

    def action_export_ali_csv(self):
        """Export selected dropship orders as a CSV ready for manual AliExpress
        ordering (product id, sku, qty + full shipping address). Returns a
        download link."""
        import base64
        import csv
        import io
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(['Order', 'Date', 'Customer', 'Product ID', 'Product',
                    'SKU Attrs', 'Qty', 'Unit Price', 'Country', 'State/Province',
                    'City', 'Address', 'Contact', 'Phone', 'ZIP'])
        for order in self:
            if not order._has_dropship_lines():
                continue
            addr = order._dropship_address()
            for line in order.order_line.filtered(lambda l: l.product_id.is_dropship):
                ds = line.product_id.product_tmpl_id.dropship_product_id
                variants = []
                try:
                    variants = json.loads(ds.variants_json or '[]') if ds else []
                except Exception:  # noqa: BLE001
                    variants = []
                sku_attr = (variants[0].get('attrs') if variants else '') or ''
                w.writerow([
                    order.name,
                    order.date_order and order.date_order.strftime('%Y-%m-%d') or '',
                    order.partner_id.name or '',
                    ds.source_id if ds else '',
                    line.product_id.display_name or '',
                    sku_attr,
                    int(line.product_uom_qty),
                    line.price_unit,
                    addr['country'], addr['province'], addr['city'],
                    addr['address'], addr['contact_person'],
                    '%s %s' % (addr['phone_country'], addr['mobile_no']),
                    addr['zip'],
                ])
        data = base64.b64encode(buf.getvalue().encode('utf-8-sig'))
        att = self.env['ir.attachment'].create({
            'name': 'aliexpress_fulfillment.csv',
            'type': 'binary',
            'datas': data,
            'mimetype': 'text/csv',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % att.id,
            'target': 'self',
        }

    def _alert_needs_fulfillment(self):
        """Tell the admins a dropship order is waiting to be placed manually.
        Posts a chatter note + a To-Do activity for the salesperson (best-effort)."""
        self.ensure_one()
        try:
            self.message_post(
                body="🚀 This order contains Uellow World (dropship) items and "
                     "is <b>waiting to be fulfilled to the provider</b>. Open the "
                     "Dropship tab and click <b>Fulfill to AliExpress</b>.",
                subject="Dropship order needs fulfillment")
        except Exception:  # noqa: BLE001
            pass
        try:
            user = self.user_id or self.env.user
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary='Fulfill dropship order to AliExpress',
                user_id=user.id)
        except Exception:  # noqa: BLE001
            pass

    def _maybe_place_dropship_order(self, force=False):
        """Place provider orders for dropship lines, if enabled. Best-effort.
        Returns a list of human error messages (empty when it succeeded)."""
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        if not force and ICP.get_param('uellow_dropship.auto_place_order') not in ('True', '1', 'true'):
            self.dropship_status = 'pending_manual'
            self._alert_needs_fulfillment()
            return []
        if self.dropship_order_ref:
            return []  # already placed (idempotent)

        note = ICP.get_param('uellow_dropship.order_note') or ''
        address = self._dropship_address()
        # group dropship lines by provider so each provider gets one order
        by_provider = {}
        for line in self.order_line.filtered(lambda l: l.product_id.is_dropship):
            ds = line.product_id.product_tmpl_id.dropship_product_id
            if not ds:
                continue
            variants = json.loads(ds.variants_json or '[]')
            sku_attr = (variants[0].get('attrs') if variants else '') or ''
            by_provider.setdefault(ds.provider_id, []).append({
                'product_id': ds.source_id,
                'product_count': int(line.product_uom_qty),
                'sku_attr': sku_attr,
                'logistics_service_name': 'CAINIAO_FULFILLMENT_STD',
                'order_memo': note,
            })

        refs = []
        errors = []
        for provider, items in by_provider.items():
            try:
                result = provider._adapter().place_order({'address': address, 'items': items})
                if result.get('provider_order_id'):
                    refs.append(result['provider_order_id'])
                    self.dropship_status = result.get('status')
                else:
                    msg = (self._extract_provider_error(result)
                           or result.get('status') or 'placement rejected')
                    self.dropship_status = msg[:255]
                    errors.append('%s: %s' % (provider.name, msg))
            except Exception as e:  # noqa: BLE001 - provider failure must not break the sale
                _logger.warning("Dropship order placement failed for %s: %s", self.name, e)
                self.dropship_status = 'error'
                errors.append('%s: %s' % (provider.name, str(e)[:150]))
        if refs:
            self.dropship_order_ref = ', '.join(refs)
        return errors

    def _extract_provider_error(self, result):
        """Dig the human error_msg out of the AliExpress DS place_order reply."""
        raw = (result or {}).get('raw') or {}
        try:
            return raw['aliexpress_ds_order_create_response']['result']['error_msg']
        except Exception:  # noqa: BLE001
            return None

    def _dropship_address(self):
        """Map the Odoo shipping partner to the AliExpress DS address schema.

        AliExpress validates the zip as a numeric postal code — a customer's
        free-text zip (often an Arabic governorate name) fails validation, so we
        keep only digits and fall back to the configured default zip.
        """
        p = self.partner_shipping_id
        ICP = self.env['ir.config_parameter'].sudo()
        default_zip = ICP.get_param('uellow_dropship.default_zip') or '00000'
        zip_digits = ''.join(ch for ch in (p.zip or '') if ch.isdigit())
        return {
            'country': p.country_id.code or 'KW',
            'province': p.state_id.name or (p.city or ''),
            'city': p.city or '',
            'address': ' '.join(filter(None, [p.street, p.street2])) or '-',
            'contact_person': p.name or '',
            'full_name': p.name or '',
            'mobile_no': (p.mobile or p.phone or '').lstrip('+'),
            'phone_country': '+%s' % (p.country_id.phone_code or 965),
            'zip': zip_digits or default_zip,
        }
