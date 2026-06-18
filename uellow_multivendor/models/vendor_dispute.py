# -*- coding: utf-8 -*-
"""Order issues / disputes — a vendor flags a problem with an order to Uellow,
admin reviews and resolves. Threaded so both sides see the conversation."""
from odoo import api, fields, models, _


class VendorOrderDispute(models.Model):
    _name = 'vendor.order.dispute'
    _description = 'Vendor Order Issue / Dispute'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char('Reference', readonly=True, copy=False, default='New')
    vendor_id = fields.Many2one('uellow.vendor', required=True, ondelete='cascade', index=True)
    order_id = fields.Many2one('sale.order', string='Order', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer',
                                 related='order_id.partner_id', store=True)
    reason = fields.Selection([
        ('out_of_stock',   'Out of stock'),
        ('customer_unreachable', 'Customer unreachable'),
        ('damaged',        'Item damaged'),
        ('wrong_item',     'Wrong item'),
        ('not_received',   'Not received'),
        ('return_request', 'Customer return request'),
        ('other',          'Other'),
    ], required=True, default='other', tracking=True)
    description = fields.Text('Details')
    state = fields.Selection([
        ('open',      'Open'),
        ('in_review', 'In review'),
        ('resolved',  'Resolved'),
        ('rejected',  'Rejected'),
    ], default='open', tracking=True, index=True)
    resolution = fields.Text('Resolution')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'vendor.order.dispute') or 'DISP/%s' % fields.Datetime.now().strftime('%y%m%d%H%M%S')
        recs = super().create(vals_list)
        for rec in recs:
            rec._notify_admin_new()
        return recs

    def _notify_admin_new(self):
        self.ensure_one()
        try:
            Notif = self.env['mobile.customer.notification'].sudo()
            admins = self.env['res.users'].sudo().search([
                ('groups_id', 'in', self.env.ref('uellow_multivendor.group_marketplace_manager').id),
            ]).mapped('partner_id')
            if admins:
                Notif.push_role('notify_order_dispute', admins,
                                'New order issue', 'بلاغ طلب جديد',
                                '%s — %s' % (self.order_id.name, dict(self._fields['reason'].selection).get(self.reason, '')),
                                '%s — %s' % (self.order_id.name, self.reason),
                                {'type': 'order_dispute', 'id': self.id})
        except Exception:
            pass

    def action_resolve(self):
        for r in self:
            r.state = 'resolved'
            r._notify_vendor(_('✅ Your order issue %s was resolved.') % r.name)

    def action_reject(self):
        for r in self:
            r.state = 'rejected'
            r._notify_vendor(_('Your order issue %s was closed.') % r.name)

    def _notify_vendor(self, msg):
        self.ensure_one()
        if self.vendor_id and self.vendor_id.user_id:
            self.message_post(
                body=msg,
                partner_ids=[self.vendor_id.user_id.partner_id.id],
                message_type='notification')
