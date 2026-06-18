# -*- coding: utf-8 -*-
"""Excel exports — /api/vendor/v1/export/* and /admin/export/*

Returns real .xlsx files (xlsxwriter). The app fetches with the Bearer token
and shares/saves the file; the portal/browser can hit the same URL.
"""
import io

import xlsxwriter

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, ok, fail, require_auth, require_admin, current_vendor,
)

XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _xlsx(filename, headers, rows):
    """Build an xlsx and return an http file response."""
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {'in_memory': True})
    ws = wb.add_worksheet('Sheet1')
    hfmt = wb.add_format({'bold': True, 'bg_color': '#FFF7DA', 'border': 1})
    for c, h in enumerate(headers):
        ws.write(0, c, h, hfmt)
        ws.set_column(c, c, max(12, len(str(h)) + 2))
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row):
            ws.write(r, c, val if val is not None else '')
    wb.close()
    data = buf.getvalue()
    return request.make_response(data, headers=[
        ('Content-Type', XLSX_MIME),
        ('Content-Disposition', 'attachment; filename="%s"' % filename),
        ('Content-Length', str(len(data))),
    ])


class VendorExportsAPI(http.Controller):

    @http.route('/api/vendor/v1/export/orders.xlsx', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def export_orders(self, **kw):
        v = current_vendor()
        orders = request.env['sale.order'].sudo().search(
            [('vendor_id', '=', v.id)], order='id desc', limit=5000)
        rows = [[
            o.name,
            (o.date_order or o.create_date).strftime('%Y-%m-%d %H:%M') if (o.date_order or o.create_date) else '',
            o.partner_id.name or '',
            o.state,
            o.invoice_status,
            round(o.amount_untaxed, 3),
            round(o.amount_total, 3),
        ] for o in orders]
        return _xlsx('orders.xlsx',
                     ['Order', 'Date', 'Customer', 'Status', 'Invoice', 'Subtotal', 'Total'], rows)

    @http.route('/api/vendor/v1/export/products.xlsx', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def export_products(self, **kw):
        v = current_vendor()
        prods = request.env['product.template'].sudo().with_context(active_test=False).search(
            [('vendor_id', '=', v.id)], order='id desc', limit=5000)
        rows = [[
            t.name, t.default_code or '', t.barcode or '',
            round(t.standard_price or 0, 3), round(t.list_price or 0, 3),
            float(t.qty_available or 0),
            t.vendor_approval_state or '', 'Yes' if t.is_published else 'No',
            'Archived' if not t.active else 'Active',
        ] for t in prods]
        return _xlsx('products.xlsx',
                     ['Name', 'SKU', 'Barcode', 'Cost', 'Sale price', 'Qty',
                      'Approval', 'Published', 'State'], rows)

    @http.route('/api/vendor/v1/export/returns.xlsx', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def export_returns(self, **kw):
        v = current_vendor()
        reqs = request.env['uellow.return.request'].sudo().search(
            [('vendor_id', '=', v.id)], order='id desc', limit=5000)
        rows = []
        for r in reqs:
            for l in r.line_ids:
                rows.append([r.name, r.state, r.pickup_mode,
                             l.product_id.display_name, l.qty, round(l.cost or 0, 3)])
        return _xlsx('returns.xlsx',
                     ['Reference', 'Status', 'Handover', 'Product', 'Qty', 'Cost'], rows)

    # ── admin exports ────────────────────────────────────────────────
    @http.route('/api/vendor/v1/admin/export/orders.xlsx', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_export_orders(self, **kw):
        orders = request.env['sale.order'].sudo().search(
            [('vendor_id', '!=', False)], order='id desc', limit=10000)
        rows = [[
            o.name,
            (o.date_order or o.create_date).strftime('%Y-%m-%d %H:%M') if (o.date_order or o.create_date) else '',
            o.vendor_id.display_name or '', o.partner_id.name or '',
            o.state, o.invoice_status, round(o.amount_total, 3),
        ] for o in orders]
        return _xlsx('marketplace_orders.xlsx',
                     ['Order', 'Date', 'Vendor', 'Customer', 'Status', 'Invoice', 'Total'], rows)

    @http.route('/api/vendor/v1/admin/export/vendors.xlsx', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_admin
    def admin_export_vendors(self, **kw):
        vendors = request.env['uellow.vendor'].sudo().search([], order='total_sales desc')
        rows = [[
            v.display_name, v.vendor_type or 'seller', v.tier or 'bronze',
            v.state, v.product_total, round(v.total_sales or 0, 3),
            v.order_count, round(v.avg_rating or 0, 2),
        ] for v in vendors]
        return _xlsx('vendors.xlsx',
                     ['Vendor', 'Type', 'Tier', 'State', 'Products', 'Sales',
                      'Orders', 'Rating'], rows)
