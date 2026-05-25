from odoo import models, fields, api


class SEOConfig(models.Model):
    _name = 'uellow.seo.config'
    _description = 'SEO Automation Config'

    name = fields.Char(default='SEO Settings')
    active = fields.Boolean(default=True)
    anthropic_api_key = fields.Char('Anthropic API Key')
    site_name_en = fields.Char('Site Name (EN)', default='Uellow')
    site_name_ar = fields.Char('Site Name (AR)', default='يلو')
    default_suffix_en = fields.Char('Title Suffix (EN)', default='| Uellow Kuwait')
    default_suffix_ar = fields.Char('Title Suffix (AR)', default='| يلو الكويت')
    auto_generate_new = fields.Boolean('Auto-generate for New Products', default=True)
    overwrite_existing = fields.Boolean('Overwrite Existing SEO', default=False)
    include_price = fields.Boolean('Include Price in Title', default=False)
    include_brand = fields.Boolean('Include Brand', default=True)
    schema_markup = fields.Boolean('Add Schema Markup', default=True)

    @api.model
    def get_config(self):
        cfg = self.search([], limit=1)
        if not cfg:
            cfg = self.create({})
        return cfg
