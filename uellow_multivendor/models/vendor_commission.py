from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CommissionPlan(models.Model):
    """
    Subscription plan defining monthly fee + commission rate.
    Supports multi-currency — each plan has its own currency.
    """
    _name = 'uellow.commission.plan'
    _description = 'Vendor Commission Plan'
    _rec_name = 'name'

    name = fields.Char('Plan Name', required=True)
    code = fields.Char('Code', required=True, index=True)
    monthly_fee = fields.Float('Monthly Fee', required=True)
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.ref('base.KWD', raise_if_not_found=False),
    )
    commission_rate = fields.Float('Default Commission Rate (%)', required=True)
    active = fields.Boolean(default=True)
    description = fields.Text('Description')

    # Per-category overrides
    category_commission_ids = fields.One2many(
        'uellow.category.commission', 'plan_id',
        string='Category Overrides',
    )

    _sql_constraints = [
        ('unique_code', 'UNIQUE(code)', 'Plan code must be unique.'),
    ]


class CategoryCommission(models.Model):
    """Override commission rate for specific product categories."""
    _name = 'uellow.category.commission'
    _description = 'Category Commission Override'

    plan_id = fields.Many2one('uellow.commission.plan', ondelete='cascade')
    category_id = fields.Many2one(
        'product.category', string='Product Category', required=True,
    )
    commission_rate = fields.Float('Commission Rate (%)', required=True)


class VendorCommissionLine(models.Model):
    """
    One line per sale order — tracks commission earned by Uellow.
    Created automatically when a sale order is confirmed.
    Multi-currency: stores both vendor currency and company currency.
    """
    _name = 'uellow.vendor.commission'
    _description = 'Vendor Commission Line'
    _rec_name = 'order_id'
    _order = 'id desc'

    vendor_id = fields.Many2one(
        'uellow.vendor', required=True, ondelete='cascade', index=True,
    )
    order_id = fields.Many2one(
        'sale.order', string='Sale Order',
        required=True, ondelete='restrict', index=True,
    )
    order_date = fields.Datetime(related='order_id.date_order', store=True)

    # Amounts in vendor currency
    order_amount = fields.Float('Order Amount')
    commission_rate = fields.Float('Commission Rate (%)')
    commission_amount = fields.Float('Commission Amount')
    net_vendor_amount = fields.Float('Net Vendor Amount')

    # Currency
    currency_id = fields.Many2one(
        'res.currency', related='vendor_id.currency_id', store=True,
    )

    # Amounts in company currency (for accounting)
    commission_amount_company = fields.Float('Commission (Company Currency)')
    company_currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    state = fields.Selection([
        ('pending',   'Pending'),
        ('hold',      'On Hold'),
        ('released',  'Released'),
        ('paid',      'Paid'),
        ('refunded',  'Refunded'),
    ], default='pending', string='Status', index=True)

    hold_days = fields.Integer('Hold Period (days)', default=7)
    release_date = fields.Date('Release Date', compute='_compute_release_date', store=True)

    payout_id = fields.Many2one(
        'uellow.vendor.payout', string='Payout', ondelete='set null',
    )

    @api.depends('order_date', 'hold_days')
    def _compute_release_date(self):
        from datetime import timedelta
        for line in self:
            if line.order_date:
                line.release_date = line.order_date.date() + timedelta(days=line.hold_days)
            else:
                line.release_date = False

    @api.model
    def create_from_order(self, order):
        """Called when a sale order is confirmed."""
        vendor = order.vendor_id
        if not vendor:
            return
        plan = vendor.plan_id
        rate = plan.commission_rate if plan else 10.0

        # Check category override
        for line in order.order_line:
            cat = line.product_id.categ_id
            if plan:
                override = plan.category_commission_ids.filtered(
                    lambda c: c.category_id == cat)
                if override:
                    rate = override[0].commission_rate
                    break

        # Convert to vendor currency if needed
        company_currency = self.env.company.currency_id
        vendor_currency = vendor.currency_id or company_currency
        order_amount = order.amount_total
        if order.currency_id != vendor_currency:
            order_amount = order.currency_id._convert(
                order_amount, vendor_currency,
                self.env.company, order.date_order or fields.Date.today(),
            )

        commission = order_amount * rate / 100
        net = order_amount - commission

        return self.create({
            'vendor_id': vendor.id,
            'order_id': order.id,
            'order_amount': order_amount,
            'commission_rate': rate,
            'commission_amount': commission,
            'net_vendor_amount': net,
            'hold_days': vendor.plan_id.id and 7 or 7,
        })

    def action_release(self):
        """Release held commission to vendor wallet."""
        for line in self:
            if line.state != 'hold':
                continue
            line.state = 'released'
            # Credit vendor wallet
            if line.vendor_id.wallet_id:
                line.vendor_id.wallet_id.credit(
                    line.net_vendor_amount,
                    description=f'Order {line.order_id.name}',
                    commission_line_id=line.id,
                )


class VendorPayout(models.Model):
    """Monthly payout batch — groups multiple commission lines."""
    _name = 'uellow.vendor.payout'
    _description = 'Vendor Payout'
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char('Payout Reference', readonly=True, default='New')
    vendor_id = fields.Many2one('uellow.vendor', required=True, index=True)
    currency_id = fields.Many2one(
        'res.currency', related='vendor_id.currency_id', store=True,
    )
    amount = fields.Float('Payout Amount')
    state = fields.Selection([
        ('draft',     'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid',      'Paid'),
        ('cancelled', 'Cancelled'),
    ], default='draft')

    commission_line_ids = fields.One2many(
        'uellow.vendor.commission', 'payout_id', string='Commission Lines',
    )
    payout_date = fields.Date('Payout Date')
    bank_iban = fields.Char(related='vendor_id.bank_iban', string='IBAN')
    bank_name = fields.Char(related='vendor_id.bank_name', string='Bank')
    note = fields.Text('Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('uellow.vendor.payout') or 'New'
        return super().create(vals_list)

    def action_confirm(self):
        self.state = 'confirmed'

    def action_mark_paid(self):
        for payout in self:
            payout.state = 'paid'
            payout.commission_line_ids.write({'state': 'paid'})
            payout.vendor_id.wallet_id.debit(
                payout.amount,
                description=f'Payout {payout.name}',
            )
