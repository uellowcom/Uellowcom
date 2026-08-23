# -*- coding: utf-8 -*-
from odoo import models, fields, api

# Icon keys must match the SVG set defined in static/src/js/slider.js
ICON_SELECTION = [
    ('phone', 'Phone'),
    ('mobile', 'Mobile'),
    ('tablet', 'Tablet'),
    ('bolt', 'Electronics'),
    ('laptop', 'Laptop'),
    ('tv', 'TV'),
    ('watch', 'Watch'),
    ('drop', 'Fragrance'),
    ('home', 'Home'),
    ('baby', 'Baby'),
    ('heart', 'Health'),
    ('shirt', 'Fashion'),
    ('gem', 'Jewellery'),
    ('camera', 'Camera'),
    ('headphones', 'Audio'),
    ('game', 'Gaming'),
    ('car', 'Automotive'),
    ('dumbbell', 'Sports'),
    ('tools', 'Tools'),
    ('shield', 'Security'),
    ('tag', 'Tag'),
    ('gift', 'Gift'),
    ('star', 'Star'),
    ('truck', 'Delivery'),
    ('cash', 'Cash'),
    ('lock', 'Secure'),
    ('percent', 'Discount'),
]


class UellowHomeSlider(models.Model):
    _name = 'uellow.home.slider'
    _description = 'Home Slider'
    _order = 'sequence, id'

    name            = fields.Char(string='Name', required=True, default='Main slider')
    sequence        = fields.Integer(string='Order', default=10)
    active          = fields.Boolean(string='Active', default=True)
    show_coupon     = fields.Boolean(string='Show coupon', default=True)
    coupon_code     = fields.Char(string='Coupon code', default='WELCOME05')
    coupon_discount = fields.Char(string='Discount', default='5%')
    signup_url      = fields.Char(string='Sign-up link', default='/web/signup')
    login_url       = fields.Char(string='Login link', default='/web/login')
    logo_image      = fields.Binary(string='Logo image', attachment=True)
    logo_url        = fields.Char(string='Logo URL', default='/web/image/website/1/logo/Uellow?unique=13b1cfb')

    # ===== Desktop controls (spotlight + departments menu) =====
    show_menu        = fields.Boolean(string='Show departments menu', default=True)
    menu_title_ar    = fields.Char(string='Menu title (AR)', default='كل الأقسام')
    menu_title_en    = fields.Char(string='Menu title (EN)', default='All Departments')
    menu_footer_ar   = fields.Char(string='Menu footer button (AR)', default='كل الأقسام')
    menu_footer_en   = fields.Char(string='Menu footer button (EN)', default='All departments')
    menu_footer_url  = fields.Char(string='Menu footer link', default='/shop')
    show_features    = fields.Boolean(string='Show features', default=True)
    show_overlay_text = fields.Boolean(string='Show slide overlay text', default=True)
    show_arrows      = fields.Boolean(string='Show arrows', default=True)
    show_dots        = fields.Boolean(string='Show dots', default=True)
    autoplay         = fields.Boolean(string='Autoplay', default=True)
    autoplay_speed   = fields.Integer(string='Autoplay speed (sec)', default=5)
    overlay_opacity  = fields.Integer(string='Overlay darkness (%)', default=100)
    cta_label_ar     = fields.Char(string='Shop button (AR)', default='تسوّق الآن')
    cta_label_en     = fields.Char(string='Shop button (EN)', default='Shop now')

    ar_banner1_image = fields.Binary(string='[AR] Banner 1 - Image', attachment=True)
    ar_banner1_url   = fields.Char(string='[AR] Banner 1 - URL', default='/ar/shop')
    ar_banner1_alt   = fields.Char(string='[AR] Banner 1 - Alt', default='بنر 1')
    ar_banner2_image = fields.Binary(string='[AR] Banner 2 - Image', attachment=True)
    ar_banner2_url   = fields.Char(string='[AR] Banner 2 - URL', default='/ar/shop')
    ar_banner2_alt   = fields.Char(string='[AR] Banner 2 - Alt', default='بنر 2')

    en_banner1_image = fields.Binary(string='[EN] Banner 1 - Image', attachment=True)
    en_banner1_url   = fields.Char(string='[EN] Banner 1 - URL', default='/en/shop')
    en_banner1_alt   = fields.Char(string='[EN] Banner 1 - Alt', default='Banner 1')
    en_banner2_image = fields.Binary(string='[EN] Banner 2 - Image', attachment=True)
    en_banner2_url   = fields.Char(string='[EN] Banner 2 - URL', default='/en/shop')
    en_banner2_alt   = fields.Char(string='[EN] Banner 2 - Alt', default='Banner 2')

    slide_ids    = fields.One2many('uellow.home.slide', 'slider_id', string='Slides')
    slide_count  = fields.Integer(string='Slides', compute='_compute_slide_count')
    menu_ids     = fields.One2many('uellow.home.slider.dept', 'slider_id', string='Menu departments')
    feature_ids  = fields.One2many('uellow.home.slider.feature', 'slider_id', string='Features')

    @api.depends('slide_ids')
    def _compute_slide_count(self):
        for rec in self:
            rec.slide_count = len(rec.slide_ids.filtered('active'))

    @api.model
    def get_active(self):
        return self.search([('active', '=', True)], limit=1)

    def action_view_slides(self):
        self.ensure_one()
        return {
            'name': 'Slides: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'uellow.home.slide',
            'view_mode': 'tree,form',
            'domain': [('slider_id', '=', self.id)],
            'context': {'default_slider_id': self.id},
        }


