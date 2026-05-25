from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BarcodeReceiveSession(models.Model):
    """
    Active barcode receiving session for a restock request.
    Warehouse staff scans barcodes to confirm receipt variant by variant.
    """
    _name = 'uellow.barcode.session'
    _description = 'Barcode Receiving Session'
    _rec_name = 'request_id'

    request_id = fields.Many2one(
        'uellow.restock.request', required=True, ondelete='cascade',
    )
    user_id = fields.Many2one('res.users', default=lambda s: s.env.user.id)
    state = fields.Selection([
        ('open',   'Open'),
        ('closed', 'Closed'),
    ], default='open')
    started_at = fields.Datetime(default=fields.Datetime.now)
    closed_at = fields.Datetime()

    scan_ids = fields.One2many('uellow.barcode.scan', 'session_id', string='Scans')
    total_scanned = fields.Integer(compute='_compute_totals', string='Total Scanned')
    total_lines = fields.Integer(compute='_compute_totals', string='Total Lines')

    @api.depends('scan_ids')
    def _compute_totals(self):
        for s in self:
            s.total_scanned = len(s.scan_ids)
            s.total_lines = len(s.request_id.line_ids) if s.request_id else 0

    def action_close(self):
        """Validate all scans and update restock request."""
        self.ensure_one()
        for scan in self.scan_ids:
            if scan.product_id and scan.qty_scanned > 0:
                line = self.request_id.line_ids.filtered(
                    lambda l: l.product_id == scan.product_id)
                if line:
                    line.write({'qty_received': scan.qty_scanned})
        self.write({'state': 'closed', 'closed_at': fields.Datetime.now()})


class BarcodeScan(models.Model):
    """One scan event — product identified from barcode."""
    _name = 'uellow.barcode.scan'
    _description = 'Barcode Scan'
    _order = 'id desc'

    session_id = fields.Many2one('uellow.barcode.session', ondelete='cascade')
    barcode = fields.Char('Scanned Barcode')
    product_id = fields.Many2one('product.product', string='Identified Product')
    variant_description = fields.Char(related='product_id.display_name', readonly=True)
    qty_scanned = fields.Integer('Qty Scanned', default=1)
    scan_time = fields.Datetime(default=fields.Datetime.now)
    status = fields.Selection([
        ('ok',       'Matched'),
        ('unknown',  'Unknown Barcode'),
        ('mismatch', 'Not in Request'),
    ], default='ok')
