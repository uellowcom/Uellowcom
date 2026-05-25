# -*- coding: utf-8 -*-
from odoo import models, fields, api


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

    slide_ids   = fields.One2many('uellow.home.slide', 'slider_id', string='الشرائح')
    slide_count = fields.Integer(string='عدد الشرائح', compute='_compute_slide_count')

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
