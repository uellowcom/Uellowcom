# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # thumbnail shown in the SO order-line list
    uc_product_image = fields.Binary(
        related='product_id.image_128', string='Image', store=False)

    def _get_sale_order_line_multiline_description_sale(self):
        # Show ONLY the product name on the order line — strip the sales
        # description and the multiline variant block (per request).
        if self.product_id and not self.display_type:
            return self.product_id.with_context(display_default_code=False).display_name
        return super()._get_sale_order_line_multiline_description_sale()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ------------------------------------------------------------------
    # Warehouse preparation lifecycle (sits BEFORE the delivery lifecycle).
    # delivery_status (delivery_carrier_portal) takes over once the pickup
    # courier collects the order -> we then mirror it to 'picked_up'.
    # ------------------------------------------------------------------
    preparation_state = fields.Selection(
        selection=[
            ('to_prepare', 'To Prepare / بانتظار التجهيز'),
            ('preparing', 'Preparing / جاري التجهيز'),
            ('ready_for_pickup', 'Ready for Pickup / جاهز للاستلام'),
            ('picked_up', 'Picked Up / تم الاستلام'),
        ],
        string='Preparation Status / حالة التجهيز',
        default='to_prepare',
        copy=False,
        tracking=True,
        index=True,
        help='Warehouse order-preparation stage. After "Ready for Pickup" '
             'the existing pickup/delivery flow takes over.',
    )
    preparation_done_by = fields.Many2one(
        'res.users', string='Prepared By / جهّزه', copy=False, readonly=True)
    preparation_done_date = fields.Datetime(
        string='Prepared On / تاريخ التجهيز', copy=False, readonly=True)

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        # When the pickup courier collects (delivery_status -> picked_up),
        # close out the preparation stage so the order leaves the queue.
        if vals.get('delivery_status') == 'picked_up':
            to_sync = self.filtered(lambda o: o.preparation_state != 'picked_up')
            if to_sync:
                super(SaleOrder, to_sync).write({'preparation_state': 'picked_up'})
        return res

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if not order.preparation_state:
                order.preparation_state = 'to_prepare'
        return res

    # ------------------------------------------------------------------
    # Workflow buttons
    # ------------------------------------------------------------------
    def action_prep_start(self):
        for order in self:
            if order.state != 'sale':
                raise UserError(_('Only confirmed sales orders can be prepared.'))
            order.preparation_state = 'preparing'
        return True

    def action_prep_done(self):
        for order in self:
            if order.state != 'sale':
                raise UserError(
                    _('Only confirmed sales orders can be marked ready for pickup.'))
            order.write({
                'preparation_state': 'ready_for_pickup',
                'preparation_done_by': self.env.user.id,
                'preparation_done_date': fields.Datetime.now(),
            })
            order.message_post(
                body=_('✅ Order prepared and marked Ready for Pickup by %s '
                       '/ تم تجهيز الطلب وهو جاهز للاستلام.') % self.env.user.name)
        return True

    def action_prep_reset(self):
        for order in self:
            order.write({
                'preparation_state': 'to_prepare',
                'preparation_done_by': False,
                'preparation_done_date': False,
            })
        return True

    # ------------------------------------------------------------------
    # Print helpers (everything from the order screen)
    # ------------------------------------------------------------------
    def _prep_report(self, xmlid, records, missing_msg):
        if not records:
            raise UserError(missing_msg)
        report = self.env.ref(xmlid, raise_if_not_found=False)
        if not report:
            raise UserError(_('Report not available: %s') % xmlid)
        return report.report_action(records)

    def action_prep_print_order(self):
        self.ensure_one()
        return self._prep_report(
            'sale.action_report_saleorder', self,
            _('Sale order report not found.'))

    def action_prep_print_invoices(self):
        self.ensure_one()
        invoices = self.invoice_ids.filtered(lambda m: m.state == 'posted') \
            or self.invoice_ids
        return self._prep_report(
            'account.account_invoices', invoices,
            _('This order has no invoice yet / لا توجد فاتورة لهذا الطلب بعد.'))

    def action_prep_print_label(self):
        self.ensure_one()
        return self._prep_report(
            'delivery_label.action_report_delivery_label', self.picking_ids,
            _('This order has no delivery to label yet / لا يوجد شحن لطباعة الليبل.'))

    def action_prep_print_receipt(self):
        self.ensure_one()
        return self._prep_report(
            'uellow_order_prep.action_report_sale_receipt', self,
            _('Sales receipt not available.'))

    def action_prep_print_warranty(self):
        self.ensure_one()
        return self._prep_report(
            'uellow_warranty.action_report_warranty_certificate',
            self.warranty_card_ids,
            _('This order has no warranty cards / لا توجد بطاقات ضمان لهذا الطلب.'))
