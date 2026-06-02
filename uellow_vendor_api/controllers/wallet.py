# -*- coding: utf-8 -*-
"""Vendor wallet — /api/vendor/v1/wallet*"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, ok, require_auth, current_vendor, fmt_price,
)


class VendorWalletAPI(http.Controller):

    @http.route('/api/vendor/v1/wallet', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def wallet(self, **kw):
        v = current_vendor()
        wallet = v.wallet_id
        cur = v.currency_id or request.env.company.currency_id
        txs = []
        if wallet and 'transaction_ids' in wallet._fields:
            for t in wallet.transaction_ids[:100]:
                txs.append({
                    'id': t.id,
                    'amount': fmt_price(t.amount, cur),
                    'type': getattr(t, 'tx_type', 'adjust'),
                    'state': getattr(t, 'state', ''),
                    'description': getattr(t, 'description', '') or '',
                    'when': (t.create_date or t.write_date).isoformat()
                            if (t.create_date or t.write_date) else '',
                })
        return ok({
            'balance': fmt_price(v.wallet_balance or 0, cur),
            'pending': fmt_price(getattr(wallet, 'pending_balance', 0) or 0, cur)
                        if wallet else fmt_price(0, cur),
            'transactions': txs,
        })
