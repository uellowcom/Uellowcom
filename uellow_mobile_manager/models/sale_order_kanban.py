# -*- coding: utf-8 -*-
"""Computed helpers for the rich Sales KANBAN card (design C+).

All labels follow the *current UI language*: English page → English only,
Arabic page → Arabic only (never mixed).
"""
from datetime import datetime

from odoo import api, fields, models


class SaleOrderKanban(models.Model):
    _inherit = 'sale.order'

    # ── source of sale (App / Web / POS / Back-office) ──────────────────
    uellow_source = fields.Char(string='Source', compute='_compute_uellow_kanban')
    uellow_source_class = fields.Char(compute='_compute_uellow_kanban')
    # ── age ─────────────────────────────────────────────────────────────
    uellow_age_label = fields.Char(string='Age', compute='_compute_uellow_kanban')
    uellow_stale = fields.Boolean(compute='_compute_uellow_kanban')
    # ── payment / delivery / invoice (label + css class) ────────────────
    uellow_pay_label = fields.Char(compute='_compute_uellow_kanban')
    uellow_pay_class = fields.Char(compute='_compute_uellow_kanban')
    uellow_pay_method = fields.Char(compute='_compute_uellow_kanban')
    uellow_deliv_label = fields.Char(compute='_compute_uellow_kanban')
    uellow_deliv_class = fields.Char(compute='_compute_uellow_kanban')
    uellow_deliv_extra = fields.Char(compute='_compute_uellow_kanban')
    uellow_inv_label = fields.Char(compute='_compute_uellow_kanban')
    uellow_inv_class = fields.Char(compute='_compute_uellow_kanban')
    uellow_state_label = fields.Char(compute='_compute_uellow_kanban')
    uellow_state_class = fields.Char(compute='_compute_uellow_kanban')
    # ── extras ──────────────────────────────────────────────────────────
    uellow_cod_amount = fields.Monetary(compute='_compute_uellow_kanban',
                                        currency_field='currency_id')
    uellow_is_new_customer = fields.Boolean(compute='_compute_uellow_kanban')
    uellow_items_count = fields.Integer(compute='_compute_uellow_kanban')
    uellow_city = fields.Char(compute='_compute_uellow_kanban')
    uellow_phone = fields.Char(compute='_compute_uellow_kanban')
    uellow_has_return = fields.Boolean(compute='_compute_uellow_kanban')
    uellow_margin_pct = fields.Integer(compute='_compute_uellow_kanban')
    uellow_can_confirm = fields.Boolean(compute='_compute_uellow_kanban')
    # ── custom kanban grouping stage (stored, ordered columns) ──────────
    uellow_stage = fields.Selection([
        ('quotation', 'Quotation'),
        ('quotation_sent', 'Quotation Sent'),
        ('sales_order', 'Sales Order'),
        ('assigned', 'Assigned to Carrier'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancel', 'Cancelled'),
    ], string='Stage', compute='_compute_uellow_stage', store=True,
        group_expand='_expand_uellow_stage')

    @api.depends('state', 'delivery_status')
    def _compute_uellow_stage(self):
        for o in self:
            ds = getattr(o, 'delivery_status', False)
            if o.state == 'cancel':
                o.uellow_stage = 'cancel'
            elif o.state == 'draft':
                o.uellow_stage = 'quotation'
            elif o.state == 'sent':
                o.uellow_stage = 'quotation_sent'
            elif ds == 'delivered':
                o.uellow_stage = 'delivered'
            elif ds == 'out_for_delivery':
                o.uellow_stage = 'out_for_delivery'
            elif ds in ('assigned', 'accepted'):
                o.uellow_stage = 'assigned'
            else:
                # confirmed but not yet dispatched (pending / sorting / failed)
                o.uellow_stage = 'sales_order'

    @api.model
    def _expand_uellow_stage(self, values, domain, order=None):
        # always show all columns, in this order
        return ['quotation', 'quotation_sent', 'sales_order', 'assigned',
                'out_for_delivery', 'delivered', 'cancel']
    # ── localized static UI strings (follow page language) ──────────────
    uellow_t_new = fields.Char(compute='_compute_uellow_kanban')
    uellow_t_cod = fields.Char(compute='_compute_uellow_kanban')
    uellow_t_return = fields.Char(compute='_compute_uellow_kanban')
    uellow_t_confirm = fields.Char(compute='_compute_uellow_kanban')
    uellow_t_cancel = fields.Char(compute='_compute_uellow_kanban')

    @api.depends('state', 'website_id', 'payment_method_type', 'invoice_status',
                 'amount_total', 'partner_id', 'order_line', 'date_order',
                 'create_date')
    def _compute_uellow_kanban(self):
        now = datetime.now()
        lang = self.env.context.get('lang') or self.env.user.lang or 'en_US'
        is_ar = lang.startswith('ar')

        def L(en, ar):
            return ar if is_ar else en

        # Pre-count confirmed orders per partner in ONE query (avoid N+1
        # search_count per card which made the Sales kanban load slowly).
        pids = self.mapped('partner_id').ids
        order_counts = {}
        if pids:
            for grp in self.env['sale.order'].read_group(
                    [('partner_id', 'in', pids), ('state', 'in', ('sale', 'done'))],
                    ['partner_id'], ['partner_id']):
                if grp.get('partner_id'):
                    order_counts[grp['partner_id'][0]] = grp['partner_id_count']

        for o in self:
            # localized static strings
            o.uellow_t_new = L('New', 'جديد')
            o.uellow_t_cod = L('Collect cash', 'تحصيل كاش')
            o.uellow_t_return = L('Return', 'مرتجع')
            o.uellow_t_confirm = L('Confirm', 'اعتماد')
            o.uellow_t_cancel = L('Cancel', 'إلغاء')

            # source
            wname = (o.website_id.name or '') if o.website_id else ''
            if 'app' in wname.lower():
                o.uellow_source = '📱 ' + wname
                o.uellow_source_class = 'sapp'
            elif o.website_id:
                o.uellow_source = '🌐 ' + wname
                o.uellow_source_class = 'sweb'
            elif getattr(o, 'pos_order_count', 0):
                o.uellow_source = '🧾 POS'
                o.uellow_source_class = 'spos'
            else:
                o.uellow_source = L('🏢 Back-office', '🏢 إدارة')
                o.uellow_source_class = 'sback'

            # age
            base = o.date_order or o.create_date
            if base:
                hrs = (now - base).total_seconds() / 3600.0
                if hrs < 1:
                    n = max(1, int(hrs * 60))
                    o.uellow_age_label = L('%dm ago' % n, 'منذ %d د' % n)
                elif hrs < 48:
                    n = int(hrs)
                    o.uellow_age_label = L('%dh ago' % n, 'منذ %d س' % n)
                else:
                    n = int(hrs / 24)
                    o.uellow_age_label = L('%dd ago' % n, 'منذ %d يوم' % n)
                o.uellow_stale = (o.state in ('sale', 'done')
                                  and getattr(o, 'delivery_status', 'pending')
                                  in ('pending', False, 'arrived_sorting')
                                  and hrs > 24)
            else:
                o.uellow_age_label = ''
                o.uellow_stale = False

            # order state
            st = {
                'draft': (L('Draft', 'مسودة'), 'k-grey'),
                'sent': (L('Quotation', 'عرض سعر'), 'k-grey'),
                'sale': (L('Confirmed', 'مؤكد'), 'k-green'),
                'done': (L('Done', 'مكتمل'), 'k-green'),
                'cancel': (L('Cancelled', 'ملغي'), 'k-red'),
            }.get(o.state, (o.state, 'k-grey'))
            o.uellow_state_label, o.uellow_state_class = st
            o.uellow_can_confirm = o.state in ('draft', 'sent')

            # payment
            pmt = getattr(o, 'payment_method_type', None)
            paid = False
            try:
                paid = any(t.state in ('done', 'authorized')
                           for t in o.transaction_ids)
            except Exception:
                paid = False
            if pmt == 'cash':
                o.uellow_pay_method = L('Cash on delivery', 'كاش عند الاستلام')
                if paid:
                    o.uellow_pay_label, o.uellow_pay_class = L('Paid', 'مدفوع'), 'k-green'
                else:
                    o.uellow_pay_label, o.uellow_pay_class = L('Collect on delivery', 'تحصيل عند الاستلام'), 'k-amber'
                o.uellow_cod_amount = o.amount_total if not paid else 0.0
            elif pmt == 'free':
                o.uellow_pay_method = L('Free', 'مجاني')
                o.uellow_pay_label, o.uellow_pay_class = L('Free', 'مجاني'), 'k-grey'
                o.uellow_cod_amount = 0.0
            else:
                o.uellow_pay_method = L('Online', 'أونلاين')
                if paid:
                    o.uellow_pay_label, o.uellow_pay_class = L('Paid', 'مدفوع'), 'k-green'
                else:
                    o.uellow_pay_label, o.uellow_pay_class = L('Unpaid', 'غير مدفوع'), 'k-red'
                o.uellow_cod_amount = 0.0

            # delivery
            ds = getattr(o, 'delivery_status', False) or 'pending'
            dmap = {
                'pending': (L('Unassigned', 'لم يُسند'), 'k-grey'),
                'arrived_sorting': (L('At sorting center', 'في مركز الفرز'), 'k-blue'),
                'assigned': (L('Assigned', 'مُسند لسائق'), 'k-blue'),
                'accepted': (L('Accepted by driver', 'قبله السائق'), 'k-blue'),
                'out_for_delivery': (L('Out for delivery', 'خرج للتوصيل'), 'k-amber'),
                'delivered': (L('Delivered', 'تم التسليم'), 'k-green'),
                'failed': (L('Failed', 'فشل التوصيل'), 'k-red'),
                'failed_returned': (L('Failed & returned', 'فشل ومرتجع'), 'k-red'),
            }
            o.uellow_deliv_label, o.uellow_deliv_class = dmap.get(ds, (ds, 'k-grey'))
            extra = []
            cc = getattr(o, 'delivery_carrier_company_id', False)
            if cc:
                extra.append(cc.name)
            dr = getattr(o, 'delivery_driver_id', False)
            if dr:
                extra.append(L('Driver: ', 'سائق: ') + (dr.name or ''))
            o.uellow_deliv_extra = ' · '.join(extra)

            # invoice
            imap = {
                'invoiced': (L('Invoiced', 'تم الفوترة'), 'k-green'),
                'to invoice': (L('To invoice', 'بانتظار الفوترة'), 'k-amber'),
                'no': (L('No invoice', 'لا فوترة'), 'k-grey'),
                'upselling': (L('Upselling', 'فرصة بيع'), 'k-blue'),
            }
            o.uellow_inv_label, o.uellow_inv_class = imap.get(
                o.invoice_status, (o.invoice_status or '', 'k-grey'))

            # extras
            o.uellow_items_count = int(sum(o.order_line.filtered(
                lambda l: not l.display_type).mapped('product_uom_qty')))
            ship = o.partner_shipping_id or o.partner_id
            o.uellow_city = (ship.city or '') if ship else ''
            o.uellow_phone = (o.partner_id.phone or o.partner_id.mobile or '') \
                if o.partner_id else ''
            o.uellow_has_return = bool(getattr(o, 'return_status', False)
                                       and o.return_status not in (False, 'none'))
            # new customer = this partner's only confirmed order (pre-counted)
            o.uellow_is_new_customer = order_counts.get(o.partner_id.id, 0) <= 1
            # margin %
            try:
                cost = sum((getattr(l, 'purchase_price', 0.0) or 0.0)
                           * l.product_uom_qty for l in o.order_line)
                unt = o.amount_untaxed or 0.0
                o.uellow_margin_pct = int(round((unt - cost) / unt * 100.0)) if unt else 0
            except Exception:
                o.uellow_margin_pct = 0
