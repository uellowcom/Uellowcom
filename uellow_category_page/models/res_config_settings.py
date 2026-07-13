# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ucp_enabled            = fields.Boolean(related='website_id.ucp_enabled', readonly=False)
    ucp_hero_enabled       = fields.Boolean(related='website_id.ucp_hero_enabled', readonly=False)
    ucp_hero_image         = fields.Binary(related='website_id.ucp_hero_image', readonly=False)
    ucp_breadcrumb_enabled = fields.Boolean(related='website_id.ucp_breadcrumb_enabled', readonly=False)
    ucp_ai_enabled         = fields.Boolean(related='website_id.ucp_ai_enabled', readonly=False)
    ucp_ai_placeholder     = fields.Char(related='website_id.ucp_ai_placeholder', readonly=False)
    ucp_badges_enabled     = fields.Boolean(related='website_id.ucp_badges_enabled', readonly=False)
    ucp_presets_enabled    = fields.Boolean(related='website_id.ucp_presets_enabled', readonly=False)
    ucp_unlock_enabled     = fields.Boolean(related='website_id.ucp_unlock_enabled', readonly=False)
    ucp_freeship_threshold = fields.Float(related='website_id.ucp_freeship_threshold', readonly=False)
    ucp_ticker_enabled     = fields.Boolean(related='website_id.ucp_ticker_enabled', readonly=False)
    ucp_ticker_text        = fields.Char(related='website_id.ucp_ticker_text', readonly=False)
    ucp_flash_enabled      = fields.Boolean(related='website_id.ucp_flash_enabled', readonly=False)
    ucp_card_restyle       = fields.Boolean(related='website_id.ucp_card_restyle', readonly=False)
    ucp_card_badges        = fields.Boolean(related='website_id.ucp_card_badges', readonly=False)
