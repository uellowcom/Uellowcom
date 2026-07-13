# -*- coding: utf-8 -*-
"""Manual stock adjustment audit log (Admin Console → product → stock).

Every on-hand quantity change made from the in-app 🛡️ admin console is
recorded here with a mandatory REASON, so the physical count can always be
reconciled against an auditable trail ("who set it to what, and why").

The real inventory change is applied via ``stock.quant`` inventory adjustment
(see ``admin_product_stock_adjust`` in ``controllers/api_v2/admin_app.py``);
this model only stores the reasoned audit row that Odoo's native adjustment
does not keep.
"""
from odoo import api, fields, models


class UellowStockAdjust(models.Model):
    _name = 'uellow.stock.adjust'
    _description = 'Admin Stock Adjustment Log'
    _order = 'create_date desc, id desc'

    product_id = fields.Many2one('product.product', string='Variant',
                                 required=True, ondelete='cascade', index=True)
    template_id = fields.Many2one('product.template',
                                  related='product_id.product_tmpl_id',
                                  store=True, index=True, string='Product')
    location_id = fields.Many2one('stock.location', string='Location')
    qty_before = fields.Float('Qty Before', digits='Product Unit of Measure')
    qty_after = fields.Float('Qty After', digits='Product Unit of Measure')
    delta = fields.Float('Change', digits='Product Unit of Measure')
    reason = fields.Text('Reason / السبب', required=True)
    user_id = fields.Many2one('res.users', string='By',
                              default=lambda s: s.env.user)
    source = fields.Char('Source', default='admin_app')

    @api.model
    def log(self, product, location, before, after, reason, user=None):
        """Create one audit row (best-effort — never blocks the adjustment)."""
        return self.sudo().create({
            'product_id': product.id,
            'location_id': location.id if location else False,
            'qty_before': before,
            'qty_after': after,
            'delta': (after or 0.0) - (before or 0.0),
            'reason': (reason or '').strip() or '—',
            'user_id': (user or self.env.user).id,
        })
