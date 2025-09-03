# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class DeliveryLabelController(http.Controller):
    
    @http.route('/delivery_label/print/<int:picking_id>', type='http', auth='user')
    def print_delivery_label(self, picking_id, **kwargs):
        """
        Controller to print the delivery label
        """
        picking = request.env['stock.picking'].browse(picking_id)
        if not picking.exists() or not picking.carrier_id:
            return request.not_found()
        
        pdf = request.env.ref('delivery_label.action_report_delivery_label').render_qweb_pdf([picking_id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=delivery_label_%s.pdf' % picking.name)
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
