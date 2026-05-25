from odoo import models, fields, api, _


class RestockRequestLine(models.Model):
    """
    One line per product.product (variant) per restock request.
    Tracks: qty_requested, qty_received, qty_damaged.
    """
    _name = 'uellow.restock.request.line'
    _description = 'سطر طلب التزويد (Variant)'
    _order = 'request_id, id'

    request_id = fields.Many2one(
        'uellow.restock.request', string='الطلب',
        required=True, ondelete='cascade', index=True,
    )
    product_id = fields.Many2one(
        'product.product', string='المنتج (Variant)',
        required=True, ondelete='restrict',
        domain=[('type', '=', 'product')],
    )
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id',
        string='المنتج الأب', store=True, readonly=True,
    )
    # Color / size attributes for display
    variant_description = fields.Char(
        compute='_compute_variant_description',
        string='اللون/الحجم', store=True,
    )

    qty_requested = fields.Integer('الكمية المطلوبة', required=True, default=1)
    qty_received = fields.Integer('الكمية المستلمة', default=0, readonly=True)
    qty_damaged = fields.Integer('التالف/الناقص', default=0, readonly=True)
    qty_accepted = fields.Integer(
        compute='_compute_qty_accepted',
        string='المقبول', store=True,
    )

    # Current FBU stock for reference
    fbu_qty_onhand = fields.Float(
        compute='_compute_fbu_qty',
        string='في WH/VND الآن',
    )

    difference_reason = fields.Selection([
        ('shortage', 'نقص في الشحنة'),
        ('damaged', 'تالف عند الاستلام'),
        ('count_error', 'خطأ في العد'),
        ('other', 'أخرى'),
    ], string='سبب الفرق')
    difference_note = fields.Char('ملاحظة الفرق')

    @api.depends('product_id')
    def _compute_variant_description(self):
        for line in self:
            if line.product_id:
                attrs = line.product_id.product_template_attribute_value_ids
                line.variant_description = ' · '.join(attrs.mapped('name')) if attrs else ''
            else:
                line.variant_description = ''

    @api.depends('qty_received', 'qty_damaged')
    def _compute_qty_accepted(self):
        for line in self:
            line.qty_accepted = max(0, line.qty_received - line.qty_damaged)

    def _compute_fbu_qty(self):
        for line in self:
            loc = line.request_id.location_id
            if loc and line.product_id:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', loc.id),
                ], limit=1)
                line.fbu_qty_onhand = quant.quantity if quant else 0.0
            else:
                line.fbu_qty_onhand = 0.0
