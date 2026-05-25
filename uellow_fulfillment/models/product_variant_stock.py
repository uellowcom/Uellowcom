from odoo import models, fields, api, _


class ProductProduct(models.Model):
    """
    Extend product.product with:
    - vendor_qty: units the vendor has at THEIR OWN warehouse (Continue Selling)
    - continue_selling: computed True if vendor_qty > 0
    - fbu_state: on_hand | continue_selling | out_of_stock
    - vendor_location_id: which FBU sub-location holds this product
    """
    _inherit = 'product.product'

    vendor_qty = fields.Integer(
        string='كمية التاجر الخارجية',
        default=0,
        help='عدد الوحدات في مستودع التاجر الخاص. إذا أصبح صفراً يُعطَّل Continue Selling.',
    )
    continue_selling = fields.Boolean(
        string='Continue Selling',
        compute='_compute_continue_selling',
        store=True,
        help='True إذا vendor_qty > 0',
    )
    fbu_state = fields.Selection([
        ('on_hand',         'On Hand'),
        ('continue_selling', 'Continue Selling'),
        ('out_of_stock',    'Out of Stock'),
    ], compute='_compute_fbu_state', store=True, string='حالة المخزون')

    fbu_qty_onhand = fields.Float(
        compute='_compute_fbu_qty',
        string='كمية WH/VND',
    )

    vendor_partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        index=True,
        help='التاجر المالك لهذا المنتج. فارغ = منتج Uellow المباشر.',
    )

    @api.depends('vendor_qty')
    def _compute_continue_selling(self):
        for p in self:
            p.continue_selling = p.vendor_qty > 0

    def _get_fbu_location(self):
        """Return the vendor sub-location for this product (if any)."""
        if not self.vendor_partner_id:
            return None
        vl = self.env['uellow.vendor.location'].search([
            ('partner_id', '=', self.vendor_partner_id.id),
            ('state', '=', 'active'),
        ], limit=1)
        return vl.location_id if vl else None

    def _compute_fbu_qty(self):
        for p in self:
            loc = p._get_fbu_location()
            if loc:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', p.id),
                    ('location_id', '=', loc.id),
                ], limit=1)
                p.fbu_qty_onhand = quant.quantity if quant else 0.0
            else:
                p.fbu_qty_onhand = 0.0

    @api.depends('vendor_qty', 'fbu_qty_onhand')
    def _compute_fbu_state(self):
        for p in self:
            # Re-read fbu_qty_onhand (not stored)
            loc = p._get_fbu_location()
            fbu_qty = 0.0
            if loc:
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', p.id),
                    ('location_id', '=', loc.id),
                ], limit=1)
                fbu_qty = quant.quantity if quant else 0.0

            if fbu_qty > 0:
                p.fbu_state = 'on_hand'
            elif p.vendor_qty > 0:
                p.fbu_state = 'continue_selling'
            else:
                p.fbu_state = 'out_of_stock'

    def write(self, vals):
        """
        If vendor_qty is set to 0, auto-disable continue_selling.
        Optionally hide website product.
        """
        res = super().write(vals)
        if 'vendor_qty' in vals and vals['vendor_qty'] == 0:
            # Check if FBU stock also zero — if so, consider hiding
            for p in self:
                loc = p._get_fbu_location()
                fbu_qty = 0.0
                if loc:
                    quant = self.env['stock.quant'].search([
                        ('product_id', '=', p.id),
                        ('location_id', '=', loc.id),
                    ], limit=1)
                    fbu_qty = quant.quantity if quant else 0.0
                # Log state change
                if fbu_qty == 0:
                    p.message_post(body=_(
                        'تنبيه: الكمية الخارجية وFBU كلاهما صفر → Out of Stock'))
        return res
