# -*- coding: utf-8 -*-
from odoo import api, fields, models

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    logo = fields.Binary(string='Carrier Logo', attachment=True, help="Upload the carrier logo here")
    vendor_partner_id = fields.Many2one(
        'res.partner',
        string='Vendor Partner',
        readonly=True,
        copy=False,
        help="The vendor partner associated with this carrier",
    )
    vendor_phone = fields.Char(string='Vendor Phone')
    vendor_email = fields.Char(string='Vendor Email')
    vendor_street = fields.Char(string='Vendor Street')
    vendor_city = fields.Char(string='Vendor City')
    vendor_zip = fields.Char(string='Vendor ZIP')
    vendor_country_id = fields.Many2one('res.country', string='Vendor Country')

    @api.model_create_multi
    def create(self, vals_list):
        carriers = super().create(vals_list)
        for carrier in carriers:
            if not carrier.vendor_partner_id:
                partner = self.env['res.partner'].create(carrier._prepare_vendor_partner_vals())
                carrier.vendor_partner_id = partner
        return carriers

    def write(self, vals):
        result = super().write(vals)
        sync_fields = {
            'name',
            'logo',
            'vendor_phone',
            'vendor_email',
            'vendor_street',
            'vendor_city',
            'vendor_zip',
            'vendor_country_id',
        }
        if sync_fields.intersection(vals):
            for carrier in self.filtered('vendor_partner_id'):
                carrier.vendor_partner_id.write(carrier._prepare_vendor_partner_vals())
        return result

    def _prepare_vendor_partner_vals(self):
        self.ensure_one()
        vals = {
            'name': self.name,
            'phone': self.vendor_phone or False,
            'email': self.vendor_email or False,
            'street': self.vendor_street or False,
            'city': self.vendor_city or False,
            'zip': self.vendor_zip or False,
            'country_id': self.vendor_country_id.id or False,
            'image_1920': self.logo or False,
            'supplier_rank': 1,
            'company_type': 'company',
        }
        return vals

    def print_delivery_label(self, picking):
        self.ensure_one()
        if not picking:
            return False
        return self.env.ref('delivery_label.action_report_delivery_label').report_action(picking)
