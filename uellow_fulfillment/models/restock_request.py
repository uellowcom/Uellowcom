from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class RestockRequest(models.Model):
    """
    Vendor restock request — header record.
    Lines are in uellow.restock.request.line (one per product.product variant).
    On approval: a purchase.order is auto-created at 0.0 price (trust/consignment).
    On warehouse receipt: stock.move validates into vendor sub-location.
    """
    _name = 'uellow.restock.request'
    _description = 'طلب تزويد المخزون'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char(
        'رقم الطلب', required=True,
        copy=False, readonly=True, default='جديد',
    )
    vendor_location_id = fields.Many2one(
        'uellow.vendor.location', string='Vendor Sub-warehouse',
        required=True, ondelete='restrict', index=True,
    )
    partner_id = fields.Many2one(
        related='vendor_location_id.partner_id',
        string='Vendor', store=True, readonly=True,
    )
    location_id = fields.Many2one(
        related='vendor_location_id.location_id',
        string='Receiving Location', store=True, readonly=True,
    )
    state = fields.Selection([
        ('draft',     'مسودة'),
        ('submitted', 'بانتظار الموافقة'),
        ('approved',  'موافق — بانتظار التسليم'),
        ('received',  'تم الاستلام'),
        ('cancelled', 'ملغي'),
    ], default='draft', string='State', tracking=True, index=True)

    expected_date = fields.Date('تاريخ التسليم المتوقع', required=True)
    pickup_date = fields.Date('تاريخ التسليم/الاستلام المقترح من التاجر')
    confirmed_date = fields.Date('تاريخ الاستلام المؤكد (من Uellow)')
    transport_method = fields.Selection([
        ('self', 'التاجر يوصّل بنفسه'),
        ('carrier', 'شركة شحن (التاجر يدفع)'),
        ('uellow', 'Uellow تستلم (رسوم إضافية)'),
    ], default='self', string='Transport Method')

    notes = fields.Text('ملاحظات للمستودع')
    admin_notes = fields.Text('ملاحظات Uellow Admin')

    line_ids = fields.One2many(
        'uellow.restock.request.line', 'request_id',
        string='Lines', copy=True,
    )
    purchase_order_id = fields.Many2one(
        'purchase.order', string='Linked Purchase Order',
        readonly=True, copy=False,
    )

    total_variants = fields.Integer(compute='_compute_totals', string='Variant Count')
    total_units = fields.Integer(compute='_compute_totals', string='Total Units')

    @api.depends('line_ids.qty_requested')
    def _compute_totals(self):
        for r in self:
            r.total_variants = len(r.line_ids)
            r.total_units = sum(r.line_ids.mapped('qty_requested'))

    # ── ORM ───────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'جديد') == 'جديد':
                vals['name'] = self.env['ir.sequence'].next_by_code('uellow.restock.request') or 'جديد'
        return super().create(vals_list)

    # ── Transitions ───────────────────────────────────────

    def action_submit(self):
        for r in self:
            if not r.line_ids:
                raise UserError(_('أضف منتجاً على الأقل قبل الإرسال.'))
            r.state = 'submitted'
            r.message_post(body=_('تم إرسال الطلب للموافقة.'))

    def action_approve(self):
        for r in self:
            r.state = 'approved'
            po = r._create_purchase_order()
            r.purchase_order_id = po
            # Confirm the PO so its OWN receipt picking is the single stock op,
            # and route that receipt into the request's vendor sub-location so
            # the PO warehouse matches the request (no mismatch, no duplication).
            try:
                po.button_confirm()
                if r.location_id:
                    picks = po.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
                    picks.write({'location_dest_id': r.location_id.id})
                    picks.move_ids.write({'location_dest_id': r.location_id.id})
                    picks.move_line_ids.write({'location_dest_id': r.location_id.id})
            except Exception:
                _logger.exception('Restock PO confirm/route failed for %s', r.name)
            r.message_post(body=_(
                'تمت الموافقة. طلب الشراء المرتبط: %s') % po.name)

    def action_cancel(self):
        for r in self:
            if r.state == 'received':
                raise UserError(_('لا يمكن إلغاء طلب تم استلامه.'))
            r.state = 'cancelled'

    def action_receive(self):
        """Open warehouse receive wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'استلام المخزون',
            'res_model': 'uellow.warehouse.receive.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    # ── PO creation ──────────────────────────────────────

    def _create_purchase_order(self):
        """
        Creates a purchase.order priced at the product cost (so the PO shows
        real prices, not zeros). Its incoming picking type is the warehouse that
        owns the request's receiving location, so the PO warehouse matches the
        request. One PO line per restock request line (product.product variant).
        """
        self.ensure_one()
        # Pick the incoming type of the warehouse that owns the receiving loc.
        picking_type = False
        if self.location_id:
            wh = self.env['stock.warehouse'].sudo().search(
                [('lot_stock_id', 'parent_of', self.location_id.id)], limit=1) \
                or self.env['stock.warehouse'].sudo().search([], limit=1)
            if wh:
                picking_type = self.env['stock.picking.type'].sudo().search(
                    [('code', '=', 'incoming'), ('warehouse_id', '=', wh.id)], limit=1)
        po_vals = {
            'partner_id': self.partner_id.id,
            'date_order': fields.Datetime.now(),
            'date_planned': self.expected_date,
            'origin': self.name,
            'notes': f'FBU — {self.name} — {self.partner_id.name}\n{self.notes or ""}',
            'order_line': [],
        }
        if picking_type:
            po_vals['picking_type_id'] = picking_type.id
        for line in self.line_ids:
            prod = line.product_id
            po_vals['order_line'].append((0, 0, {
                'product_id': prod.id,
                'name': f'[FBU] {prod.display_name}',
                'product_qty': line.qty_requested,
                'price_unit': prod.standard_price or 0.0,
                'date_planned': self.expected_date,
                'product_uom': prod.uom_po_id.id or prod.uom_id.id,
            }))
        return self.env['purchase.order'].create(po_vals)
