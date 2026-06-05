# -*- coding: utf-8 -*-
{
    'name': 'Uellow Affiliate / Reseller Program',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Agents sell on behalf of Uellow for commission — '
               'referral links, submitted orders with admin approval, '
               'tiered commissions, payouts, leaderboard.',
    'description': """
Uellow Affiliate Program
========================
• Affiliate agents (linked to a customer account) with a unique code.
• Product / category assignments with per-row commission %.
• Tiers (Bronze/Silver/Gold/Platinum) with commission multipliers and
  auto-upgrade by confirmed monthly sales.
• Two selling paths:
    1. Referral link/QR — the customer orders himself; the order carries
       the affiliate code and the commission books automatically.
    2. Affiliate-submitted order — the agent fills customer + items and
       sends it for admin review; approval creates the sale order.
• Commission ledger: pending on order, CONFIRMED only after delivery,
  paid through payout requests (min-threshold, methods: bank / KNET
  / wallet credit).
• Mobile API for the in-app Affiliate Center.
""",
    'author': 'Uellow',
    'depends': ['mail', 'portal', 'sale_management', 'stock', 'website_sale', 'uellow_mobile_manager'],
    'data': [
        'security/ir.model.access.csv',
        'views/affiliate_views.xml',
        'views/affiliate_order_views.xml',
        'views/affiliate_dashboard_views.xml',
        'views/portal_templates.xml',
        'data/cron.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