class UellowHomeSlide(models.Model):
    _name = 'uellow.home.slide'
    _description = 'Home Slide'
    _order = 'sequence, id'

    slider_id    = fields.Many2one('uellow.home.slider', string='Slider', required=True, ondelete='cascade')
    name         = fields.Char(string='Name', required=True)
    sequence     = fields.Integer(string='Order', default=10)
    active       = fields.Boolean(string='Active', default=True)
    image        = fields.Binary(string='Image', attachment=True)
    image_url    = fields.Char(string='Image URL')
    alt_text     = fields.Char(string='Alt text')
    link_url     = fields.Char(string='Click link', default='/shop')
    open_new_tab = fields.Boolean(string='Open in new tab', default=False)
    show_overlay   = fields.Boolean(string='Show overlay text', default=False)
    overlay_kicker = fields.Char(string='Kicker')
    overlay_title  = fields.Char(string='Title')
    overlay_sub    = fields.Char(string='Subtitle')
    overlay_btn    = fields.Char(string='Button label')
    overlay_btn_url = fields.Char(string='Button link')
    # ── per-slide coupon + features (override the slider defaults) ──
    sl_coupon_mode = fields.Selection([
        ('inherit', '⤴ Same as slider'), ('custom', 'Custom for this slide'), ('hide', 'Hide')],
        string='Slide coupon', default='inherit')
    sl_coupon_code = fields.Char(string='Slide coupon code')
    sl_coupon_disc = fields.Char(string='Slide discount')
    sl_feats_mode  = fields.Selection([
        ('inherit', '⤴ Same as slider'), ('hide', 'Hide on this slide')],
        string='Slide features', default='inherit')
    language = fields.Selection([('ar', 'Arabic'), ('en', 'English')], string='Language', required=True, default='ar')
    device   = fields.Selection([('desktop', 'Desktop'), ('mobile', 'Mobile')], string='Device', required=True, default='desktop')

    def get_src(self):
        self.ensure_one()
        if self.image:
            # ?unique busts the browser/Cloudflare edge cache whenever the
            # banner is re-uploaded (write_date changes) — otherwise a stale
            # image (or placeholder) can be served from the CDN indefinitely.
            _u = int(self.write_date.timestamp()) if self.write_date else 0
            return '/web/image/uellow.home.slide/%d/image?unique=%s' % (self.id, _u)
        return self.image_url or ''

    def get_target(self):
        self.ensure_one()
        return '_blank' if self.open_new_tab else '_self'


class UellowHomeSliderDept(models.Model):
    _name = 'uellow.home.slider.dept'
    _description = 'Slider Department Menu Item'
    _order = 'sequence, id'

    slider_id = fields.Many2one('uellow.home.slider', string='Slider', required=True, ondelete='cascade')
    sequence  = fields.Integer(string='Order', default=10)
    active    = fields.Boolean(string='Active', default=True)
    name_ar   = fields.Char(string='Name (AR)', required=True)
    name_en   = fields.Char(string='Name (EN)', required=True)
    icon      = fields.Selection(ICON_SELECTION, string='Icon', default='tag')
    url       = fields.Char(string='Link', default='/shop')


class UellowHomeSliderFeature(models.Model):
    _name = 'uellow.home.slider.feature'
    _description = 'Slider Feature Badge'
    _order = 'sequence, id'

    slider_id = fields.Many2one('uellow.home.slider', string='Slider', required=True, ondelete='cascade')
    sequence  = fields.Integer(string='Order', default=10)
    active    = fields.Boolean(string='Active', default=True)
    name_ar   = fields.Char(string='Text (AR)', required=True)
    name_en   = fields.Char(string='Text (EN)', required=True)
    icon      = fields.Selection(ICON_SELECTION, string='Icon', default='star')
