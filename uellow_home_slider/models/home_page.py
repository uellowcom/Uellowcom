# -*- coding: utf-8 -*-
from odoo import models, fields, api

# Block types, ordered by how often they are used. The two "legacy" ones are
# kept only for backward-compatibility with pages that still reference them.
SECTION_TYPES = [
    ('hero_slider',      'Hero slider'),
    ('product_row',      'Products row'),
    ('flash_deals',      'Flash deals'),
    ('new_user_bonus',   'New-user bonus'),
    ('category_grid',    'Categories grid'),
    ('feature_bar',      'Feature / trust bar'),
    ('banner',           'Banner (image + link)'),
    ('infinite_products', 'Infinite products feed'),
    ('custom_html',      'Custom HTML'),
    ('dept_spotlight',   'Departments spotlight (legacy)'),
    ('category_strip',   'Categories strip (legacy)'),
]

# How a products block picks what to show.
PRODUCT_SOURCE = [
    ('newest',       'Newest arrivals'),
    ('bestsellers',  'Best sellers'),
    ('discounted',   'Biggest discounts'),
    ('trending',     'Trending'),
    ('you_may_like', 'You may like'),
    ('category',     'A specific category'),
    ('installments', 'Installments-eligible'),
    ('manual',       'Hand-picked products'),
]

STYLE = [
    ('rail',     'Horizontal rail'),
    ('grid',     'Grid'),
    ('carousel', 'Carousel'),
]

FLASH_SORT = [
    ('disc_desc',  'Biggest discount first'),
    ('newest',     'Newest first'),
    ('price_asc',  'Cheapest first'),
    ('price_desc', 'Most expensive first'),
]


