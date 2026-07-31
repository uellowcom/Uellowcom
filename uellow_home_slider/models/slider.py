# -*- coding: utf-8 -*-
from odoo import models, fields, api

# Icon keys must match the SVG set defined in static/src/js/slider.js
ICON_SELECTION = [
    ('phone', 'هاتف · Phone'),
    ('mobile', 'جوّال · Mobile'),
    ('tablet', 'لوحي · Tablet'),
    ('bolt', 'إلكترونيات · Electronics'),
    ('laptop', 'لابتوب · Laptop'),
    ('tv', 'تلفزيون · TV'),
    ('watch', 'ساعة · Watch'),
    ('drop', 'عطر · Fragrance'),
    ('home', 'منزل · Home'),
    ('baby', 'طفل · Baby'),
    ('heart', 'صحة · Health'),
    ('shirt', 'أزياء · Fashion'),
    ('gem', 'مجوهرات · Jewellery'),
    ('camera', 'كاميرا · Camera'),
    ('headphones', 'سماعات · Audio'),
    ('game', 'ألعاب · Gaming'),
    ('car', 'سيارات · Automotive'),
    ('dumbbell', 'رياضة · Sports'),
    ('tools', 'أدوات · Tools'),
    ('shield', 'أمن · Security'),
    ('tag', 'وسم · Tag'),
    ('gift', 'هدية · Gift'),
    ('star', 'نجمة · Star'),
    ('truck', 'شحن · Delivery'),
    ('cash', 'نقد · Cash'),
    ('lock', 'قفل · Secure'),
    ('percent', 'خصم · Discount'),
]


class UellowHomeSlider(models.Model):
    _name = 'uellow.home.slider'
    _description = 'Uellow Home Slider'
    _order = 'sequence, id'

    name            = fields.Char(string='الاسم', required=True, default='السلايدر الرئيسي')
    sequence        = fields.Integer(string='الترتيب', default=10)
    active          = fields.Boolean(string='نشط', default=True)
    show_coupon     = fields.Boolean(string='إظهار الكوبون', default=True)
    coupon_code     = fields.Char(string='كود الكوبون', default='WELCOME05')
    coupon_discount = fields.Char(string='نسبة الخصم', default='5%')
    signup_url      = fields.Char(string='رابط التسجيل', default='/web/signup')
    login_url       = fields.Char(string='رابط الدخول', default='/web/login')
    logo_image      = fields.Binary(string='صورة الشعار', attachment=True)
    logo_url        = fields.Char(string='رابط الشعار', default='/web/image/website/1/logo/Uellow?unique=13b1cfb')

    # ===== v2 desktop controls (Gradient Spotlight + departments menu) =====
    show_menu        = fields.Boolean(string='إظهار منيو الأقسام', default=True)
    menu_title_ar    = fields.Char(string='عنوان المنيو [ع]', default='كل الأقسام')
    menu_title_en    = fields.Char(string='Menu title [EN]', default='All Departments')
    menu_footer_ar   = fields.Char(string='زر أسفل المنيو [ع]', default='كل الأقسام')
    menu_footer_en   = fields.Char(string='Menu footer [EN]', default='All departments')
    menu_footer_url  = fields.Char(string='رابط زر المنيو', default='/shop')
    show_features    = fields.Boolean(string='إظهار المزايا', default=True)
    show_overlay_text = fields.Boolean(string='إظهار نص الشرائح فوق الصورة', default=True)
    show_arrows      = fields.Boolean(string='إظهار الأسهم', default=True)
    show_dots        = fields.Boolean(string='إظهار النقاط', default=True)
    autoplay         = fields.Boolean(string='تشغيل تلقائي', default=True)
    autoplay_speed   = fields.Integer(string='سرعة التشغيل (ثانية)', default=5)
    overlay_opacity  = fields.Integer(string='شدة التعتيم فوق الصورة (%)', default=100)
    cta_label_ar     = fields.Char(string='نص زر الشراء [ع]', default='تسوّق الآن')
    cta_label_en     = fields.Char(string='Shop button [EN]', default='Shop now')

    ar_banner1_image = fields.Binary(string='[عربي] بنر 1 - صورة', attachment=True)
    ar_banner1_url   = fields.Char(string='[عربي] بنر 1 - رابط', default='/ar/shop')
    ar_banner1_alt   = fields.Char(string='[عربي] بنر 1 - نص بديل', default='بنر 1')
    ar_banner2_image = fields.Binary(string='[عربي] بنر 2 - صورة', attachment=True)
    ar_banner2_url   = fields.Char(string='[عربي] بنر 2 - رابط', default='/ar/shop')
    ar_banner2_alt   = fields.Char(string='[عربي] بنر 2 - نص بديل', default='بنر 2')

    en_banner1_image = fields.Binary(string='[EN] Banner 1 - Image', attachment=True)
    en_banner1_url   = fields.Char(string='[EN] Banner 1 - URL', default='/en/shop')
    en_banner1_alt   = fields.Char(string='[EN] Banner 1 - Alt', default='Banner 1')
    en_banner2_image = fields.Binary(string='[EN] Banner 2 - Image', attachment=True)
    en_banner2_url   = fields.Char(string='[EN] Banner 2 - URL', default='/en/shop')
    en_banner2_alt   = fields.Char(string='[EN] Banner 2 - Alt', default='Banner 2')

    slide_ids    = fields.One2many('uellow.home.slide', 'slider_id', string='الشرائح')
    slide_count  = fields.Integer(string='عدد الشرائح', compute='_compute_slide_count')
    menu_ids     = fields.One2many('uellow.home.slider.dept', 'slider_id', string='أقسام المنيو')
    feature_ids  = fields.One2many('uellow.home.slider.feature', 'slider_id', string='المزايا')

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
            'name': 'شرائح: %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'uellow.home.slide',
            'view_mode': 'tree,form',
            'domain': [('slider_id', '=', self.id)],
            'context': {'default_slider_id': self.id},
        }


