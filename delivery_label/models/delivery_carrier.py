# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    # Add logo field to the delivery carrier
    logo = fields.Binary(string='Carrier Logo', attachment=True, help="Upload the carrier logo here")
    vendor_partner_id = fields.Many2one('res.partner', string='Vendor Partner', readonly=True,
                                       help="The vendor partner associated with this carrier")
    
    # Override create method to automatically create a vendor partner
    @api.model
    def create(self, vals):
        carrier = super(DeliveryCarrier, self).create(vals)
        # Create vendor partner with the same information
        if not carrier.vendor_partner_id:
            partner_vals = {
                'name': carrier.name,
                'phone': carrier.get_vendor_phone(),
                'email': carrier.get_vendor_email(),
                'street': carrier.get_vendor_street(),
                'city': carrier.get_vendor_city(),
                'zip': carrier.get_vendor_zip(),
                'country_id': carrier.get_vendor_country_id(),
                'image_1920': carrier.logo,
                'supplier_rank': 1,  # Mark as vendor
                'company_type': 'company',
            }
            partner = self.env['res.partner'].create(partner_vals)
            carrier.vendor_partner_id = partner.id
        return carrier
    
    # Override write method to update the vendor partner
    def write(self, vals):
        result = super(DeliveryCarrier, self).write(vals)
        for carrier in self:
            if carrier.vendor_partner_id:
                partner_vals = {}
                if 'name' in vals:
                    partner_vals['name'] = vals['name']
                if 'logo' in vals:
                    partner_vals['image_1920'] = vals['logo']
                
                # Update other fields if needed
                if partner_vals:
                    carrier.vendor_partner_id.write(partner_vals)
        return result
    
    # Helper methods to get vendor information
    def get_vendor_phone(self):
        return self.env.context.get('vendor_phone', '')
    
    def get_vendor_email(self):
        return self.env.context.get('vendor_email', '')
    
    def get_vendor_street(self):
        return self.env.context.get('vendor_street', '')
    
    def get_vendor_city(self):
        return self.env.context.get('vendor_city', '')
    
    def get_vendor_zip(self):
        return self.env.context.get('vendor_zip', '')
    
    def get_vendor_country_id(self):
        return self.env.context.get('vendor_country_id', False)
    
    # Method to print the delivery label
    def print_delivery_label(self, picking):
        """
        Print the delivery label for the given picking
        """
        self.ensure_one()
        if not picking:
            return False
        return self.env.ref('delivery_label.action_report_delivery_label').report_action(picking)
