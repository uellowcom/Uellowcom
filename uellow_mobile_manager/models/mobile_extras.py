# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta


class MobileAppOrder(models.Model):
    """Tracks which orders came from the mobile app."""
    _name = 'mobile.app.order'
    _description = 'Mobile App Order Tracking'
    _order = 'create_date desc'
    _rec_name = 'sale_order_id'

    sale_order_id = fields.Many2one(
        'sale.order', string='Sale Order', required=True, ondelete='cascade', index=True
    )
    session_id = fields.Many2one('mobile.session', string='App Session', ondelete='set null')
    platform = fields.Selection([
        ('android', 'Android'),
        ('ios', 'iOS'),
    ], string='Platform')
    app_version = fields.Char(string='App Version')
    device_model = fields.Char(string='Device Model')
    order_source = fields.Selection([
        ('home_slider', 'Home Slider'),
        ('flash_sale', 'Flash Sale'),
        ('category', 'Category Browse'),
        ('search', 'Search'),
        ('brand_section', 'Brand Section'),
        ('notification', 'Push Notification'),
        ('direct', 'Direct / Unknown'),
    ], string='Order Source', default='direct')
    notification_id = fields.Many2one('mobile.notification', string='From Notification')

    # Denormalized for fast reporting
    order_date = fields.Datetime(related='sale_order_id.date_order', store=True)
    amount_total = fields.Monetary(related='sale_order_id.amount_total', store=True)
    currency_id = fields.Many2one(related='sale_order_id.currency_id', store=True)
    partner_id = fields.Many2one(related='sale_order_id.partner_id', store=True)
    state = fields.Selection(related='sale_order_id.state', store=True)

    website_id = fields.Many2one('website', string='Website',
                                 default=lambda self: self.env['website'].search([], limit=1))

    @api.model
    def register_app_order(self, order_id, session_token=None, source='direct', notification_id=None):
        """Called from Flutter when order is placed."""
        order = self.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return False
        session = None
        if session_token:
            session = self.env['mobile.session'].sudo().search(
                [('session_token', '=', session_token)], limit=1
            )
        vals = {
            'sale_order_id': order.id,
            'order_source': source,
            'platform': session.platform if session else False,
            'app_version': session.app_version if session else False,
            'device_model': session.device_name if session else False,
        }
        if session:
            vals['session_id'] = session.id
        if notification_id:
            vals['notification_id'] = notification_id
        return self.create(vals).id


class MobileOnboardingScreen(models.Model):
    """Onboarding / Welcome screens shown on first app open."""
    _name = 'mobile.onboarding.screen'
    _description = 'Mobile App Onboarding Screen'
    _order = 'sequence asc'

    name = fields.Char(string='Screen Title', required=True, translate=True)
    name_ar = fields.Char(string='Arabic Title')
    description = fields.Text(string='Description', translate=True)
    description_ar = fields.Text(string='Arabic Description')
    image = fields.Binary(string='Screen Image', required=True, attachment=True)
    image_filename = fields.Char()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    button_label = fields.Char(string='Button Label', default='Next', translate=True)
    button_label_ar = fields.Char(string='Arabic Button Label', default='التالي')
    is_last = fields.Boolean(string='Is Last Screen', default=False)
    website_id = fields.Many2one('website', string='Website',
                                 default=lambda self: self.env['website'].search([], limit=1))


class MobileSearchAnalytic(models.Model):
    """Tracks what users search for in the app."""
    _name = 'mobile.search.analytic'
    _description = 'Mobile App Search Analytics'
    _order = 'create_date desc'

    keyword = fields.Char(string='Search Keyword', required=True, index=True)
    results_count = fields.Integer(string='Results Found', default=0)
    session_id = fields.Many2one('mobile.session', string='Session', ondelete='set null')
    platform = fields.Selection([('android', 'Android'), ('ios', 'iOS')], string='Platform')
    clicked_product_id = fields.Many2one('product.template', string='Clicked Product')
    led_to_order = fields.Boolean(string='Led to Order', default=False)
    website_id = fields.Many2one('website', string='Website',
                                 default=lambda self: self.env['website'].search([], limit=1))

    # Aggregated stats (computed on demand)
    @api.model
    def get_top_keywords(self, limit=20, days=30):
        """Return top searched keywords."""
        since = datetime.now() - timedelta(days=days)
        self.env.cr.execute("""
            SELECT keyword, COUNT(*) as count,
                   AVG(results_count) as avg_results,
                   SUM(CASE WHEN led_to_order THEN 1 ELSE 0 END) as orders
            FROM mobile_search_analytic
            WHERE create_date >= %s
            GROUP BY keyword
            ORDER BY count DESC
            LIMIT %s
        """, (since, limit))
        return self.env.cr.dictfetchall()

    @api.model
    def get_zero_result_keywords(self, limit=20, days=30):
        """Keywords that returned 0 results — product gaps."""
        since = datetime.now() - timedelta(days=days)
        self.env.cr.execute("""
            SELECT keyword, COUNT(*) as count
            FROM mobile_search_analytic
            WHERE results_count = 0 AND create_date >= %s
            GROUP BY keyword
            ORDER BY count DESC
            LIMIT %s
        """, (since, limit))
        return self.env.cr.dictfetchall()


