from odoo import models, fields, api, _


class ResPartner(models.Model):
    """
    Extend res.partner with vendor FBU info.
    """
    _inherit = 'res.partner'

    is_uellow_vendor = fields.Boolean(
        string='تاجر Uellow',
        default=False, index=True,
    )
    vendor_state = fields.Selection([
        ('pending',    'بانتظار الموافقة'),
        ('active',     'نشط'),
        ('suspended',  'موقوف'),
        ('rejected',   'مرفوض'),
    ], string='حالة التاجر', default='pending', index=True)

    fbu_location_id = fields.Many2one(
        'uellow.vendor.location',
        compute='_compute_fbu_location',
        string='مخزن FBU الفرعي',
    )

    def _compute_fbu_location(self):
        for partner in self:
            vl = self.env['uellow.vendor.location'].search([
                ('partner_id', '=', partner.id)
            ], limit=1)
            partner.fbu_location_id = vl

    def action_approve_vendor(self):
        """Approve vendor and auto-create their sub-location."""
        for partner in self:
            partner.vendor_state = 'active'
            vl = self.env['uellow.vendor.location'].create_for_vendor(partner)
            partner.message_post(body=_(
                'تم اعتماد التاجر. المخزن الفرعي: %s') % vl.location_name)

    def action_suspend_vendor(self):
        for partner in self:
            partner.vendor_state = 'suspended'
            if partner.fbu_location_id:
                partner.fbu_location_id.action_suspend()