class UellowHomeSlide(models.Model):
    _name = 'uellow.home.slide'
    _description = 'Uellow Home Slide'
    _order = 'sequence, id'

    slider_id    = fields.Many2one('uellow.home.slider', string='السلايدر', required=True, ondelete='cascade')
    name         = fields.Char(string='الاسم', required=True)
    sequence     = fields.Integer(string='الترتيب', default=10)
    active       = fields.Boolean(string='نشط', default=True)
    image        = fields.Binary(string='الصورة', attachment=True)
    image_url    = fields.Char(string='رابط الصورة')
    alt_text     = fields.Char(string='النص البديل')
    link_url     = fields.Char(string='رابط الضغط', default='/shop')
    open_new_tab = fields.Boolean(string='فتح في تبويب جديد', default=False)
    show_overlay   = fields.Boolean(string='إظهار نص فوق الصورة', default=False)
    overlay_kicker = fields.Char(string='وسم صغير (Kicker)')
    overlay_title  = fields.Char(string='العنوان')
    overlay_sub    = fields.Char(string='العنوان الفرعي')
    overlay_btn    = fields.Char(string='نص الزر')
    overlay_btn_url = fields.Char(string='رابط الزر')
    language = fields.Selection([('ar', 'عربي'), ('en', 'English')], string='اللغة', required=True, default='ar')
    device   = fields.Selection([('desktop', 'ديسك توب'), ('mobile', 'موبايل')], string='الجهاز', required=True, default='desktop')

    def get_src(self):
        self.ensure_one()
        if self.image:
            return '/web/image/uellow.home.slide/%d/image' % self.id
        return self.image_url or ''

    def get_target(self):
        self.ensure_one()
        return '_blank' if self.open_new_tab else '_self'


class UellowHomeSliderDept(models.Model):
    _name = 'uellow.home.slider.dept'
    _description = 'Uellow Slider Department Menu Item'
    _order = 'sequence, id'

    slider_id = fields.Many2one('uellow.home.slider', string='السلايدر', required=True, ondelete='cascade')
    sequence  = fields.Integer(string='الترتيب', default=10)
    active    = fields.Boolean(string='نشط', default=True)
    name_ar   = fields.Char(string='الاسم [ع]', required=True)
    name_en   = fields.Char(string='Name [EN]', required=True)
    icon      = fields.Selection(ICON_SELECTION, string='الأيقونة', default='tag')
    url       = fields.Char(string='الرابط', default='/shop')


class UellowHomeSliderFeature(models.Model):
    _name = 'uellow.home.slider.feature'
    _description = 'Uellow Slider Feature Badge'
    _order = 'sequence, id'

    slider_id = fields.Many2one('uellow.home.slider', string='السلايدر', required=True, ondelete='cascade')
    sequence  = fields.Integer(string='الترتيب', default=10)
    active    = fields.Boolean(string='نشط', default=True)
    name_ar   = fields.Char(string='النص [ع]', required=True)
    name_en   = fields.Char(string='Text [EN]', required=True)
    icon      = fields.Selection(ICON_SELECTION, string='الأيقونة', default='star')