class MobileAbTest(models.Model):
    """A/B Testing for sliders and banners."""
    _name = 'mobile.ab.test'
    _description = 'Mobile A/B Test'
    _order = 'create_date desc'

    name = fields.Char(string='Test Name', required=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
    ], default='draft', string='Status')

    test_type = fields.Selection([
        ('slider', 'Hero Slider'),
        ('section_layout', 'Section Layout'),
        ('banner', 'Feature Banner'),
    ], string='Test Type', required=True)

    slider_a_id = fields.Many2one('mobile.slider', string='Variant A — Slider')
    slider_b_id = fields.Many2one('mobile.slider', string='Variant B — Slider')

    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')

    # Results
    impressions_a = fields.Integer(string='Impressions A', default=0)
    impressions_b = fields.Integer(string='Impressions B', default=0)
    clicks_a = fields.Integer(string='Clicks A', default=0)
    clicks_b = fields.Integer(string='Clicks B', default=0)
    orders_a = fields.Integer(string='Orders A', default=0)
    orders_b = fields.Integer(string='Orders B', default=0)

    ctr_a = fields.Float(string='CTR A (%)', compute='_compute_ctr')
    ctr_b = fields.Float(string='CTR B (%)', compute='_compute_ctr')
    winner = fields.Selection([('a', 'Variant A'), ('b', 'Variant B'), ('tie', 'Tie')],
                               string='Winner', compute='_compute_winner', store=True)

    website_id = fields.Many2one('website', string='Website',
                                 default=lambda self: self.env['website'].search([], limit=1))

    @api.depends('impressions_a', 'clicks_a', 'impressions_b', 'clicks_b')
    def _compute_ctr(self):
        for rec in self:
            rec.ctr_a = (rec.clicks_a / rec.impressions_a * 100) if rec.impressions_a else 0
            rec.ctr_b = (rec.clicks_b / rec.impressions_b * 100) if rec.impressions_b else 0

    @api.depends('ctr_a', 'ctr_b')
    def _compute_winner(self):
        for rec in self:
            if rec.ctr_a > rec.ctr_b:
                rec.winner = 'a'
            elif rec.ctr_b > rec.ctr_a:
                rec.winner = 'b'
            else:
                rec.winner = 'tie'

    def action_start(self):
        self.write({'state': 'running', 'start_date': datetime.now().date()})

    def action_complete(self):
        self.write({'state': 'completed', 'end_date': datetime.now().date()})


class MobileFeatureFlag(models.Model):
    """Feature flags — toggle app features without a new build."""
    _name = 'mobile.feature.flag'
    _description = 'Mobile App Feature Flag'
    _rec_name = 'key'

    key = fields.Char(string='Feature Key', required=True, index=True,
                      help='Used in Flutter code, e.g. "chat_enabled", "wallet_visible"')
    label = fields.Char(string='Display Name', required=True)
    description = fields.Text(string='Description')
    enabled = fields.Boolean(string='Enabled', default=True)
    platforms = fields.Selection([
        ('all', 'All Platforms'),
        ('android', 'Android Only'),
        ('ios', 'iOS Only'),
    ], string='Platforms', default='all')
    min_app_version = fields.Char(string='Min App Version', help='e.g. 2.0.0')
    category = fields.Selection([
        ('ui', 'UI / Design'),
        ('payment', 'Payment'),
        ('social', 'Social Features'),
        ('commerce', 'Commerce'),
        ('debug', 'Debug / Dev'),
    ], string='Category', default='ui')
    website_id = fields.Many2one('website', string='Website',
                                 default=lambda self: self.env['website'].search([], limit=1))

    _sql_constraints = [
        ('key_unique', 'unique(key, website_id)', 'Feature key must be unique per website.')
    ]


class MobileAppCoupon(models.Model):
    """App-exclusive coupons."""
    _name = 'mobile.app.coupon'
    _description = 'Mobile App Exclusive Coupon'
    _order = 'create_date desc'

    name = fields.Char(string='Coupon Name', required=True)
    code = fields.Char(string='Coupon Code', required=True, index=True)
    active = fields.Boolean(default=True)

    discount_type = fields.Selection([
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    ], string='Discount Type', default='percent', required=True)
    discount_value = fields.Float(string='Discount Value')
    min_order_amount = fields.Monetary(string='Min Order Amount')
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.company.currency_id)
    max_uses = fields.Integer(string='Max Uses', default=0, help='0 = unlimited')
    uses_count = fields.Integer(string='Times Used', default=0, readonly=True)
    per_user_limit = fields.Integer(string='Per User Limit', default=1)

    valid_from = fields.Date(string='Valid From')
    valid_until = fields.Date(string='Valid Until')

    # Targeting
    new_users_only = fields.Boolean(string='New Users Only', default=False)
    platform = fields.Selection([
        ('all', 'All Platforms'),
        ('android', 'Android Only'),
        ('ios', 'iOS Only'),
    ], string='Platform', default='all')

    # Show in app
    show_in_app = fields.Boolean(string='Show in App Banner', default=True)
    banner_image = fields.Binary(string='Coupon Banner Image', attachment=True)
    description = fields.Char(string='Description shown in app', translate=True)

    website_id = fields.Many2one('website', string='Website',
                                 default=lambda self: self.env['website'].search([], limit=1))

    _sql_constraints = [
        ('code_unique', 'unique(code, website_id)', 'Coupon code must be unique.')
    ]

    def is_valid(self):
        self.ensure_one()
        today = datetime.now().date()
        if self.valid_from and today < self.valid_from:
            return False, 'Coupon not yet valid'
        if self.valid_until and today > self.valid_until:
            return False, 'Coupon expired'
        if self.max_uses and self.uses_count >= self.max_uses:
            return False, 'Coupon usage limit reached'
        return True, 'OK'
