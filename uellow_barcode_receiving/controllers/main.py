from odoo import http
from odoo.http import request


class BarcodeController(http.Controller):

    @http.route('/barcode/scan', type='json', auth='user')
    def scan(self, session_id, barcode):
        """Look up product by barcode and log the scan."""
        session = request.env['uellow.barcode.session'].sudo().browse(int(session_id))
        if not session.exists():
            return {'error': 'Session not found'}

        # Find product by barcode
        product = request.env['product.product'].sudo().search([
            ('barcode', '=', barcode)
        ], limit=1)

        if not product:
            # Try product template barcode
            tmpl = request.env['product.template'].sudo().search([
                ('barcode', '=', barcode)
            ], limit=1)
            if tmpl and tmpl.product_variant_ids:
                product = tmpl.product_variant_ids[0]

        status = 'unknown'
        product_name = 'Unknown'

        if product:
            # Check if product is in the restock request
            in_request = session.request_id.line_ids.filtered(
                lambda l: l.product_id == product)
            status = 'ok' if in_request else 'mismatch'
            product_name = product.display_name

            # Log scan
            existing = request.env['uellow.barcode.scan'].sudo().search([
                ('session_id', '=', session_id),
                ('product_id', '=', product.id),
            ], limit=1)
            if existing:
                existing.qty_scanned += 1
            else:
                request.env['uellow.barcode.scan'].sudo().create({
                    'session_id': session_id,
                    'barcode': barcode,
                    'product_id': product.id,
                    'status': status,
                })
        else:
            request.env['uellow.barcode.scan'].sudo().create({
                'session_id': session_id,
                'barcode': barcode,
                'status': 'unknown',
            })

        return {
            'status': status,
            'product_name': product_name,
            'product_id': product.id if product else False,
        }
