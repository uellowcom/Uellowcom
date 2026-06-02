from odoo import api, fields, models


class PerfConfig(models.Model):
    """Singleton settings for the Perf Guardian."""
    _name = 'uellow.perf.config'
    _description = 'Uellow Performance — settings'

    name = fields.Char(default='Perf Guardian settings', required=True)

    # ─── Bot quota ─────────────────────────────────────────────
    bot_quota_enabled = fields.Boolean(default=True)
    bot_quota_soft = fields.Boolean(default=False)
    bot_429_retry_after = fields.Integer(default=86400)
    burst_per_ip_per_min = fields.Integer(
        string='Per-IP burst limit (req/min)', default=120,
        help='Sliding-window cap per IP within a bot class. 0 = disabled.')

    # ─── RUM ───────────────────────────────────────────────────
    rum_enabled = fields.Boolean(default=True)
    rum_sample_rate = fields.Float(default=0.10)
    rum_retention_days = fields.Integer(default=30)
    rum_beacon_per_ip_per_min = fields.Integer(
        string='RUM beacon rate-limit (per IP/min)', default=30)

    # ─── Synthetic ─────────────────────────────────────────────
    synthetic_enabled = fields.Boolean(default=True)
    synthetic_urls = fields.Text(
        default='/\n/shop\n/blog\n/web/login\n/ar/\n/ar/shop')
    synthetic_lcp_warn_ms = fields.Integer(default=2500)
    synthetic_lcp_crit_ms = fields.Integer(default=4000)

    # ─── Slow-query ────────────────────────────────────────────
    slowq_enabled = fields.Boolean(default=True)
    slowq_threshold_ms = fields.Integer(default=500)

    # ─── Cache health ──────────────────────────────────────────
    cache_health_target_pct = fields.Integer(default=75)

    # ─── SSL + Domain expiry ───────────────────────────────────
    ssl_monitor_enabled = fields.Boolean(default=True)
    ssl_monitor_domain = fields.Char(string='Domain to check',
        default='www.uellow.com')
    ssl_warn_days = fields.Integer(default=30)
    ssl_crit_days = fields.Integer(default=7)

    # ─── 5xx error rate ────────────────────────────────────────
    error_rate_enabled = fields.Boolean(default=True)
    error_rate_warn_per_min = fields.Integer(default=5)
    error_rate_crit_per_min = fields.Integer(default=20)

    # ─── Anomaly detection ─────────────────────────────────────
    anomaly_enabled = fields.Boolean(default=True)
    anomaly_z_threshold = fields.Float(default=2.5,
        help='Z-score threshold above which a metric is anomalous.')

    # ─── Alerts: Email + Beena + Webhooks ──────────────────────
    alert_email = fields.Char(string='Alert email')
    alert_beena = fields.Boolean(default=False)
    alert_slack_webhook = fields.Char(string='Slack webhook URL',
        help='https://hooks.slack.com/services/T.../B.../...')
    alert_discord_webhook = fields.Char(string='Discord webhook URL')
    alert_telegram_token = fields.Char(string='Telegram bot token')
    alert_telegram_chat = fields.Char(string='Telegram chat ID')
    alert_sentry_dsn = fields.Char(string='Sentry DSN',
        help='Optional — post critical alerts to Sentry as events.')

    # ─── Image audit ───────────────────────────────────────────
    image_audit_enabled = fields.Boolean(default=True)
    image_size_threshold_kb = fields.Integer(default=500)

    # ─── CDN purge (Cloudflare) ────────────────────────────────
    cf_purge_enabled = fields.Boolean(default=False)
    cf_zone_id = fields.Char()
    cf_api_token = fields.Char()

    # ─── Metrics export ────────────────────────────────────────
    export_token = fields.Char()

    # ─── Dashboard ─────────────────────────────────────────────
    dashboard_auto_refresh_seconds = fields.Integer(default=30,
        help='Dashboard auto-refresh interval. 0 = no auto-refresh.')

    # ─── Multi-website filter ──────────────────────────────────
    website_filter_ids = fields.Many2many('website',
        string='Websites to include',
        help='If set, dashboard + RUM only count traffic to these websites.')

    # ─── ASN / IP enrichment ───────────────────────────────────
    ipinfo_token = fields.Char(string='ipinfo.io token',
        help='Free tier works without token (50k/month); paid tier accepts a token.')

    # ─── CrUX (Chrome UX Report) ───────────────────────────────
    crux_enabled = fields.Boolean(default=False)
    crux_api_key = fields.Char(string='CrUX API key')

    # ─── Bundle size monitor ───────────────────────────────────
    bundle_monitor_enabled = fields.Boolean(default=True)
    bundle_urls = fields.Text(string='Bundle URLs (one per line)',
        default='/web/assets/1/d1ba737/web.assets_frontend_minimal.min.js\n'
                '/web/assets/1/74cfd6e/web.assets_frontend_lazy.min.js\n'
                '/web/assets/1/b7e9f92/web.assets_frontend.min.css')

    # ─── Self-check ────────────────────────────────────────────
    self_check_enabled = fields.Boolean(default=True)

    @api.model
    def get_config(self):
        rec = self.search([], limit=1)
        if not rec:
            rec = self.create({})
        return rec
