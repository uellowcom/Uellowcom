from odoo import models, fields, _

class ProductRejectWizard(models.TransientModel):
    _name = 'uellow.product.reject.wizard'
    _description = 'Product Rejection Wizard'

    product_ids = fields.Many2many('product.template', string='Products')
    rejection_reason = fields.Text('Rejection Reason', required=True,
        placeholder='e.g. Missing images, incorrect price...')

    def action_reject(self):
        for product in self.product_ids:
            product.write({
                'vendor_approval_state': 'rejected',
                'website_published': False,
                'vendor_rejection_reason': self.rejection_reason,
                'vendor_reviewed_by': self.env.user.id,
                'vendor_reviewed_date': fields.Datetime.now(),
            })
            if product.vendor_id and product.vendor_id.user_id:
                product.message_post(
                    body=_('❌ Product <b>%s</b> was rejected.<br/>Reason: %s') % (
                        product.name, self.rejection_reason),
                    partner_ids=[product.vendor_id.user_id.partner_id.id],
                    message_type='notification',
                )
        return {'type': 'ir.actions.act_window_close'}