class UellowHomePage(models.Model):
    _name = 'uellow.home.page'
    _description = 'Home Page Layout'
    _order = 'sequence, id'

    name          = fields.Char(string='Layout name', required=True, default='Home page',
                                help='Internal name for this home-page layout.')
    sequence      = fields.Integer(default=10)
    active        = fields.Boolean(string='Active', default=True)
    is_live       = fields.Boolean(string='Live home page', default=False,
                                   help='When on, this layout is the one served on the storefront home page.')
    section_ids   = fields.One2many('uellow.home.section', 'page_id', string='Blocks')
    section_count = fields.Integer(compute='_compute_section_count', string='Blocks')

    # ── SEO (rendered into <head> of the home page) ──
    meta_title_en       = fields.Char(string='SEO title (EN)')
    meta_title_ar       = fields.Char(string='SEO title (AR)')
    meta_description_en = fields.Char(string='SEO description (EN)')
    meta_description_ar = fields.Char(string='SEO description (AR)')
    og_image            = fields.Binary(string='Share image (OG)', attachment=True,
                                        help='Image used when the home page is shared on social media.')
    og_image_url        = fields.Char(string='Share image URL')

    @api.depends('section_ids', 'section_ids.active')
    def _compute_section_count(self):
        for rec in self:
            rec.section_count = len(rec.section_ids.filtered('active'))

    @api.model
    def get_live(self):
        return self.search([('active', '=', True), ('is_live', '=', True)], limit=1) \
            or self.search([('active', '=', True)], limit=1)

    def action_open_preview(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': '/home-preview', 'target': 'new'}


class UellowHomeSection(models.Model):
    _name = 'uellow.home.section'
    _description = 'Home Page Block'
    _order = 'sequence, id'

    page_id      = fields.Many2one('uellow.home.page', string='Home page', required=True, ondelete='cascade')
    sequence     = fields.Integer(string='Order', default=10)
    active       = fields.Boolean(string='Active', default=True)
    name         = fields.Char(string='Block name', required=True,
                               help='Internal label shown in this list only.')
    section_type = fields.Selection(SECTION_TYPES, string='Block type', required=True, default='product_row')

    # ── Heading (bilingual) ──
    show_title   = fields.Boolean(string='Show heading', default=True)
    title_en     = fields.Char(string='Title (EN)')
    title_ar     = fields.Char(string='Title (AR)')
    subtitle_en  = fields.Char(string='Subtitle (EN)')
    subtitle_ar  = fields.Char(string='Subtitle (AR)')

    # ── Products (product_row / flash_deals / new_user_bonus / category_strip) ──
    product_source = fields.Selection(PRODUCT_SOURCE, string='Products from', default='newest',
                                      help='How this block chooses which products to show.')
    category_id    = fields.Many2one('product.public.category', string='Category',
                                     help='Used when "Products from" is set to "A specific category".')
    product_ids    = fields.Many2many('product.template', string='Hand-picked products',
                                      help='Used when "Products from" is set to "Hand-picked products".')
    min_discount   = fields.Integer(string='Min. discount %', default=0,
                                    help='With source "Biggest discounts": only show items discounted by at least this %.')
    limit          = fields.Integer(string='How many', default=12)
    columns        = fields.Integer(string='Columns (grid)', default=2)
    style          = fields.Selection(STYLE, string='Layout', default='rail')
    show_save_badge     = fields.Boolean(string='Show "you save" badge', default=True)
    show_discount_badge = fields.Boolean(string='Show discount % badge', default=True)

    # ── Hero slider ──
    slider_id    = fields.Many2one('uellow.home.slider', string='Slider')
    cat_width    = fields.Integer(string='Categories column width (px)', default=250)
    hero_height  = fields.Integer(string='Hero height (px)', default=620)

    # ── New-user bonus panel ──
    panel_icon   = fields.Char(string='Panel emoji', default='🎁')
    panel_btn_en = fields.Char(string='Button label (EN)', default='Go')
    panel_btn_ar = fields.Char(string='Button label (AR)', default='اذهب')
    panel_link   = fields.Char(string='Button link', default='/web/signup')
    panel_color1 = fields.Char(string='Panel colour 1', default='#FFD24D')
    panel_color2 = fields.Char(string='Panel colour 2', default='#F4A100')

    # ── Flash deals ──
    flash_label_en = fields.Char(string='Countdown label (EN)', default='Ends in')
    flash_label_ar = fields.Char(string='Countdown label (AR)', default='تنتهي خلال')
    flash_color1   = fields.Char(string='Flash colour 1', default='#E63946')
    flash_color2   = fields.Char(string='Flash colour 2', default='#F26A2E')
    flash_end      = fields.Datetime(string='Ends at (optional)',
                                     help='Deal end time. Leave empty to count down to midnight every day.')
    flash_daily    = fields.Boolean(string='Reset daily', default=True)
    flash_sort     = fields.Selection(FLASH_SORT, string='Sort products', default='disc_desc')
    flash_btn_en   = fields.Char(string='Flash button (EN)', default='View all')
    flash_btn_ar   = fields.Char(string='Flash button (AR)', default='عرض الكل')

    # ── Banner / Custom HTML ──
    image        = fields.Binary(string='Image', attachment=True)
    image_url    = fields.Char(string='Image URL')
    image_url_ar = fields.Char(string='Image URL (Arabic)')
    html_en      = fields.Html(string='HTML (EN)', sanitize=False)
    html_ar      = fields.Html(string='HTML (AR)', sanitize=False)

    # ── "View all" link ──
    link_url       = fields.Char(string='Link', default='/shop')
    link_label_en  = fields.Char(string='Link label (EN)', default='View all')
    link_label_ar  = fields.Char(string='Link label (AR)', default='عرض الكل')
    show_link      = fields.Boolean(string='Show "view all" link', default=True)

    # ── Styling ──
    bg_color     = fields.Char(string='Background colour', default='')
    pad_y        = fields.Integer(string='Vertical padding (px)', default=18)

    def title(self, lang):
        self.ensure_one()
        return (self.title_en if lang == 'en' else self.title_ar) or self.title_en or self.title_ar or ''
