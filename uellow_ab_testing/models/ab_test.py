from odoo import models, fields, api, _
import random


class ABTest(models.Model):
    _name = 'uellow.ab.test'
    _description = 'A/B Test'
    _inherit = ['mail.thread']
    _rec_name = 'name'

    name = fields.Char(required=True)
    product_id = fields.Many2one('product.template', required=True, ondelete='cascade')
    test_type = fields.Selection([
        ('price',       'Price'),
        ('title',       'Product Title'),
        ('description', 'Description'),
        ('image',       'Main Image'),
    ], required=True)

    state = fields.Selection([
        ('draft',   'Draft'),
        ('running', 'Running'),
        ('ended',   'Ended'),
    ], default='draft', tracking=True)

    # Variant A (current / control)
    variant_a_label = fields.Char('Variant A Label', default='Control')
    variant_a_value = fields.Text('Variant A Value')

    # Variant B (challenger)
    variant_b_label = fields.Char('Variant B Label', default='Challenger')
    variant_b_value = fields.Text('Variant B Value')

    # Traffic split
    traffic_split = fields.Integer('Traffic to B (%)', default=50)

    # Results
    a_views = fields.Integer('A Views', default=0, readonly=True)
    b_views = fields.Integer('B Views', default=0, readonly=True)
    a_conversions = fields.Integer('A Conversions', default=0, readonly=True)
    b_conversions = fields.Integer('B Conversions', default=0, readonly=True)
    a_revenue = fields.Float('A Revenue', default=0.0, readonly=True)
    b_revenue = fields.Float('B Revenue', default=0.0, readonly=True)

    a_conv_rate = fields.Float(compute='_compute_rates', string='A Conv%')
    b_conv_rate = fields.Float(compute='_compute_rates', string='B Conv%')
    winner = fields.Selection([('a','A Wins'),('b','B Wins'),('tie','Tie')],
                               compute='_compute_rates', store=True)

    min_sample_size = fields.Integer('Min Visitors per Variant', default=100)
    started_at = fields.Datetime('Started At')
    ended_at = fields.Datetime('Ended At')

    @api.depends('a_conversions', 'a_views', 'b_conversions', 'b_views')
    def _compute_rates(self):
        for t in self:
            t.a_conv_rate = (t.a_conversions / t.a_views * 100) if t.a_views else 0
            t.b_conv_rate = (t.b_conversions / t.b_views * 100) if t.b_views else 0
            if t.b_views >= t.min_sample_size and t.a_views >= t.min_sample_size:
                if t.b_conv_rate > t.a_conv_rate * 1.05:
                    t.winner = 'b'
                elif t.a_conv_rate > t.b_conv_rate * 1.05:
                    t.winner = 'a'
                else:
                    t.winner = 'tie'
            else:
                t.winner = False

    def get_variant_for_visitor(self, session_id):
        """Return 'a' or 'b' consistently for a visitor."""
        seed = hash(f'{self.id}-{session_id}') % 100
        return 'b' if seed < self.traffic_split else 'a'

    def action_start(self):
        self.write({'state': 'running', 'started_at': fields.Datetime.now()})

    def action_apply_winner(self):
        """Apply winning variant to product."""
        self.ensure_one()
        if not self.winner or self.winner == 'tie':
            return
        value = self.variant_b_value if self.winner == 'b' else self.variant_a_value
        if self.test_type == 'price':
            try:
                self.product_id.list_price = float(value)
            except (ValueError, TypeError):
                pass
        elif self.test_type in ('title', 'description'):
            field = 'name' if self.test_type == 'title' else 'description_sale'
            self.product_id.write({field: value})
        self.write({'state': 'ended', 'ended_at': fields.Datetime.now()})
        self.message_post(body=_('Applied winning variant %s to product.') % self.winner.upper())
