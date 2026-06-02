"""Singleton SEO configuration.

Sensitive secrets (API keys) are mirrored to `ir.config_parameter` so they
follow the same handling as the rest of the AI keys in the project. The
model field stays for the form UI but its persistence go-to is the ICP.
"""
from odoo import models, fields, api

_AI_KEY_ICP = 'uellow_seo.anthropic_api_key'


class SEOConfig(models.Model):
    _name = 'uellow.seo.config'
    _description = 'SEO Automation Config'

    name = fields.Char(default='SEO Settings')
    active = fields.Boolean(default=True)

    # API key — mirrored to ir.config_parameter on write so XML-RPC/CSV
    # export can't leak it via raw model reads by other modules.
    anthropic_api_key = fields.Char(
        'Anthropic API Key',
        compute='_compute_api_key', inverse='_inverse_api_key', store=False,
    )
    ai_model = fields.Selection([
        ('claude-haiku-4-5-20251001',     'Claude Haiku 4.5 (cheap)'),
        ('claude-sonnet-4-20250514',      'Claude Sonnet 4 (balanced)'),
        ('claude-opus-4-20250514',        'Claude Opus 4 (premium)'),
    ], default='claude-haiku-4-5-20251001', string='AI Model')

    # Branding
    site_name_en = fields.Char('Site Name (EN)', default='Uellow')
    site_name_ar = fields.Char('Site Name (AR)', default='يلو')
    default_suffix_en = fields.Char('Title Suffix (EN)', default='| Uellow Kuwait')
    default_suffix_ar = fields.Char('Title Suffix (AR)', default='| يلو الكويت')

    # Behaviour
    auto_generate_new = fields.Boolean('Auto-generate for new products', default=True)
    overwrite_existing = fields.Boolean('Overwrite existing SEO', default=False)
    include_price = fields.Boolean('Include price in title', default=False)
    include_brand = fields.Boolean('Include brand', default=True)
    schema_markup = fields.Boolean('Add JSON-LD Product schema', default=True)

    # Length windows (E7/B10)
    max_title_chars = fields.Integer('Max title characters', default=60,
        help='Google truncates above ~60 chars. Authors get a live counter.')
    max_desc_chars = fields.Integer('Max description characters', default=160,
        help='Optimal range 150-160 for Google SERP snippets.')

    # Cost guards
    cron_batch_size = fields.Integer('Cron batch size', default=50)
    daily_call_cap  = fields.Integer('Daily AI call cap', default=500,
        help='Hard ceiling on AI calls per day across all generators.')

    # Organization schema (for global Organization JSON-LD)
    org_legal_name = fields.Char('Organization Legal Name', default='Uellow W.L.L')
    org_logo_url = fields.Char('Organization Logo URL',
        default='/web/binary/company_logo')
    org_social_urls = fields.Text('Social Profile URLs (one per line)',
        help='Instagram, Twitter/X, Facebook, etc. Used for schema.org sameAs.')
    org_phone = fields.Char('Contact Phone', default='+965 9717 0933')
    org_email = fields.Char('Contact Email', default='info@uellow.com')

    # Search-engine verification meta (F9)
    google_verification    = fields.Char('Google Search Console code')
    bing_verification      = fields.Char('Bing Webmaster code')
    yandex_verification    = fields.Char('Yandex Webmaster code')
    pinterest_verification = fields.Char('Pinterest verification code')
    facebook_app_id        = fields.Char('Facebook App ID')

    # robots.txt content (rendered by /robots.txt controller)
    robots_txt = fields.Text(
        'robots.txt content',
        default=(
            'User-agent: *\n'
            'Disallow: /web/login\n'
            'Disallow: /shop/cart\n'
            'Disallow: /shop/checkout\n'
            'Disallow: /shop/payment\n'
            'Disallow: /my\n'
            '\n'
            'Sitemap: /sitemap.xml\n'
            'Sitemap: /sitemap-pages.xml\n'
        ),
    )

    @api.depends_context('uid')
    def _compute_api_key(self):
        icp = self.env['ir.config_parameter'].sudo()
        for r in self:
            r.anthropic_api_key = icp.get_param(_AI_KEY_ICP, '')

    def _inverse_api_key(self):
        icp = self.env['ir.config_parameter'].sudo()
        for r in self:
            icp.set_param(_AI_KEY_ICP, r.anthropic_api_key or '')

    @api.model
    def get_config(self):
        """Return the singleton, falling back to a defaults-only synthetic
        instance if the data record hasn't loaded yet (during install)."""
        cfg = self.search([], limit=1)
        if not cfg:
            cfg = self.create({})
        return cfg

    def get_api_key(self):
        """Convenience: returns the key from ICP without touching the field."""
        return self.env['ir.config_parameter'].sudo().get_param(_AI_KEY_ICP, '')

    def increment_daily_calls(self, n=1):
        """Bump the daily AI-call counter. Returns True if still under cap."""
        from datetime import date
        icp = self.env['ir.config_parameter'].sudo()
        today_key = 'uellow_seo.daily_calls_' + str(date.today())
        try:
            current = int(icp.get_param(today_key, '0'))
        except (TypeError, ValueError):
            current = 0
        new = current + n
        icp.set_param(today_key, str(new))
        return new <= (self.daily_call_cap or 10**9)
