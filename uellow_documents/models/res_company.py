# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Configurable document terms shown on the Uellow invoice / sales order.
    # Bilingual free text so the admin controls the exact wording (EN · AR).
    uellow_delivery_terms = fields.Char(
        string='Delivery terms (document)',
        default='Within 2–4 working days · خلال ٢-٤ أيام عمل')
    uellow_warranty_terms = fields.Char(
        string='Warranty terms (document)',
        default='12 months · ضمان ١٢ شهر')
    uellow_returns_terms = fields.Char(
        string='Returns terms (document)',
        default='14 days · إرجاع خلال ١٤ يوم')
    uellow_payment_terms_note = fields.Char(
        string='Payment terms note (document)',
        default='Cash / KNET on delivery · نقدًا / كي-نت عند الاستلام')
    uellow_doc_footer = fields.Char(
        string='Document footer line',
        default='Thank you for shopping with Uellow · شكرًا لتسوّقك مع يلو')
    uellow_bank_line = fields.Char(
        string='Bank line (invoice)',
        default='')
