"""Dead-stock monitor — identifies products with stock but no recent sales."""
import logging
from datetime import timedelta

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

# Batch knob — commit after this many product checks so a 10k catalog can't
# lock stock.quant for the whole cron run.
_DEAD_STOCK_BATCH = 200


class DeadStockMonitor(models.Model):
    """
    Identifies products with stock but zero sales for N days.
    Cron runs weekly and generates alerts.
    """
    _name = 'uellow.dead.stock'
    _description = 'Dead Stock Monitoring'
    _rec_name = 'product_id'
    _order = 'days_since_last_sale desc'

    product_id = fields.Many2one(
        'product.product', required=True, ondelete='cascade',
        string='Product (Variant)', index=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        compute='_compute_product_info',
        store=True,
        string='Parent Product',
    )
    # NB: not store=True — vendor on the product can change after we cached,
    # which would silently leave the stored value stale (audit B5).
    vendor_partner_id = fields.Many2one(
        'res.partner',
        compute='_compute_product_info',
        string='Vendor',
    )

    qty_on_hand = fields.Float('Qty On Hand', readonly=True)
    last_sale_date = fields.Date('Last Sale', readonly=True)
    days_since_last_sale = fields.Integer('Days Since Last Sale', readonly=True)

    suggested_action = fields.Selection([
        ('discount',      'Flash Sale Discount'),
        ('bundle',        'Merge into Bundle'),
        ('return_vendor', 'Return to Vendor'),
        ('write_off',     'Write Off'),
        ('none',          'No Action'),
    ], default='discount', string='Suggested Action')

    state = fields.Selection([
        ('active',   'Stale'),
        ('resolved', 'Processed'),
        ('ignored',  'Ignored'),
    ], default='active', string='Status', index=True)

    alert_sent = fields.Boolean(default=False)

    _sql_constraints = [
        # B4: prevent duplicate active rows per product. Older resolved rows
        # are fine — we cascade or upsert via write() in the cron.
        ('uniq_product', 'unique(product_id)', 'A dead-stock row already exists for this product.'),
    ]

    @api.depends('product_id', 'product_id.product_tmpl_id', 'product_id.vendor_partner_id')
    def _compute_product_info(self):
        for rec in self:
            if rec.product_id:
                rec.product_tmpl_id = rec.product_id.product_tmpl_id
                rec.vendor_partner_id = getattr(rec.product_id, 'vendor_partner_id', False) or False
            else:
                rec.product_tmpl_id = False
                rec.vendor_partner_id = False

    @api.model
    def cron_scan_dead_stock(self):
        """Weekly cron: find products with stock but no recent sales.

        Performance fixes (A7/C1):
          - One `read_group` on stock.quant to get qty per product (was: N quants).
          - One `read_group` on stock.move to get last-sale per product (was: N searches).
          - Commit every `_DEAD_STOCK_BATCH` to release locks.
        """
        settings = self.env['uellow.connector.settings'].get_settings()
        days_threshold = int(settings.get('dead_stock_days') or 30)
        today = fields.Date.today()
        cutoff = today - timedelta(days=days_threshold)

        # 1) qty per product (one query)
        quant_groups = self.env['stock.quant'].read_group(
            domain=[('location_id.usage', '=', 'internal'), ('quantity', '>', 0)],
            fields=['product_id', 'quantity:sum'],
            groupby=['product_id'],
        )
        qty_by_product = {
            row['product_id'][0]: row['quantity'] or 0
            for row in quant_groups if row.get('product_id')
        }
        if not qty_by_product:
            return

        # 2) latest customer-bound move per product (one query)
        move_groups = self.env['stock.move'].read_group(
            domain=[
                ('product_id', 'in', list(qty_by_product.keys())),
                ('location_dest_id.usage', '=', 'customer'),
                ('state', '=', 'done'),
            ],
            fields=['product_id', 'date:max'],
            groupby=['product_id'],
        )
        last_sale_by_product = {}
        for row in move_groups:
            if row.get('product_id') and row.get('date'):
                d = row['date']
                last_sale_by_product[row['product_id'][0]] = (
                    d.date() if hasattr(d, 'date') else d
                )

        # 3) Walk products in batches, commit between chunks
        product_ids = list(qty_by_product.keys())
        processed = 0
        for i in range(0, len(product_ids), _DEAD_STOCK_BATCH):
            chunk = product_ids[i:i + _DEAD_STOCK_BATCH]
            self._process_dead_stock_chunk(
                chunk, qty_by_product, last_sale_by_product, cutoff, today)
            self.env.cr.commit()  # release locks every batch
            processed += len(chunk)
            _logger.info('Smart Connector dead-stock cron: %d/%d products scanned',
                         processed, len(product_ids))

    def _process_dead_stock_chunk(self, product_ids, qty_map, last_sale_map, cutoff, today):
        existing = {
            r.product_id.id: r
            for r in self.search([('product_id', 'in', product_ids)])
        }
        to_create = []
        for pid in product_ids:
            qty = qty_map.get(pid, 0)
            last_date = last_sale_map.get(pid)
            # Skip products that DID sell recently
            if last_date and last_date >= cutoff:
                if pid in existing and existing[pid].state == 'active':
                    # Was dead, now selling — resolve it
                    existing[pid].state = 'resolved'
                continue

            # Genuinely dead
            days = (today - last_date).days if last_date else None
            vals = {
                'qty_on_hand': qty,
                'last_sale_date': last_date or False,
                # When `last_date` is None (never sold), `days` is None too —
                # represented as 9999 so it sorts to the top of the "most dead" list.
                'days_since_last_sale': days if days is not None else 9999,
            }
            row = existing.get(pid)
            if row:
                # Reactivate if previously resolved/ignored — manager will re-triage.
                if row.state != 'active':
                    vals['state'] = 'active'
                row.write(vals)
            else:
                to_create.append(dict(vals, product_id=pid))
        if to_create:
            self.create(to_create)

    def action_resolve(self):
        for r in self:
            r.state = 'resolved'

    def action_ignore(self):
        for r in self:
            r.state = 'ignored'
