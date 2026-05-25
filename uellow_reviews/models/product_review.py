from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductReview(models.Model):
    _name = 'uellow.product.review'
    _description = 'Product Review'
    _inherit = ['mail.thread']
    _rec_name = 'product_id'
    _order = 'id desc'

    product_id = fields.Many2one('product.template', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', required=True, ondelete='restrict', index=True)
    order_id = fields.Many2one('sale.order', ondelete='set null')
    is_verified = fields.Boolean('Verified Purchase', default=False, readonly=True)

    rating = fields.Integer('Rating (1-5)', required=True)
    title = fields.Char('Review Title')
    body = fields.Text('Review Body', required=True)
    photo_ids = fields.Many2many('ir.attachment', string='Photos')
    video_url = fields.Char('Video URL')

    state = fields.Selection([
        ('pending',   'Pending Moderation'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
    ], default='pending', index=True)

    points_awarded = fields.Integer('Points Awarded', default=0, readonly=True)
    helpful_count = fields.Integer('Helpful Votes', default=0)

    vendor_reply = fields.Text('Vendor Reply')
    vendor_replied_at = fields.Datetime('Replied At')

    @api.model_create_multi
    def create(self, vals_list):
        config = self.env['uellow.review.config'].get_config()
        for vals in vals_list:
            # Check verified purchase
            if config.require_purchase and vals.get('order_id'):
                order = self.env['sale.order'].browse(vals['order_id'])
                if order.partner_id.id == vals.get('partner_id') and order.state in ('sale', 'done'):
                    vals['is_verified'] = True
            if config.auto_approve:
                vals['state'] = 'approved'
        records = super().create(vals_list)
        for rec in records:
            if rec.state == 'approved':
                rec._award_points()
        return records

    def action_approve(self):
        self.state = 'approved'
        self._award_points()

    def action_reject(self):
        self.state = 'rejected'

    def _award_points(self):
        config = self.env['uellow.review.config'].get_config()
        if not config.active or self.points_awarded > 0:
            return
        points = config.points_text
        if self.photo_ids:
            points = max(points, config.points_photo)
        if self.video_url:
            points = max(points, config.points_video)
        if points > 0:
            account = self.env['uellow.loyalty.account'].sudo().search([
                ('partner_id', '=', self.partner_id.id)
            ], limit=1) if 'uellow.loyalty.account' in self.env else False
            if account:
                account.earn_points(points, reason=f'Review for {self.product_id.name}')
            self.points_awarded = points
