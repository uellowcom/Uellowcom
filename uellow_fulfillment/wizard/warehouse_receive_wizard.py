from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class WarehouseReceiveWizard(models.TransientModel):
    """
    Wizard: موظف المستودع يُدخل الكميات الفعلية المستلمة لكل variant.
    On confirm:
    1. Updates qty_received / qty_damaged on each restock line
    2. Creates stock.move for accepted qty into WH/VND sub-location
    3. Closes PO (sets qty_received on PO lines)
    4. Sets request state = 'received'
    5. Recomputes fbu_state on each product.product
    """
    _name = 'uellow.warehouse.receive.wizard'
    _description = 'استلام مخزون FBU'

    request_id = fields.Many2one(
        'uellow.restock.request', string='طلب التزويد',
        required=True, ondelete='cascade',
    )
    partner_id = fields.Many2one(
        related='request_id.partner_id', readonly=True,
    )
    location_id = fields.Many2one(
        related='request_id.location_id', readonly=True,
    )
    line_ids = fields.One2many(
        'uellow.warehouse.receive.wizard.line', 'wizard_id',
        string='السطور',
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        req_id = self.env.context.get('default_request_id')
        if req_id:
            req = self.env['uellow.restock.request'].browse(req_id)
            lines = []
            for l in req.line_ids:
                lines.append((0, 0, {
                    'restock_line_id': l.id,
                    'product_id': l.product_id.id,
                    'variant_description': l.variant_description,
                    'qty_requested': l.qty_requested,
                    'qty_received': l.qty_requested,  # default = requested
                    'qty_accepted': l.qty_requested,
                    'qty_damaged': 0,
                }))
            vals['line_ids'] = lines
        return vals

    def action_confirm_receipt(self):
        self.ensure_one()
        req = self.request_id
        if req.state != 'approved':
            raise UserError(_('الطلب يجب أن يكون في حالة "موافق" لتأكيد الاستلام.'))

        loc_dest = req.location_id
        if not loc_dest:
            raise UserError(_('لا يوجد موقع استلام محدد لهذا الطلب.'))

        # Source: supplier location
        supplier_loc = self.env['stock.location'].search(
            [('usage', '=', 'supplier')], limit=1)
        if not supplier_loc:
            raise UserError(_('لا يوجد موقع مورد. تحقق من إعدادات المخزون.'))

        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id.lot_stock_id', '=', loc_dest.id),
        ], limit=1)
        if not picking_type:
            # Fallback: any incoming
            picking_type = self.env['stock.picking.type'].search(
                [('code', '=', 'incoming')], limit=1)

        # Create picking
        picking_vals = {
            'partner_id': req.partner_id.id,
            'picking_type_id': picking_type.id if picking_type else False,
            'location_id': supplier_loc.id,
            'location_dest_id': loc_dest.id,
            'fbu_restock_id': req.id,
            'origin': req.name,
            'move_ids': [],
        }

        moves = []
        for wline in self.line_ids:
            accepted = max(0, wline.qty_received - wline.qty_damaged)
            if accepted <= 0:
                continue
            moves.append((0, 0, {
                'name': wline.product_id.display_name,
                'product_id': wline.product_id.id,
                'product_uom_qty': accepted,
                'product_uom': wline.product_id.uom_id.id,
                'location_id': supplier_loc.id,
                'location_dest_id': loc_dest.id,
            }))
        picking_vals['move_ids'] = moves

        if moves:
            picking = self.env['stock.picking'].create(picking_vals)
            picking.action_confirm()
            for move in picking.move_ids:
                move.quantity = move.product_uom_qty
            picking.button_validate()

        # Update restock lines
        for wline in self.line_ids:
            accepted = max(0, wline.qty_received - wline.qty_damaged)
            wline.restock_line_id.write({
                'qty_received': wline.qty_received,
                'qty_damaged': wline.qty_damaged,
                'difference_reason': wline.difference_reason,
                'difference_note': wline.difference_note,
            })
            # Trigger fbu_state recompute on product.product
            wline.product_id._compute_fbu_state()

        # Update PO received qty
        if req.purchase_order_id:
            for po_line in req.purchase_order_id.order_line:
                matched = self.line_ids.filtered(
                    lambda l: l.product_id == po_line.product_id)
                if matched:
                    received = sum(matched.mapped('qty_received'))
                    po_line.qty_received = received

        req.state = 'received'
        req.message_post(body=_(
            'تم تأكيد استلام المخزون. إجمالي الوحدات المقبولة: %d') % sum(
            max(0, l.qty_received - l.qty_damaged) for l in self.line_ids))

        return {'type': 'ir.actions.act_window_close'}


class WarehouseReceiveWizardLine(models.TransientModel):
    _name = 'uellow.warehouse.receive.wizard.line'
    _description = 'سطر استلام Wizard'

    wizard_id = fields.Many2one('uellow.warehouse.receive.wizard', ondelete='cascade')
    restock_line_id = fields.Many2one('uellow.restock.request.line', readonly=True)
    product_id = fields.Many2one('product.product', string='المنتج (Variant)', readonly=True)
    variant_description = fields.Char('اللون/الحجم', readonly=True)
    qty_requested = fields.Integer('مطلوب', readonly=True)
    qty_received = fields.Integer('وصل فعلاً', required=True)
    qty_accepted = fields.Integer('مقبول', compute='_compute_accepted', store=True)
    qty_damaged = fields.Integer('تالف/ناقص', default=0)
    difference_reason = fields.Selection([
        ('shortage', 'نقص في الشحنة'),
        ('damaged', 'تالف'),
        ('count_error', 'خطأ عد'),
        ('other', 'أخرى'),
    ], string='سبب الفرق')
    difference_note = fields.Char('ملاحظة')

    @api.depends('qty_received', 'qty_damaged')
    def _compute_accepted(self):
        for l in self:
            l.qty_accepted = max(0, l.qty_received - l.qty_damaged)
