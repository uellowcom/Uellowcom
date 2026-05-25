from odoo import models, fields, api, _


class ProductMapping(models.Model):
    """
    Maps supplier product codes (SKU/barcode) to our product.template.
    Used by Smart Connector to auto-link imported products to existing catalog.
    Also tracks supplier price updates over time.
    """
    _name = 'uellow.product.mapping'
    _description = 'ربط منتجات المورد بالكتالوج'
    _rec_name = 'supplier_sku'

    product_id = fields.Many2one(
        'product.template', required=True, ondelete='cascade',
        string='المنتج في كتالوج Uellow',
    )
    supplier_partner_id = fields.Many2one(
        'res.partner', string='المورد/التاجر', ondelete='restrict',
    )
    supplier_sku = fields.Char('SKU المورد', required=True, index=True)
    supplier_barcode = fields.Char('Barcode المورد', index=True)
    supplier_name = fields.Char('اسم المنتج عند المورد')
    supplier_price = fields.Float('آخر سعر من المورد')
    last_sync = fields.Datetime('آخر مزامنة')
    sync_count = fields.Integer('عدد المزامنات', default=0)

    _sql_constraints = [
        ('unique_sku_supplier', 'UNIQUE(supplier_sku, supplier_partner_id)',
         'SKU المورد يجب أن يكون فريداً لكل مورد.'),
    ]

    @api.model
    def find_or_create_mapping(self, sku, supplier_id, product_id=False):
        """Look up mapping by SKU+supplier. Create if not found."""
        mapping = self.search([
            ('supplier_sku', '=', sku),
            ('supplier_partner_id', '=', supplier_id),
        ], limit=1)
        if not mapping and product_id:
            mapping = self.create({
                'supplier_sku': sku,
                'supplier_partner_id': supplier_id,
                'product_id': product_id,
            })
        return mapping

    def action_sync_price(self):
        """Update product list_price from latest supplier_price."""
        for rec in self:
            if rec.supplier_price > 0:
                rec.product_id.list_price = rec.supplier_price
                rec.last_sync = fields.Datetime.now()
                rec.sync_count += 1
