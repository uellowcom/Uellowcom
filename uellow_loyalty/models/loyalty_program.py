from odoo import models, fields, api, _


class LoyaltyProgram(models.Model):
    """
    Global loyalty program settings.
    Singleton — one record per company.
    """
    _name = 'uellow.loyalty.program'
    _description = 'Loyalty Program'
    _rec_name = 'name'

    name = fields.Char(default='Uellow Loyalty Program')
    active = fields.Boolean(default=True)

    # Earning rules
    points_per_kd = fields.Float('Points per 1 KD spent', default=10.0)
    points_review_text = fields.Integer('Points for text review', default=5)
    points_review_photo = fields.Integer('Points for photo review', default=15)
    points_review_video = fields.Integer('Points for video review', default=30)
    points_referral = fields.Integer('Points for referral', default=50)
    points_first_purchase = fields.Integer('Bonus on first purchase', default=100)
    points_birthday = fields.Integer('Birthday bonus points', default=200)

    # Redemption
    points_per_kd_redeem = fields.Float(
        'Points needed to redeem 1 KD', default=100.0,
    )
    min_points_redeem = fields.Integer('Minimum points to redeem', default=100)
    max_redeem_pct = fields.Float(
        'Max discount from points (%)', default=20.0,
        help='Customer cannot pay more than X% of order using points',
    )

    # Expiry
    points_expire_days = fields.Integer(
        'Points expire after (days)', default=365,
        help='0 = never expire',
    )

    # Tiers
    tier_silver_min = fields.Integer('Silver tier minimum points', default=1000)
    tier_gold_min = fields.Integer('Gold tier minimum points', default=5000)
    tier_platinum_min = fields.Integer('Platinum tier minimum points', default=15000)

    silver_multiplier = fields.Float('Silver earning multiplier', default=1.5)
    gold_multiplier = fields.Float('Gold earning multiplier', default=2.0)
    platinum_multiplier = fields.Float('Platinum earning multiplier', default=3.0)

    @api.model
    def get_program(self):
        program = self.search([], limit=1)
        if not program:
            program = self.create({'name': 'Uellow Loyalty Program'})
        return program


class LoyaltyTierRule(models.Model):
    """Extra rewards per tier — free shipping, discount vouchers."""
    _name = 'uellow.loyalty.tier.rule'
    _description = 'Loyalty Tier Rule'

    program_id = fields.Many2one('uellow.loyalty.program', ondelete='cascade')
    tier = fields.Selection([
        ('silver',   'Silver'),
        ('gold',     'Gold'),
        ('platinum', 'Platinum'),
    ], required=True)
    benefit = fields.Selection([
        ('free_shipping',    'Free Shipping'),
        ('discount_voucher', 'Discount Voucher'),
        ('early_access',     'Early Access to Flash Sales'),
        ('priority_support', 'Priority Support'),
        ('birthday_gift',    'Birthday Gift'),
    ], required=True)
    value = fields.Float('Benefit Value', default=0.0)
    description = fields.Char('Description')
