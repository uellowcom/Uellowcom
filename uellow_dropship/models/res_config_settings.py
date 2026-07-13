# -*- coding: utf-8 -*-
"""Global dropship policy settings (prefix ``uellow_dropship.``).

Per-provider credentials live on ``dropship.provider`` records; these are the
store-wide toggles: eligibility gate, pricing markup, storefront brand/website,
and import field selection.
"""
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ds_enabled = fields.Boolean(
        string="Enable Dropshipping",
        config_parameter='uellow_dropship.enabled')
    ds_brand_name = fields.Char(
        string="Storefront Brand", default="Uellow World",
        config_parameter='uellow_dropship.brand_name')
    ds_website_id = fields.Many2one(
        'website', string="Dropship Website",
        config_parameter='uellow_dropship.website_id',
        help="Products are published only on this isolated website.")
    ds_default_markup = fields.Float(
        string="Default Markup %", default=0.0,
        config_parameter='uellow_dropship.default_markup')
    ds_min_price = fields.Float(
        string="Min Landed Price (KWD)", default=0.0,
        config_parameter='uellow_dropship.min_price',
        help="Eligibility gate: listings below this landed price are hidden.")
    ds_auto_publish = fields.Boolean(
        string="Auto-publish on Materialize",
        config_parameter='uellow_dropship.auto_publish')
    ds_import_fields = fields.Char(
        string="Imported Fields",
        default="images,description,specs,shipping",
        config_parameter='uellow_dropship.import_fields',
        help="Comma-separated: images,description,specs,shipping,variants")
    ds_prepaid_only = fields.Boolean(
        string="Prepaid Only (no COD)", default=True,
        config_parameter='uellow_dropship.prepaid_only')
    ds_monthly_cost_cap = fields.Float(
        string="Monthly API/Cost Cap (USD)", default=0.0,
        config_parameter='uellow_dropship.monthly_cost_cap')
    ds_ai_rewrite_website = fields.Boolean(
        string="Allow AI Rewrite on Website Products too",
        config_parameter='uellow_dropship.ai_rewrite_website')
    ds_show_videos = fields.Boolean(
        string="Show Product Videos", default=True,
        config_parameter='uellow_dropship.show_videos')
    ds_show_deals = fields.Boolean(
        string="Show Deals / Offers Rail", default=True,
        config_parameter='uellow_dropship.show_deals')
    ds_deal_min_percent = fields.Float(
        string="Min Discount % for Deals", default=15.0,
        config_parameter='uellow_dropship.deal_min_percent')
    ds_exclude_flash_deals = fields.Boolean(
        string="Skip Flash / Limited-time Deals", default=True,
        config_parameter='uellow_dropship.exclude_flash_deals',
        help="Don't import products whose provider price is a short-lived "
             "flash/seckill deal — those prices expire and go stale, which "
             "causes wrong prices for customers.")
    ds_max_discount_percent = fields.Float(
        string="Max Discount % on Import", default=0.0,
        config_parameter='uellow_dropship.max_discount_percent',
        help="Skip importing anything discounted beyond this % (0 = no limit). "
             "Very large markdowns are usually unstable flash prices.")

    # ---- Auto-import -------------------------------------------------- #
    ds_auto_import = fields.Boolean(
        string="Auto-import (Cron)",
        config_parameter='uellow_dropship.auto_import')
    ds_import_interval_hours = fields.Integer(
        string="Import Every (hours)", default=12,
        config_parameter='uellow_dropship.import_interval_hours')
    ds_import_keywords = fields.Char(
        string="Import Keywords", config_parameter='uellow_dropship.import_keywords',
        help="Comma-separated search terms to pull each run.")
    ds_import_categories = fields.Char(
        string="Import Categories", config_parameter='uellow_dropship.import_categories',
        help="Comma-separated provider category ids to pull.")
    ds_import_max_products = fields.Integer(
        string="Max Products / Run", default=500,
        config_parameter='uellow_dropship.import_max_products')
    ds_import_min_orders = fields.Integer(
        string="Min Provider Orders", default=0,
        config_parameter='uellow_dropship.import_min_orders',
        help="Skip listings with fewer sales than this (quality gate).")
    ds_import_min_rating = fields.Float(
        string="Min Rating", default=0.0,
        config_parameter='uellow_dropship.import_min_rating')

    # ---- Exclusion filters ------------------------------------------- #
    ds_exclude_keywords = fields.Char(
        string="Exclude Keywords", config_parameter='uellow_dropship.exclude_keywords',
        help="Skip products whose title contains any of these (comma-separated).")
    ds_exclude_categories = fields.Char(
        string="Exclude Categories", config_parameter='uellow_dropship.exclude_categories')
    ds_exclude_brands = fields.Char(
        string="Exclude Brands", config_parameter='uellow_dropship.exclude_brands',
        help="Avoid trademarked brands to prevent takedowns (e.g. Apple, Nike).")
    ds_max_price = fields.Float(
        string="Max Landed Price (KWD)", default=0.0,
        config_parameter='uellow_dropship.max_price')
    ds_max_ship_days = fields.Integer(
        string="Max Shipping Days", default=0,
        config_parameter='uellow_dropship.max_ship_days',
        help="Skip items that ship slower than this (0 = no limit).")
    ds_exclude_no_image = fields.Boolean(
        string="Skip Items Without Image", default=True,
        config_parameter='uellow_dropship.exclude_no_image')
    ds_exclude_no_video = fields.Boolean(
        string="Require Video", config_parameter='uellow_dropship.exclude_no_video')

    # ---- Pricing rules ----------------------------------------------- #
    ds_price_rounding = fields.Selection([
        ('none', 'No rounding'),
        ('900', 'End in .900'),
        ('990', 'End in .990'),
        ('950', 'End in .950'),
    ], string="Price Rounding", default='900',
        config_parameter='uellow_dropship.price_rounding')
    ds_fx_buffer = fields.Float(
        string="FX Buffer %", default=3.0,
        config_parameter='uellow_dropship.fx_buffer',
        help="Extra margin to absorb currency swings.")
    ds_customs_percent = fields.Float(
        string="Customs / Duty %", default=0.0,
        config_parameter='uellow_dropship.customs_percent')
    ds_min_margin = fields.Float(
        string="Min Margin %", default=10.0,
        config_parameter='uellow_dropship.min_margin',
        help="Guard: never list below this margin.")

    # ---- Sync / quality ---------------------------------------------- #
    ds_price_sync = fields.Boolean(
        string="Auto-sync Prices", default=True,
        config_parameter='uellow_dropship.price_sync')
    ds_stock_sync = fields.Boolean(
        string="Auto-sync Stock", default=True,
        config_parameter='uellow_dropship.stock_sync')
    ds_unpublish_oos = fields.Boolean(
        string="Unpublish When Out of Stock", default=True,
        config_parameter='uellow_dropship.unpublish_oos')
    ds_max_variants = fields.Integer(
        string="Max Variants / Product", default=0,
        config_parameter='uellow_dropship.max_variants')
    ds_import_variants = fields.Boolean(
        string="Build Product Variants (Color/Size)", default=True,
        config_parameter='uellow_dropship.import_variants',
        help="Recreate the provider's option selectors (Color, Size, …) with "
             "per-variant images on the Uellow product. Pricing stays uniform.")
    ds_dedupe = fields.Boolean(
        string="Skip Duplicates", default=True,
        config_parameter='uellow_dropship.dedupe')

    # ---- Order fulfilment -------------------------------------------- #
    ds_auto_place_order = fields.Boolean(
        string="Auto-place Provider Order on Payment",
        config_parameter='uellow_dropship.auto_place_order')
    ds_order_note = fields.Char(
        string="Provider Order Note", config_parameter='uellow_dropship.order_note',
        help="Note sent with each provider order, e.g. 'no invoice / no promo inside'.")
    ds_hold_hours = fields.Integer(
        string="Hold Before Placing (hours)", default=2,
        config_parameter='uellow_dropship.hold_hours',
        help="Delay before forwarding, so fraud/cancels are caught first.")
    ds_default_zip = fields.Char(
        string="Default Zip / Postal Code", default="00000",
        config_parameter='uellow_dropship.default_zip',
        help="Fallback numeric postal code sent to the provider when the "
             "customer's address has no valid zip (AliExpress rejects "
             "non-numeric zips like an Arabic governorate name).")

    # ---- Chrome extension importer ----------------------------------- #
    ds_ext_api_key = fields.Char(
        string="Extension API Key",
        config_parameter='uellow_dropship.ext_api_key',
        help="Shared secret the Chrome extension sends to import products from "
             "aliexpress.com. Paste the same value into the extension settings.")
    ds_ext_max_per_call = fields.Integer(
        string="Extension Max Products / Import", default=60,
        config_parameter='uellow_dropship.ext_max_per_call',
        help="Safety cap on how many products one 'import this page' click "
             "can pull at once.")

    def action_generate_ext_key(self):
        """Generate a fresh random key for the Chrome extension."""
        import uuid
        key = uuid.uuid4().hex
        self.env['ir.config_parameter'].sudo().set_param(
            'uellow_dropship.ext_api_key', key)
        self.ds_ext_api_key = key
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Key generated',
                       'message': 'Paste this into the extension settings: %s' % key,
                       'type': 'success', 'sticky': True},
        }

    # ---- Storefront / UX --------------------------------------------- #
    ds_show_eta_badge = fields.Boolean(
        string="Show Delivery ETA Badge", default=True,
        config_parameter='uellow_dropship.show_eta_badge')
    ds_eta_extra_days = fields.Integer(
        string="ETA Safety Buffer (days)", default=3,
        config_parameter='uellow_dropship.eta_extra_days',
        help="Added to the provider ETA shown to the customer.")
    ds_show_origin_badge = fields.Boolean(
        string="Show 'Ships Internationally' Badge", default=True,
        config_parameter='uellow_dropship.show_origin_badge')
    ds_hide_supplier_images_with_text = fields.Boolean(
        string="Hide Images With Watermark/Text", default=True,
        config_parameter='uellow_dropship.hide_text_images')
    ds_default_lang = fields.Selection([
        ('en', 'English first'), ('ar', 'Arabic first'),
    ], string="Default Content Language", default='en',
        config_parameter='uellow_dropship.default_lang')
    ds_products_per_page = fields.Integer(
        string="Products / Page", default=40,
        config_parameter='uellow_dropship.products_per_page')
    ds_sort_default = fields.Selection([
        ('deal', 'Best deals'), ('new', 'Newest'),
        ('price_asc', 'Price low→high'), ('orders', 'Best-selling'),
    ], string="Default Sort", default='orders',
        config_parameter='uellow_dropship.sort_default')

    # ---- Reviews / social proof -------------------------------------- #
    ds_import_reviews = fields.Boolean(
        string="Import Provider Reviews", default=True,
        config_parameter='uellow_dropship.import_reviews')
    ds_min_review_stars = fields.Float(
        string="Only Import Reviews ≥ Stars", default=4.0,
        config_parameter='uellow_dropship.min_review_stars')
    ds_detail_ttl_hours = fields.Integer(
        string="Product-detail Cache (hours)", default=12,
        config_parameter='uellow_dropship.detail_ttl_hours',
        help="How long the full description / specs / shipping / review summary "
             "is cached before a fresh provider fetch on the next product open.")
    ds_fake_urgency = fields.Boolean(
        string="Show 'X sold today' Social Proof",
        config_parameter='uellow_dropship.social_proof')

    # ---- SEO --------------------------------------------------------- #
    ds_noindex = fields.Boolean(
        string="No-index Dropship Pages", default=True,
        config_parameter='uellow_dropship.noindex',
        help="Avoid duplicate-content SEO penalties on the main domain.")
    ds_auto_seo = fields.Boolean(
        string="Auto-generate SEO (title/meta) via AI", default=True,
        config_parameter='uellow_dropship.auto_seo')
    ds_canonical_host = fields.Char(
        string="Canonical Host", config_parameter='uellow_dropship.canonical_host')

    # ---- Returns / policy -------------------------------------------- #
    ds_returns_policy = fields.Selection([
        ('none', 'No returns'), ('store_credit', 'Store credit only'),
        ('refund', 'Refund allowed'),
    ], string="Returns Policy", default='store_credit',
        config_parameter='uellow_dropship.returns_policy')
    ds_return_window_days = fields.Integer(
        string="Return Window (days)", default=7,
        config_parameter='uellow_dropship.return_window_days')

    # ---- Notifications ------------------------------------------------ #
    ds_notify_on_import = fields.Boolean(
        string="Notify Admin on Import", config_parameter='uellow_dropship.notify_import')
    ds_notify_price_spike = fields.Boolean(
        string="Alert on Cost Spike", default=True,
        config_parameter='uellow_dropship.notify_price_spike')
    ds_price_spike_percent = fields.Float(
        string="Cost Spike Threshold %", default=20.0,
        config_parameter='uellow_dropship.price_spike_percent')
    ds_notify_tracking = fields.Boolean(
        string="Push Tracking Updates to Customer", default=True,
        config_parameter='uellow_dropship.notify_tracking')

    # ---- Caps / safety ------------------------------------------------ #
    ds_daily_order_cap = fields.Integer(
        string="Max Provider Orders / Day", default=0,
        config_parameter='uellow_dropship.daily_order_cap')
    ds_max_listings = fields.Integer(
        string="Max Total Listings", default=0,
        config_parameter='uellow_dropship.max_listings',
        help="Hard cap on dropship.product rows (0 = unlimited).")
    ds_purge_stale_days = fields.Integer(
        string="Purge Unsold Listings After (days)", default=0,
        config_parameter='uellow_dropship.purge_stale_days',
        help="Delete never-ordered listings older than this, to keep the table lean.")
    ds_fail_closed = fields.Boolean(
        string="Fail-closed (hide on provider error)", default=True,
        config_parameter='uellow_dropship.fail_closed')

    # ---- AI ----------------------------------------------------------- #
    ds_ai_auto_translate = fields.Boolean(
        string="Auto-translate Titles to Arabic", default=True,
        config_parameter='uellow_dropship.ai_auto_translate')
    ds_ai_model = fields.Char(
        string="AI Model", default="claude-haiku-4-5-20251001",
        config_parameter='uellow_dropship.ai_model')
    ds_ai_tone = fields.Char(
        string="AI Rewrite Tone", default="clean, honest, concise",
        config_parameter='uellow_dropship.ai_tone')

    # ---- Server-load protection -------------------------------------- #
    ds_import_batch_size = fields.Integer(
        string="Import Batch Size", default=50,
        config_parameter='uellow_dropship.import_batch_size',
        help="Rows processed + committed per chunk, so a run never locks the DB.")
    ds_rate_limit_ms = fields.Integer(
        string="Delay Between API Calls (ms)", default=300,
        config_parameter='uellow_dropship.rate_limit_ms',
        help="Throttle provider calls to stay under rate limits and CPU spikes.")
    ds_cron_time_budget = fields.Integer(
        string="Cron Time Budget (seconds)", default=120,
        config_parameter='uellow_dropship.cron_time_budget',
        help="Each cron run stops after this many seconds and resumes next time.")
    ds_offpeak_only = fields.Boolean(
        string="Run Imports Off-peak Only", default=True,
        config_parameter='uellow_dropship.offpeak_only')
    ds_offpeak_start = fields.Integer(
        string="Off-peak Start (hour)", default=1,
        config_parameter='uellow_dropship.offpeak_start')
    ds_offpeak_end = fields.Integer(
        string="Off-peak End (hour)", default=6,
        config_parameter='uellow_dropship.offpeak_end')
    ds_pause_when_busy = fields.Boolean(
        string="Pause When Server Busy", default=True,
        config_parameter='uellow_dropship.pause_when_busy',
        help="Skip a run if system load is high (perf-guardian style).")
    ds_max_load = fields.Float(
        string="Max Load Average", default=4.0,
        config_parameter='uellow_dropship.max_load',
        help="Skip the run if 1-min load average exceeds this.")

    # ---- Product-page display (World storefront + app) ---------------- #
    ds_pp_show_specs = fields.Boolean(
        string="Show Specifications", default=True,
        config_parameter='uellow_dropship.pp_show_specs')
    ds_pp_show_reviews = fields.Boolean(
        string="Show Reviews", default=True,
        config_parameter='uellow_dropship.pp_show_reviews')
    ds_pp_show_shipping = fields.Boolean(
        string="Show Shipping Info", default=True,
        config_parameter='uellow_dropship.pp_show_shipping')
    ds_pp_show_seller = fields.Boolean(
        string="Show Seller / Store Info", default=False,
        config_parameter='uellow_dropship.pp_show_seller')
    ds_pp_show_variants = fields.Boolean(
        string="Show Variants", default=True,
        config_parameter='uellow_dropship.pp_show_variants')
    ds_pp_show_views = fields.Boolean(
        string="Show Views Count", default=True,
        config_parameter='uellow_dropship.pp_show_views')
    ds_pp_show_sold = fields.Boolean(
        string="Show Sold Count", default=True,
        config_parameter='uellow_dropship.pp_show_sold')
    ds_pp_min_views = fields.Integer(
        string="Hide Views Below", default=0,
        config_parameter='uellow_dropship.pp_min_views',
        help="Only surface the views count once it reaches this number "
             "(avoids showing '3 views' on a brand-new listing).")
    ds_pp_views_boost = fields.Integer(
        string="Views Baseline Boost", default=0,
        config_parameter='uellow_dropship.pp_views_boost',
        help="Optional number added on top of real views for social proof "
             "(0 = show the honest real count only).")
    ds_pp_max_reviews = fields.Integer(
        string="Max Reviews Shown", default=12,
        config_parameter='uellow_dropship.pp_max_reviews')
    ds_pp_max_gallery = fields.Integer(
        string="Max Gallery Images", default=8,
        config_parameter='uellow_dropship.pp_max_gallery')

    # ---- Sync schedules (drive the crons) ---------------------------- #
    ds_import_cron_active = fields.Boolean(
        string="Enable Auto-import Cron", default=False,
        config_parameter='uellow_dropship.import_cron_active')
    ds_schedules_cron_mins = fields.Integer(
        string="Check Schedules Every (min)", default=15,
        config_parameter='uellow_dropship.schedules_cron_mins')
    ds_deal_sync_enabled = fields.Boolean(
        string="Enable Deal Price Sync", default=True,
        config_parameter='uellow_dropship.deal_sync_enabled')
    ds_deal_sync_mins = fields.Integer(
        string="Deal Sync Every (min)", default=30,
        config_parameter='uellow_dropship.deal_sync_mins')
    ds_deal_sync_budget = fields.Integer(
        string="Deal Sync Time Budget (sec)", default=60,
        config_parameter='uellow_dropship.deal_sync_budget')
    ds_category_sync_days = fields.Integer(
        string="Category Sync Every (days)", default=1,
        config_parameter='uellow_dropship.category_sync_days')

    # ---- Auto-promote bestsellers ------------------------------------ #
    ds_autopromote = fields.Boolean(
        string="Auto-promote Bestsellers", default=False,
        config_parameter='uellow_dropship.autopromote',
        help="Turn listings that already sold a lot on the provider into live "
             "Uellow products automatically (before the first on-site order).")
    ds_autopromote_min_orders = fields.Integer(
        string="Auto-promote if Units Sold ≥", default=500,
        config_parameter='uellow_dropship.autopromote_min_orders')
    ds_autopromote_max_per_run = fields.Integer(
        string="Auto-promote Max / Run", default=50,
        config_parameter='uellow_dropship.autopromote_max_per_run')

    # ---- Slow-mover rescue -------------------------------------------- #
    ds_slowmover_min_views = fields.Integer(
        string="Slow-mover Min Views", default=20,
        config_parameter='uellow_dropship.slowmover_min_views',
        help="A materialized product with at least this many views and zero "
             "sales is flagged as a slow mover.")
    ds_slowmover_discount = fields.Float(
        string="Slow-mover Discount %", default=15.0,
        config_parameter='uellow_dropship.slowmover_discount',
        help="Discount applied by the 'Apply slow-mover discount' action.")

    # ---- Shipping / delivery labels ---------------------------------- #
    ds_ships_label_en = fields.Char(
        string="Ships Label (EN)", default="Ships worldwide from China",
        config_parameter='uellow_dropship.ships_label_en',
        help="Honest delivery line shown on World product cards (never "
             "'delivery in hours', which only applies to local Kuwait stock).")
    ds_ships_label_ar = fields.Char(
        string="Ships Label (AR)", default="شحن دولي سريع من الصين",
        config_parameter='uellow_dropship.ships_label_ar')

    # ---- Monthly performance report ---------------------------------- #
    ds_monthly_report_enabled = fields.Boolean(
        string="Email Monthly Report", default=False,
        config_parameter='uellow_dropship.monthly_report_enabled',
        help="Email the branded World performance PDF once a month.")
    ds_monthly_report_emails = fields.Char(
        string="Report Recipients", config_parameter='uellow_dropship.monthly_report_emails',
        help="Comma-separated email addresses that receive the monthly report.")

    ds_enrich_on_import = fields.Boolean(
        string="Fetch Full Detail on Import", default=True,
        config_parameter='uellow_dropship.enrich_on_import',
        help="Pull reviews / specifications / shipping while importing so "
             "listings are complete immediately (bounded by the run time "
             "budget). If off, detail is fetched lazily on first view.")

    # ---- A/B title testing ------------------------------------------- #
    ds_ab_bucket_hours = fields.Integer(
        string="A/B Rotation (hours)", default=12,
        config_parameter='uellow_dropship.ab_bucket_hours',
        help="How often Uellow World flips between title A and title B during a "
             "live A/B test. Both card and product page use the same variant "
             "within each window, so views/orders attribute cleanly.")

    def _apply_cron(self, xmlid, active=None, number=None, unit=None):
        cron = self.env.ref(xmlid, raise_if_not_found=False)
        if not cron:
            return
        vals = {}
        if active is not None:
            vals['active'] = bool(active)
        if number:
            vals['interval_number'] = int(number)
        if unit:
            vals['interval_type'] = unit
        if vals:
            cron.sudo().write(vals)

    def set_values(self):
        res = super().set_values()
        # push the schedule settings onto the actual ir.cron records so the
        # admin's chosen cadence takes effect immediately.
        self._apply_cron('uellow_dropship.cron_dropship_auto_import',
                         active=self.ds_import_cron_active,
                         number=self.ds_import_interval_hours or 1, unit='hours')
        self._apply_cron('uellow_dropship.cron_dropship_run_schedules',
                         number=self.ds_schedules_cron_mins or 15, unit='minutes')
        self._apply_cron('uellow_dropship.cron_dropship_sync_deals',
                         active=self.ds_deal_sync_enabled,
                         number=self.ds_deal_sync_mins or 30, unit='minutes')
        self._apply_cron('uellow_dropship.cron_dropship_sync_categories',
                         number=self.ds_category_sync_days or 1, unit='days')
        self._apply_cron('uellow_dropship.cron_dropship_auto_promote',
                         active=self.ds_autopromote)
        self._apply_cron('uellow_dropship.cron_dropship_monthly_report',
                         active=self.ds_monthly_report_enabled)
        return res

    def action_open_providers(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Dropship Providers',
            'res_model': 'dropship.provider',
            'views': [[False, 'list'], [False, 'form']],
            'view_mode': 'list,form',
        }
