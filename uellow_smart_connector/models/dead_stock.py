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
        compute='_compute_vendor',
        string='Vendor',
    )

    qty_on_hand = fields.Float('Qty On Hand', readonly=True)
    last_sale_date = fields.Date('Last Sale', readonly=True)
    days_since_last_sale = fields.Integer('Days Since Last Sale', readonly=True)
    # v2.1 — "never sold" is now measured from the product's CREATE date, and
    # brand-new products inside the grace window are not flagged at all (was:
    # a hard 9999 that put fresh products at the top of the dead list).
    never_sold = fields.Boolean('Never Sold', readonly=True, default=False)
    product_age_days = fields.Integer('Product Age (days)', readonly=True)
    # v3 — seasonality + liquidation staging (ideas #26 / #27)
    is_seasonal = fields.Boolean(
        'Seasonal', readonly=True, default=False,
        help='Historically sells in the current/upcoming months — protected '
             'from liquidation so we do not dump stock right before its season.')
    target_discount_pct = fields.Float('Suggested Discount %', default=0.0)
    beena_promote = fields.Boolean(
        'Promote via Beena', default=False,
        help='Flag so Beena can surface this idle item to relevant customers.')

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

    # Split compute methods: product_tmpl_id is STORED, vendor_partner_id is
    # NOT — Odoo warns when stored & non-stored share one compute method.
    @api.depends('product_id', 'product_id.product_tmpl_id')
    def _compute_product_info(self):
        for rec in self:
            rec.product_tmpl_id = rec.product_id.product_tmpl_id or False

    @api.depends('product_id', 'product_id.vendor_partner_id')
    def _compute_vendor(self):
        for rec in self:
            rec.vendor_partner_id = (
                getattr(rec.product_id, 'vendor_partner_id', False) or False)

    @api.model
    def cron_scan_dead_stock(self):
        """Weekly cron: find products with stock but no recent sales.

        Performance fixes (A7/C1):
          - One `read_group` on stock.quant to get qty per product (was: N quants).
          - One `read_group` on stock.move to get last-sale per product (was: N searches).
          - Commit every `_DEAD_STOCK_BATCH` to release locks.
        """
        settings = self.env['uellow.connector.settings'].get_settings()
        if not settings.get('feat_dead_stock'):
            return
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

        # 2b) creation date per product (one read) — lets us age "never sold"
        #     products from when they were ADDED, not from epoch 9999.
        create_by_product = {}
        for p in self.env['product.product'].browse(list(qty_by_product.keys())):
            cd = p.create_date
            create_by_product[p.id] = (cd.date() if cd else today)

        # season window = current month + next N-1 (a product whose season is
        # approaching must NOT be liquidated now). Wrap around December.
        # Disabled / 0 look-ahead → no seasonal protection (empty set).
        if settings.get('feat_seasonality'):
            look = max(1, int(settings.get('season_lookahead_months') or 3))
            season_months = {((today.month - 1 + k) % 12) + 1 for k in range(look)}
        else:
            season_months = set()

        # 3) Walk products in batches, commit between chunks
        product_ids = list(qty_by_product.keys())
        processed = 0
        for i in range(0, len(product_ids), _DEAD_STOCK_BATCH):
            chunk = product_ids[i:i + _DEAD_STOCK_BATCH]
            self._process_dead_stock_chunk(
                chunk, qty_by_product, last_sale_by_product,
                create_by_product, cutoff, today, season_months)
            self.env.cr.commit()  # release locks every batch
            processed += len(chunk)
            _logger.info('Smart Connector dead-stock cron: %d/%d products scanned',
                         processed, len(product_ids))

    def _seasonal_months_map(self, product_ids):
        """Return {product_id: set(month_int)} of months each product ever sold in.

        One read_group over the chunk — used to spare seasonal stock from
        being flagged dead just because it's off-season right now (idea #27).
        """
        out = {}
        if not product_ids:
            return out
        groups = self.env['stock.move'].read_group(
            domain=[
                ('product_id', 'in', product_ids),
                ('location_dest_id.usage', '=', 'customer'),
                ('state', '=', 'done'),
            ],
            fields=['product_id'],
            groupby=['product_id', 'date:month'],
            lazy=False,
        )
        for row in groups:
            if not row.get('product_id') or not row.get('date:month'):
                continue
            pid = row['product_id'][0]
            # 'date:month' looks like "March 2024" → map via the raw range start
            rng = row.get('__range', {}).get('date:month', {})
            start = rng.get('from')
            if not start:
                continue
            try:
                month = fields.Date.to_date(start).month
            except Exception:                       # noqa: BLE001
                continue
            out.setdefault(pid, set()).add(month)
        return out

    def _process_dead_stock_chunk(self, product_ids, qty_map, last_sale_map,
                                  create_map, cutoff, today, season_months=None):
        season_months = season_months or set()
        sale_months = self._seasonal_months_map(product_ids)
        existing = {
            r.product_id.id: r
            for r in self.search([('product_id', 'in', product_ids)])
        }
        to_create = []
        for pid in product_ids:
            qty = qty_map.get(pid, 0)
            last_date = last_sale_map.get(pid)
            created = create_map.get(pid, today)
            age = (today - created).days if created else 0
            # Skip products that DID sell recently
            if last_date and last_date >= cutoff:
                if pid in existing and existing[pid].state == 'active':
                    # Was dead, now selling — resolve it
                    existing[pid].state = 'resolved'
                continue

            never_sold = not last_date
            if never_sold:
                # Never sold — age it from when it was ADDED. A brand-new
                # product still inside the grace window is NOT dead yet.
                if created >= cutoff:
                    # too new to judge; if a stale row exists, clear it
                    if pid in existing and existing[pid].state == 'active':
                        existing[pid].state = 'resolved'
                    continue
                days = age
            else:
                days = (today - last_date).days

            # Seasonality guard: a product that historically sells in the
            # current/upcoming months is entering its season — don't liquidate.
            months = sale_months.get(pid)
            seasonal = bool(months and (months & season_months))
            if seasonal:
                if pid in existing and existing[pid].state == 'active':
                    existing[pid].write({'is_seasonal': True, 'state': 'resolved'})
                continue

            vals = {
                'qty_on_hand': qty,
                'last_sale_date': last_date or False,
                'days_since_last_sale': days,
                'never_sold': never_sold,
                'product_age_days': age,
                'is_seasonal': False,
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

    # ── liquidation staging (idea #26) ─────────────────────────────────────
    def action_flag_discount(self):
        """Stage a flash-sale discount decision (default 15% if unset)."""
        for r in self:
            r.write({
                'suggested_action': 'discount',
                'target_discount_pct': r.target_discount_pct or 15.0,
            })

    def action_promote_beena(self):
        """Mark this idle item so Beena can surface it to relevant customers."""
        for r in self:
            r.write({'beena_promote': True})

    def action_stop_promote(self):
        for r in self:
            r.write({'beena_promote': False})

    @api.model
    def beena_promotable_products(self, limit=10):
        """Return idle products flagged for Beena promotion (hook for Beena AI).

        Used by the AI assistant to weave 'clearance' suggestions into chat.
        Returns plain dicts so the controller layer needs no ORM knowledge.
        """
        rows = self.search(
            [('beena_promote', '=', True), ('state', '=', 'active')],
            order='days_since_last_sale desc', limit=limit)
        out = []
        for r in rows:
            tmpl = r.product_tmpl_id
            out.append({
                'product_tmpl_id': tmpl.id if tmpl else False,
                'name': tmpl.name if tmpl else (r.product_id.name or ''),
                'discount_pct': r.target_discount_pct,
                'qty_on_hand': r.qty_on_hand,
                'days_idle': r.days_since_last_sale,
            })
        return out
