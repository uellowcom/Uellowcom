# -*- coding: utf-8 -*-
"""Vendor purchase statistics shown on the partner (vendor) form.

Adds a small live dashboard to each vendor page: total purchases (all
posted vendor bills, net of vendor credit notes), how much has been paid,
and how much is still outstanding — mirroring the accounting `debit`
(Total Payable). All figures aggregate the vendor plus its child contacts,
like Odoo's own `total_invoiced`.
"""
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendor_currency_id = fields.Many2one(
        'res.currency', compute='_compute_vendor_purchase_stats',
        string='Vendor Currency')
    vendor_purchase_total = fields.Monetary(
        string='Total Purchases', compute='_compute_vendor_purchase_stats',
        currency_field='vendor_currency_id',
        help='Total of all posted vendor bills for this vendor, '
             'net of vendor credit notes.')
    vendor_amount_paid = fields.Monetary(
        string='Paid', compute='_compute_vendor_purchase_stats',
        currency_field='vendor_currency_id',
        help='Purchases already paid = Total Purchases − Outstanding.')
    vendor_amount_due = fields.Monetary(
        string='Outstanding', compute='_compute_vendor_purchase_stats',
        currency_field='vendor_currency_id',
        help='Amount still owed to this vendor (unpaid part of posted '
             'bills). Matches the accounting Total Payable.')
    vendor_bill_count = fields.Integer(
        string='Vendor Bills', compute='_compute_vendor_purchase_stats')

    @api.depends('supplier_rank')
    def _compute_vendor_purchase_stats(self):
        AM = self.env['account.move']
        company_currency = self.env.company.currency_id
        for partner in self:
            partner.vendor_currency_id = (
                partner.company_id.currency_id or company_currency)
            # New / unsaved records have no id → nothing to aggregate.
            if not partner.id or partner.supplier_rank <= 0:
                partner.vendor_purchase_total = 0.0
                partner.vendor_amount_paid = 0.0
                partner.vendor_amount_due = 0.0
                partner.vendor_bill_count = 0
                continue
            bills = AM.search([
                ('partner_id', 'child_of', partner.commercial_partner_id.id),
                ('move_type', 'in', ('in_invoice', 'in_refund')),
                ('state', '=', 'posted'),
            ])
            total = 0.0
            due = 0.0
            for bill in bills:
                sign = 1.0 if bill.move_type == 'in_invoice' else -1.0
                total += sign * bill.amount_total
                due += sign * bill.amount_residual
            partner.vendor_purchase_total = total
            partner.vendor_amount_due = due
            partner.vendor_amount_paid = total - due
            partner.vendor_bill_count = len(bills)
