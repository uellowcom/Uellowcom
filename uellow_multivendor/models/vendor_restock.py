from odoo import models, fields, api


class UellowVendorRestock(models.Model):
    _name = 'uellow.vendor.restock'
    _description = 'Vendor Restock Request'
    _order = 'create_date desc'
    _rec_name = 'product_id'

    vendor_id = fields.Many2one('uellow.vendor', string='Vendor', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    qty = fields.Integer('Requested Qty', default=0)
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ], string='Priority', default='normal')
    notes = fields.Text('Vendor Notes')
    admin_notes = fields.Text('Admin Notes')
    state = fields.Selection([
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('shipped', 'Shipped'),
        ('received', 'Received'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending', index=True)
    expected_date = fields.Date('Expected Date')

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_ship(self):
        self.write({'state': 'shipped'})

    def action_receive(self):
        self.write({'state': 'received'})

    def action_reject(self):
        self.write({'state': 'rejected'})
