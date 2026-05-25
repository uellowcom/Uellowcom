# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class DeliveryLabelController(http.Controller):
    
    @http.route('/delivery_label/print/<int:picking_id>', type='http', auth='user')
    def print_delivery_label(self, picking_id, **kwargs):
        picking = request.env['stock.picking'].browse(picking_id)
        if not picking.exists() or not picking.carrier_id:
            return request.not_found()
        
        report = request.env.ref('delivery_label.action_report_delivery_label')
        pdf, _ = report._render_qweb_pdf(report.report_name, res_ids=[picking_id])
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', 'attachment; filename=delivery_label_%s.pdf' % picking.name)
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
