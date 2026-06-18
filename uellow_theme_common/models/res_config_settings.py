# -*- coding: utf-8 -*-
# Copyright (c) 2019-Present Droggol Infotech Private Limited. (<https://www.droggol.com/>)

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dr_pwa_activated = fields.Boolean(related='website_id.dr_pwa_activated', readonly=False)
    dr_pwa_name = fields.Char(related='website_id.dr_pwa_name', readonly=False)
    dr_pwa_short_name = fields.Char(related='website_id.dr_pwa_short_name', readonly=False)
    dr_pwa_background_color = fields.Char(related='website_id.dr_pwa_background_color', readonly=False)
    dr_pwa_theme_color = fields.Char(related='website_id.dr_pwa_theme_color', readonly=False)
    dr_pwa_icon_192 = fields.Binary(related='website_id.dr_pwa_icon_192', readonly=False)
    dr_pwa_icon_512 = fields.Binary(related='website_id.dr_pwa_icon_512', readonly=False)
    dr_pwa_start_url = fields.Char(related='website_id.dr_pwa_start_url', readonly=False)
    dr_pwa_screenshots = fields.One2many(related='website_id.dr_pwa_screenshots', readonly=False)
    dr_pwa_shortcuts = fields.One2many(related='website_id.dr_pwa_shortcuts', readonly=False)
    dr_pwa_show_install_banner = fields.Boolean(related='website_id.dr_pwa_show_install_banner', readonly=False)
    dr_pwa_offline_page = fields.Boolean(related='website_id.dr_pwa_offline_page', readonly=False)

    # ─── Uellow Theme — branding, header, search ───────────────────────
    # All related-to-website so editors can manage them per-storefront from
    # the standard Website Settings page without touching theme source code.
    uc_logo_height = fields.Integer(related='website_id.uc_logo_height', readonly=False)
    uc_logo_mobile = fields.Binary(related='website_id.uc_logo_mobile', readonly=False)
    uc_favicon = fields.Binary(related='website_id.uc_favicon', readonly=False)
    uc_header_bg = fields.Char(related='website_id.uc_header_bg', readonly=False)
    uc_header_yellow = fields.Char(related='website_id.uc_header_yellow', readonly=False)
    uc_preheader_text = fields.Char(related='website_id.uc_preheader_text', readonly=False)
    uc_preheader_phone = fields.Char(related='website_id.uc_preheader_phone', readonly=False)
    uc_search_placeholder = fields.Char(related='website_id.uc_search_placeholder', readonly=False)
    uc_trending_terms = fields.Char(related='website_id.uc_trending_terms', readonly=False)

    # Today's Deals promo
    uc_deals_active       = fields.Boolean(related='website_id.uc_deals_active', readonly=False)
    uc_deals_label        = fields.Char(related='website_id.uc_deals_label', readonly=False)
    uc_deals_icon         = fields.Char(related='website_id.uc_deals_icon', readonly=False)
    uc_deals_target_type  = fields.Selection(related='website_id.uc_deals_target_type', readonly=False)
    uc_deals_category_id  = fields.Many2one(related='website_id.uc_deals_category_id', readonly=False)
    uc_deals_tag_id       = fields.Many2one(related='website_id.uc_deals_tag_id', readonly=False)
    uc_deals_page_id      = fields.Many2one(related='website_id.uc_deals_page_id', readonly=False)
    uc_deals_url          = fields.Char(related='website_id.uc_deals_url', readonly=False)
    uc_deals_query        = fields.Char(related='website_id.uc_deals_query', readonly=False)

    # Footer
    uc_app_ios_url     = fields.Char(related='website_id.uc_app_ios_url', readonly=False)
    uc_app_android_url = fields.Char(related='website_id.uc_app_android_url', readonly=False)
    uc_app_huawei_url  = fields.Char(related='website_id.uc_app_huawei_url', readonly=False)
    uc_app_popup_enabled = fields.Boolean(related='website_id.uc_app_popup_enabled', readonly=False)
    uc_app_popup_delay   = fields.Integer(related='website_id.uc_app_popup_delay', readonly=False)
    uc_app_popup_title   = fields.Char(related='website_id.uc_app_popup_title', readonly=False)
    uc_app_popup_text    = fields.Char(related='website_id.uc_app_popup_text', readonly=False)
    uc_app_banner_enabled = fields.Boolean(related='website_id.uc_app_banner_enabled', readonly=False)
    uc_app_banner_devices = fields.Selection(related='website_id.uc_app_banner_devices', readonly=False)
    uc_app_banner_frequency = fields.Selection(related='website_id.uc_app_banner_frequency', readonly=False)
    uc_app_banner_dismiss_days = fields.Integer(related='website_id.uc_app_banner_dismiss_days', readonly=False)
    uc_app_banner_ios_smart = fields.Boolean(related='website_id.uc_app_banner_ios_smart', readonly=False)
    uc_footer_about    = fields.Text(related='website_id.uc_footer_about', readonly=False)
    uc_footer_credit   = fields.Char(related='website_id.uc_footer_credit', readonly=False)
    uc_footer_newsletter_intro = fields.Char(related='website_id.uc_footer_newsletter_intro', readonly=False)
    uc_beena_icon              = fields.Binary(related='website_id.uc_beena_icon', readonly=False)
    uc_policy_privacy_url       = fields.Char(related='website_id.uc_policy_privacy_url', readonly=False)
    uc_policy_terms_url         = fields.Char(related='website_id.uc_policy_terms_url', readonly=False)
    uc_policy_cookies_url       = fields.Char(related='website_id.uc_policy_cookies_url', readonly=False)
    uc_policy_accessibility_url = fields.Char(related='website_id.uc_policy_accessibility_url', readonly=False)

    # This has been done in order to fix Odoo's broken behavior for theme customization.
    # If database already have theme installed, it is impossible to have custom module later.
    dr_has_custom_module = fields.Boolean(compute='_compute_dr_has_custom_module')

    @api.depends('website_id')
    def _compute_dr_has_custom_module(self):
        IrModuleModule = self.env['ir.module.module']
        themes = self._get_droggol_theme_list()
        for setting in self:
            setting.dr_has_custom_module = False
            if setting.website_id and setting.website_id.theme_id and setting.website_id.theme_id.name in themes:
                search_term = '%s_%%' % setting.website_id.theme_id.name
                has_custom_apps = IrModuleModule.sudo().search([('name', '=ilike', search_term)])
                setting.dr_has_custom_module = bool(has_custom_apps)

    def dr_open_pwa_screenshots(self):
        self.website_id._force()
        action = self.env.ref('uellow_theme_common.dr_pwa_screenshots_action').read()[0]
        action['domain'] = [('website_id', '=', self.website_id.id)]
        action['context'] = {'default_website_id': self.website_id.id}
        return action

    def dr_open_pwa_shortcuts(self):
        self.website_id._force()
        action = self.env.ref('uellow_theme_common.dr_pwa_shortcuts_action').read()[0]
        action['domain'] = [('website_id', '=', self.website_id.id)]
        action['context'] = {'default_website_id': self.website_id.id}
        return action

    def dr_open_theme_custom_modules(self):
        self.ensure_one()
        themes = self._get_droggol_theme_list()
        if self.website_id and self.website_id.theme_id and self.website_id.theme_id.name in themes:
            search_term = '%s_%%' % self.website_id.theme_id.name
            return {
                'name': _('Theme Customizations'),
                'view_mode': 'kanban,list,form',
                'res_model': 'ir.module.module',
                'type': 'ir.actions.act_window',
                'domain': [('name', '=ilike', search_term)]
            }
        return True

    def _get_droggol_theme_list(self):
        return ['uellow_theme']
