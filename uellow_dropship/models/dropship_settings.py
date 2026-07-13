# -*- coding: utf-8 -*-
"""In-module settings page.

A single persistent record whose fields read/write ir.config_parameter, so the
admin edits every Uellow World setting on a normal form INSIDE the module
(breadcrumb stays in Uellow World) instead of being thrown to Odoo's global
Settings app. One generic compute + inverse binds every field to its param.
"""
from odoo import api, fields, models


class DropshipSettings(models.Model):
    _name = 'dropship.settings'
    _description = 'Uellow World Settings'

    name = fields.Char(default='Uellow World Settings')

    # field_name -> (config param key, type, default)
    _PARAMS = {
        # General
        'ds_enabled': ('uellow_dropship.enabled', 'bool', False),
        'ds_brand_name': ('uellow_dropship.brand_name', 'char', 'Uellow World'),
        'ds_prepaid_only': ('uellow_dropship.prepaid_only', 'bool', True),
        'ds_auto_publish': ('uellow_dropship.auto_publish', 'bool', False),
        # Pricing
        'ds_default_markup': ('uellow_dropship.default_markup', 'float', 0.0),
        'ds_fx_buffer': ('uellow_dropship.fx_buffer', 'float', 3.0),
        'ds_customs_percent': ('uellow_dropship.customs_percent', 'float', 0.0),
        'ds_min_margin': ('uellow_dropship.min_margin', 'float', 10.0),
        'ds_min_price': ('uellow_dropship.min_price', 'float', 0.0),
        'ds_max_price': ('uellow_dropship.max_price', 'float', 0.0),
        # Deals & flash guard
        'ds_show_deals': ('uellow_dropship.show_deals', 'bool', True),
        'ds_deal_min_percent': ('uellow_dropship.deal_min_percent', 'float', 15.0),
        'ds_exclude_flash_deals': ('uellow_dropship.exclude_flash_deals', 'bool', True),
        'ds_max_discount_percent': ('uellow_dropship.max_discount_percent', 'float', 0.0),
        'ds_block_restricted': ('uellow_dropship.block_restricted', 'bool', True),
        'ds_block_terms': ('uellow_dropship.block_terms', 'char', ''),
        # Import behaviour
        'ds_import_min_orders': ('uellow_dropship.import_min_orders', 'int', 0),
        'ds_import_min_rating': ('uellow_dropship.import_min_rating', 'float', 0.0),
        'ds_import_max_products': ('uellow_dropship.import_max_products', 'int', 500),
        'ds_enrich_on_import': ('uellow_dropship.enrich_on_import', 'bool', True),
        'ds_require_shippable': ('uellow_dropship.require_shippable', 'bool', True),
        'ds_import_max_scan': ('uellow_dropship.import_max_scan', 'int', 4000),
        'ds_filter_by_ship_country': ('uellow_dropship.filter_by_ship_country', 'bool', False),
        'ds_max_ship_checks': ('uellow_dropship.max_ship_checks', 'int', 20),
        # Product page display
        'ds_pp_show_specs': ('uellow_dropship.pp_show_specs', 'bool', True),
        'ds_pp_show_reviews': ('uellow_dropship.pp_show_reviews', 'bool', True),
        'ds_pp_show_shipping': ('uellow_dropship.pp_show_shipping', 'bool', True),
        'ds_pp_show_views': ('uellow_dropship.pp_show_views', 'bool', True),
        'ds_pp_show_sold': ('uellow_dropship.pp_show_sold', 'bool', True),
        # Shipping (Uellow World international carrier)
        'ds_free_shipping': ('uellow_dropship.free_shipping', 'bool', True),
        'ds_shipping_price': ('uellow_dropship.shipping_price', 'float', 0.0),
        'ds_free_ship_threshold': ('uellow_dropship.free_ship_threshold', 'float', 0.0),
        # Orders / fulfilment
        'ds_auto_place_order': ('uellow_dropship.auto_place_order', 'bool', False),
        'ds_default_zip': ('uellow_dropship.default_zip', 'char', '00000'),
        'ds_daily_order_cap': ('uellow_dropship.daily_order_cap', 'int', 0),
        # Sync schedules
        'ds_deal_sync_enabled': ('uellow_dropship.deal_sync_enabled', 'bool', False),
        'ds_deal_sync_mins': ('uellow_dropship.deal_sync_mins', 'int', 30),
        'ds_autopromote': ('uellow_dropship.autopromote', 'bool', False),
        # Slow-mover rescue
        'ds_slowmover_min_views': ('uellow_dropship.slowmover_min_views', 'int', 20),
        'ds_slowmover_discount': ('uellow_dropship.slowmover_discount', 'float', 15.0),
        'ds_auto_reprice': ('uellow_dropship.auto_reprice', 'bool', False),
        # Chrome extension
        'ds_ext_api_key': ('uellow_dropship.ext_api_key', 'char', ''),
        'ds_ext_max_per_call': ('uellow_dropship.ext_max_per_call', 'int', 60),
        # Monthly report
        'ds_monthly_report_enabled': ('uellow_dropship.monthly_report_enabled', 'bool', False),
        'ds_monthly_report_emails': ('uellow_dropship.monthly_report_emails', 'char', ''),
    }

    ds_enabled = fields.Boolean("Enable Dropshipping", compute='_compute_params', inverse='_inverse_params')
    ds_brand_name = fields.Char("Storefront Brand", compute='_compute_params', inverse='_inverse_params')
    ds_prepaid_only = fields.Boolean("Prepaid Only (no COD)", compute='_compute_params', inverse='_inverse_params')
    ds_auto_publish = fields.Boolean("Auto-publish on Materialize", compute='_compute_params', inverse='_inverse_params')
    ds_default_markup = fields.Float("Default Markup %", compute='_compute_params', inverse='_inverse_params')
    ds_fx_buffer = fields.Float("FX Buffer %", compute='_compute_params', inverse='_inverse_params')
    ds_customs_percent = fields.Float("Customs / Duty %", compute='_compute_params', inverse='_inverse_params')
    ds_min_margin = fields.Float("Min Margin %", compute='_compute_params', inverse='_inverse_params')
    ds_min_price = fields.Float("Min Landed Price (KWD)", compute='_compute_params', inverse='_inverse_params')
    ds_max_price = fields.Float("Max Landed Price (KWD)", compute='_compute_params', inverse='_inverse_params')
    ds_show_deals = fields.Boolean("Show Deals / Offers", compute='_compute_params', inverse='_inverse_params')
    ds_deal_min_percent = fields.Float("Min Discount % for Deals", compute='_compute_params', inverse='_inverse_params')
    ds_exclude_flash_deals = fields.Boolean("Skip Flash / Limited-time Deals", compute='_compute_params', inverse='_inverse_params')
    ds_max_discount_percent = fields.Float("Max Discount % on Import", compute='_compute_params', inverse='_inverse_params')
    ds_block_restricted = fields.Boolean("Block Prohibited Products", compute='_compute_params', inverse='_inverse_params')
    ds_block_terms = fields.Char("Prohibited Terms (comma-separated)", compute='_compute_params', inverse='_inverse_params')
    ds_import_min_orders = fields.Integer("Min Units Sold", compute='_compute_params', inverse='_inverse_params')
    ds_import_min_rating = fields.Float("Min Rating", compute='_compute_params', inverse='_inverse_params')
    ds_import_max_products = fields.Integer("Max Products / Run", compute='_compute_params', inverse='_inverse_params')
    ds_enrich_on_import = fields.Boolean("Fetch Full Detail on Import", compute='_compute_params', inverse='_inverse_params')
    ds_require_shippable = fields.Boolean("Only Products That Ship to Us", compute='_compute_params', inverse='_inverse_params')
    ds_import_max_scan = fields.Integer("Max Items Scanned / Run", compute='_compute_params', inverse='_inverse_params')
    ds_filter_by_ship_country = fields.Boolean("Show Products Only Where They Ship", compute='_compute_params', inverse='_inverse_params')
    ds_max_ship_checks = fields.Integer("Max Countries Checked / Product", compute='_compute_params', inverse='_inverse_params')
    ds_target_country_ids = fields.Many2many(
        'res.country', 'dropship_settings_target_country_rel', 'settings_id', 'country_id',
        string="Target Countries",
        compute='_compute_target_countries', inverse='_inverse_target_countries',
        help="Countries the store targets. 'Check shipping coverage' verifies "
             "each product against these. Select/deselect any; all by default.")

    def _compute_target_countries(self):
        Country = self.env['res.country'].sudo()
        codes = [c.strip().upper() for c in
                 (self.env['ir.config_parameter'].sudo().get_param(
                     'uellow_dropship.target_countries') or '').split(',') if c.strip()]
        countries = Country.search([('code', 'in', codes)]) if codes else Country.browse()
        for rec in self:
            rec.ds_target_country_ids = countries

    def _inverse_target_countries(self):
        for rec in self:
            codes = ','.join(sorted(c.code for c in rec.ds_target_country_ids if c.code))
            self.env['ir.config_parameter'].sudo().set_param(
                'uellow_dropship.target_countries', codes)
    # ── Shipping (Uellow World international carrier) ──────────────────────
    ds_free_shipping = fields.Boolean(
        "Free International Shipping", compute='_compute_params',
        inverse='_inverse_params',
        help="When on, Uellow World orders always ship free. Turn off to "
             "charge the flat fee below.")
    ds_shipping_price = fields.Float(
        "Flat Shipping Fee (KWD)", compute='_compute_params',
        inverse='_inverse_params',
        help="Charged per order when free shipping is off.")
    ds_free_ship_threshold = fields.Float(
        "Free Shipping Over (KWD)", compute='_compute_params',
        inverse='_inverse_params',
        help="Orders at/above this subtotal ship free even when a flat fee is "
             "set. 0 = disabled.")
    # ── Home tab-navigation categories ────────────────────────────────────
    ds_tabnav_category_ids = fields.Many2many(
        'dropship.category', 'dropship_settings_tabnav_rel',
        'settings_id', 'category_id', string="Home Tab Categories",
        compute='_compute_tabnav_categories', inverse='_inverse_tabnav_categories',
        help="Categories shown as the top tabs on the Uellow World home. "
             "Leave empty to auto-pick the top categories by product count.")

    def _compute_tabnav_categories(self):
        Cat = self.env['dropship.category'].sudo()
        raw = (self.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.tabnav_category_ids') or '')
        ids = [int(x) for x in raw.split(',') if x.strip().isdigit()]
        cats = Cat.browse(ids).exists() if ids else Cat.browse()
        for rec in self:
            rec.ds_tabnav_category_ids = cats

    def _inverse_tabnav_categories(self):
        for rec in self:
            ids = ','.join(str(c.id) for c in rec.ds_tabnav_category_ids)
            self.env['ir.config_parameter'].sudo().set_param(
                'uellow_dropship.tabnav_category_ids', ids)

    ds_pp_show_specs = fields.Boolean("Show Specifications", compute='_compute_params', inverse='_inverse_params')
    ds_pp_show_reviews = fields.Boolean("Show Reviews", compute='_compute_params', inverse='_inverse_params')
    ds_pp_show_shipping = fields.Boolean("Show Shipping Info", compute='_compute_params', inverse='_inverse_params')
    ds_pp_show_views = fields.Boolean("Show Views Count", compute='_compute_params', inverse='_inverse_params')
    ds_pp_show_sold = fields.Boolean("Show Sold Count", compute='_compute_params', inverse='_inverse_params')
    ds_auto_place_order = fields.Boolean("Auto-place Provider Order on Payment", compute='_compute_params', inverse='_inverse_params')
    ds_default_zip = fields.Char("Default Zip / Postal Code", compute='_compute_params', inverse='_inverse_params')
    ds_daily_order_cap = fields.Integer("Max Provider Orders / Day", compute='_compute_params', inverse='_inverse_params')
    ds_deal_sync_enabled = fields.Boolean("Enable Deal Price Sync", compute='_compute_params', inverse='_inverse_params')
    ds_deal_sync_mins = fields.Integer("Deal Sync Every (min)", compute='_compute_params', inverse='_inverse_params')
    ds_autopromote = fields.Boolean("Auto-promote Bestsellers", compute='_compute_params', inverse='_inverse_params')
    ds_slowmover_min_views = fields.Integer("Slow-mover Min Views", compute='_compute_params', inverse='_inverse_params')
    ds_slowmover_discount = fields.Float("Slow-mover Discount %", compute='_compute_params', inverse='_inverse_params')
    ds_auto_reprice = fields.Boolean("Auto-reprice to Protect Margin", compute='_compute_params', inverse='_inverse_params')
    ds_ext_api_key = fields.Char("Chrome Extension API Key", compute='_compute_params', inverse='_inverse_params')
    ds_ext_max_per_call = fields.Integer("Extension Max Products / Import", compute='_compute_params', inverse='_inverse_params')
    ds_monthly_report_enabled = fields.Boolean("Email Monthly Report", compute='_compute_params', inverse='_inverse_params')
    ds_monthly_report_emails = fields.Char("Report Recipients", compute='_compute_params', inverse='_inverse_params')

    @staticmethod
    def _cast(raw, typ, dflt):
        # get_param returns Python False (not None/'') when a param is UNSET —
        # treat that as "use the default". A param intentionally set to false is
        # the STRING 'False', which is handled below.
        if raw is None or raw is False or raw == '':
            return dflt
        try:
            if typ == 'bool':
                return raw in ('True', '1', 'true', True)
            if typ == 'int':
                return int(float(raw))
            if typ == 'float':
                return float(raw)
            return raw
        except (TypeError, ValueError):
            return dflt

    @staticmethod
    def _ser(val, typ):
        if typ == 'bool':
            return 'True' if val else 'False'
        return str(val if val is not None else '')

    def _compute_params(self):
        ICP = self.env['ir.config_parameter'].sudo()
        for rec in self:
            for f, (key, typ, dflt) in self._PARAMS.items():
                rec[f] = self._cast(ICP.get_param(key), typ, dflt)

    def _inverse_params(self):
        ICP = self.env['ir.config_parameter'].sudo()
        for rec in self:
            for f, (key, typ, dflt) in self._PARAMS.items():
                ICP.set_param(key, self._ser(rec[f], typ))
        # push schedule cadence onto the crons (mirror res.config.settings)
        self.env['res.config.settings']._apply_cron(
            'uellow_dropship.cron_dropship_sync_deals',
            active=self.ds_deal_sync_enabled,
            number=self.ds_deal_sync_mins or 30, unit='minutes')
        self.env['res.config.settings']._apply_cron(
            'uellow_dropship.cron_dropship_auto_promote',
            active=self.ds_autopromote)

    def action_generate_ext_key(self):
        import uuid
        self.ds_ext_api_key = uuid.uuid4().hex
        return True

    def action_open_providers(self):
        return {
            'type': 'ir.actions.act_window', 'name': 'Providers',
            'res_model': 'dropship.provider',
            'views': [[False, 'list'], [False, 'form']],
            'view_mode': 'list,form', 'target': 'current',
        }
