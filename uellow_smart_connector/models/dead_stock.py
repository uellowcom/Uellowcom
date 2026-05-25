import logging
from odoo import models, fields, api, _
from datetime import timedelta

_logger = logging.getLogger(__name__)


class DeadStockMonitor(models.Model):
    """
    Identifies products with stock but zero sales for N days.
    Cron runs weekly and generates alerts.
    """
    _name = 'uellow.dead.stock'
    _description = 'مراقبة المخزون الراكد'
    _rec_name = 'product_id'
    _order = 'days_since_last_sale desc'

    product_id = fields.Many2one(
        'product.product', required=True, ondelete='cascade',
        string='المنتج (Variant)',
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        compute='_compute_product_info',
        store=True,
        string='المنتج الأب',
    )
    vendor_partner_id = fields.Many2one(
        'res.partner',
        compute='_compute_product_info',
        store=True,
        string='التاجر',
    )

    qty_on_hand = fields.Float('الكمية في المخزن', readonly=True)
    last_sale_date = fields.Date('آخر بيعة', readonly=True)
    days_since_last_sale = fields.Integer('أيام منذ آخر بيعة', readonly=True)

    suggested_action = fields.Selection([
        ('discount',      'خصم Flash Sale'),
        ('bundle',        'دمج في حزمة Bundle'),
        ('return_vendor', 'إرجاع للتاجر'),
        ('write_off',     'شطب'),
        ('none',          'لا إجراء'),
    ], default='discount', string='الإجراء المقترح')

    state = fields.Selection([
        ('active',   'راكد'),
        ('resolved', 'تمت المعالجة'),
        ('ignored',  'متجاهل'),
    ], default='active', string='الحالة')

    alert_sent = fields.Boolean(default=False)

    @api.depends('product_id')
    def _compute_product_info(self):
        for rec in self:
            if rec.product_id:
                rec.product_tmpl_id = rec.product_id.product_tmpl_id
                # vendor_partner_id only exists if uellow_fulfillment is installed
                rec.vendor_partner_id = getattr(rec.product_id, 'vendor_partner_id', False) or False
            else:
                rec.product_tmpl_id = False
                rec.vendor_partner_id = False

    @api.model
    def cron_scan_dead_stock(self):
        """Weekly cron: find products with stock but no recent sales."""
        settings = self.env['uellow.connector.settings'].get_settings()
        days_threshold = settings.get('dead_stock_days', 30)
        cutoff = fields.Date.today() - timedelta(days=days_threshold)

        quants = self.env['stock.quant'].search([
            ('location_id.usage', '=', 'internal'),
            ('quantity', '>', 0),
        ])

        for quant in quants:
            product = quant.product_id
            last_move = self.env['stock.move'].search([
                ('product_id', '=', product.id),
                ('location_dest_id.usage', '=', 'customer'),
                ('state', '=', 'done'),
            ], order='date desc', limit=1)

            last_date = last_move.date.date() if last_move else None
            if last_date and last_date >= cutoff:
                continue

            days = (fields.Date.today() - last_date).days if last_date else days_threshold + 1

            existing = self.search([
                ('product_id', '=', product.id),
                ('state', '=', 'active'),
            ], limit=1)

            vals = {
                'qty_on_hand': quant.quantity,
                'last_sale_date': last_date,
                'days_since_last_sale': days,
            }
            if existing:
                existing.write(vals)
            else:
                self.create({'product_id': product.id, **vals})

    def action_resolve(self):
        self.state = 'resolved'

    def action_ignore(self):
        self.state = 'ignored'
