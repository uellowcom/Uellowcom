from odoo import models, fields, api, _


class StockPicking(models.Model):
    """
    Link stock.picking to a restock request.
    """
    _inherit = 'stock.picking'

    fbu_restock_id = fields.Many2one(
        'uellow.restock.request',
        string='طلب تزويد FBU',
        index=True, copy=False,
    )
    is_fbu = fields.Boolean(
        string='FBU استلام',
        compute='_compute_is_fbu',
        store=True,
    )

    @api.depends('fbu_restock_id')
    def _compute_is_fbu(self):
        for p in self:
            p.is_fbu = bool(p.fbu_restock_id)
