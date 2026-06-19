# -*- coding: utf-8 -*-
"""Vendor bulk imports — /api/vendor/v1/imports*

A vendor uploads a CSV/Excel file → it is parsed into editable staged rows →
the vendor fixes any issues → submits for Uellow review. On approval each row
becomes a product (pending approval), scoped to the vendor's markets.
"""
import base64

from odoo import http, SUPERUSER_ID
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_vendor,
)


def _ser_line(ln):
    return {
        'id': ln.id, 'name_en': ln.name_en or '', 'name_ar': ln.name_ar or '',
        'sku': ln.sku or '', 'barcode': ln.barcode or '',
        'cost': ln.cost or '', 'price': ln.price or '',
        'category': ln.category or '', 'description': ln.description or '',
        'error': ln.error or '', 'created': bool(ln.created_product_id),
    }


def _ser_job(r, lines=False):
    out = {
        'id': r.id, 'name': r.name, 'state': r.state,
        'file_name': r.file_name or '', 'row_count': r.row_count,
        'error_count': r.error_count, 'created_count': r.created_count,
        'note': r.note or '',
        'when': r.create_date.isoformat() if r.create_date else '',
    }
    if lines:
        out['lines'] = [_ser_line(l) for l in r.line_ids]
    return out


class VendorImportsAPI(http.Controller):

    @http.route('/api/vendor/v1/imports', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_imports(self, **kw):
        v = current_vendor()
        rows = request.env['uellow.product.import'].sudo().search(
            [('vendor_id', '=', v.id)], order='id desc', limit=50)
        return ok([_ser_job(r) for r in rows])

    @http.route('/api/vendor/v1/imports/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_import(self, **kw):
        """Body: {file_base64, file_name}. Creates the job + parses the file."""
        v = current_vendor()
        if not (v.cap('import_products') or v.cap('add_products')):
            return fail('FORBIDDEN', 'Importing products is disabled for your account.', 403, capability='import_products')
        p = get_payload()
        b64 = p.get('file_base64') or ''
        fname = (p.get('file_name') or 'import.csv').strip()
        if not b64:
            return fail('NO_FILE', 'file_base64 required')
        try:
            data = b64.split(',', 1)[-1]
            base64.b64decode(data)  # validate
        except Exception:
            return fail('BAD_FILE', 'file_base64 is not valid base64')
        senv = request.env(user=SUPERUSER_ID)
        job = senv['uellow.product.import'].create({
            'vendor_id': v.id, 'file_name': fname, 'file_data': data,
        })
        try:
            job._parse_file()
        except Exception as e:
            return fail('PARSE_ERROR', str(e)[:200])
        request.env.cr.commit()
        return ok(_ser_job(job, lines=True))

    @http.route('/api/vendor/v1/imports/<int:job_id>', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def get_import(self, job_id, **kw):
        v = current_vendor()
        r = request.env['uellow.product.import'].sudo().browse(job_id)
        if not r.exists() or r.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Import not found', 404)
        return ok(_ser_job(r, lines=True))

    @http.route('/api/vendor/v1/imports/<int:job_id>/line/<int:line_id>',
                type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def edit_line(self, job_id, line_id, **kw):
        v = current_vendor()
        r = request.env['uellow.product.import'].sudo().browse(job_id)
        if not r.exists() or r.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Import not found', 404)
        if r.state != 'draft':
            return fail('LOCKED', 'Only draft imports can be edited.', 409)
        ln = r.line_ids.filtered(lambda l: l.id == line_id)
        if not ln:
            return fail('NOT_FOUND', 'Row not found', 404)
        p = get_payload()
        vals = {f: (p[f] or '') for f in
                ('name_en', 'name_ar', 'sku', 'barcode', 'cost', 'price', 'category', 'description')
                if f in p}
        if vals:
            ln.write(vals)
        request.env.cr.commit()
        return ok(_ser_line(ln))

    @http.route('/api/vendor/v1/imports/<int:job_id>/line/<int:line_id>/delete',
                type='http', auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def delete_line(self, job_id, line_id, **kw):
        v = current_vendor()
        r = request.env['uellow.product.import'].sudo().browse(job_id)
        if not r.exists() or r.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Import not found', 404)
        if r.state != 'draft':
            return fail('LOCKED', 'Only draft imports can be edited.', 409)
        r.line_ids.filtered(lambda l: l.id == line_id).unlink()
        request.env.cr.commit()
        return ok({'deleted': True})

    @http.route('/api/vendor/v1/imports/<int:job_id>/submit', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def submit_import(self, job_id, **kw):
        v = current_vendor()
        r = request.env['uellow.product.import'].sudo().browse(job_id)
        if not r.exists() or r.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Import not found', 404)
        try:
            r.action_submit()
        except Exception as e:
            return fail('SUBMIT_ERROR', str(e)[:200])
        request.env.cr.commit()
        return ok(_ser_job(r))

    @http.route('/api/vendor/v1/imports/<int:job_id>/delete', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def delete_import(self, job_id, **kw):
        v = current_vendor()
        r = request.env['uellow.product.import'].sudo().browse(job_id)
        if not r.exists() or r.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Import not found', 404)
        if r.state == 'done':
            return fail('LOCKED', 'Imported jobs cannot be deleted.', 409)
        r.unlink()
        request.env.cr.commit()
        return ok({'deleted': True})
