from odoo import models, fields, api, _


class SupplierProfile(models.Model):
    _name = 'uellow.supplier.profile'
    _description = 'Supplier Profile'
    _inherit = ['mail.thread']
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Portal User')
    is_dropship = fields.Boolean('Dropship Supplier', default=False)
    active = fields.Boolean(default=True)

    # Health Score components
    health_score = fields.Float('Health Score', compute='_compute_health', store=True)
    on_time_rate = fields.Float('On-time Delivery Rate (%)', default=100.0)
    quality_rate = fields.Float('Quality Rate (%)', default=100.0)
    response_time_hrs = fields.Float('Avg Response Time (hrs)', default=4.0)
    cancel_rate = fields.Float('Cancel Rate (%)', default=0.0)

    total_orders = fields.Integer('Total Orders', default=0)
    total_revenue = fields.Float('Total Revenue')

    notes = fields.Text('Internal Notes')

    @api.depends('on_time_rate', 'quality_rate', 'response_time_hrs', 'cancel_rate')
    def _compute_health(self):
        for s in self:
            # Weighted score: on_time 40%, quality 30%, response 20%, cancel -10%
            response_score = max(0, 100 - (s.response_time_hrs - 4) * 5) if s.response_time_hrs > 4 else 100
            s.health_score = (
                s.on_time_rate * 0.4 +
                s.quality_rate * 0.3 +
                response_score * 0.2 +
                (100 - s.cancel_rate) * 0.1
            )

    def health_badge(self):
        if self.health_score >= 90:
            return 'excellent'
        elif self.health_score >= 70:
            return 'good'
        elif self.health_score >= 50:
            return 'fair'
        return 'poor'
