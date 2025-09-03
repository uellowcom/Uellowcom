# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    # Add carrier_id field if it doesn't exist in the stock.picking model
    # This ensures compatibility even if stock_delivery is not installed
    carrier_id = fields.Many2one('delivery.carrier', string='Carrier', check_company=True,
                               states={'done': [('readonly', True)]}, copy=True)
    
    def print_delivery_label(self):
        """
        Print the delivery label for the carrier
        """
        self.ensure_one()
        if not hasattr(self, 'carrier_id') or not self.carrier_id:
            return self.env['ir.actions.act_window'].for_xml_id('delivery_label', 'action_delivery_carrier_form')
        
        return self.env.ref('delivery_label.action_report_delivery_label').report_action(self)
    
    def action_print_delivery_label(self):
        """
        Action to print the delivery label
        """
        self.ensure_one()
        return {
            'name': _('Delivery Label'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.id,
            'context': {
                'default_picking_id': self.id,
                'form_view_initial_mode': 'print',
            },
            'target': 'new',
        }
