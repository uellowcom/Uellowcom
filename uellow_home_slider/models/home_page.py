# -*- coding: utf-8 -*-
from odoo import models, fields, api

SECTION_TYPES = [
    ('hero_slider',    'سلايدر الهيرو · Hero slider'),
    ('product_row',    'صف منتجات · Products row'),
    ('dept_spotlight', 'واجهة الأقسام · Departments spotlight'),
    ('category_strip', 'شريط الأقسام · Categories strip'),
    ('new_user_bonus', 'مكافأة عضو جديد · New-user bonus'),
    ('banner',         'بانر · Banner (image + link)'),
    ('flash_deals',    'عروض فلاش · Flash deals'),
    ('infinite_products','منتجات لانهائية · Infinite products'),
    ('category_grid',  'شبكة الأقسام · Categories grid'),
    ('feature_bar',    'شريط المزايا · Feature/trust bar'),
    ('custom_html',    'HTML مخصّص · Custom HTML'),
]

PRODUCT_SOURCE = [
    ('newest',      'وصل حديثًا · Newest'),
    ('bestsellers', 'الأكثر مبيعًا · Best sellers'),
    ('discounted',  'عروض · Biggest discounts'),
    ('trending',    'رائج · Trending'),
    ('you_may_like','قد يعجبك · You may like'),
    ('category',    'قسم محدّد · A specific category'),
    ('installments','قابل للتقسيط · Installments-eligible'),
]

STYLE = [('rail', 'شريط أفقي · Rail'), ('grid', 'شبكة · Grid'), ('carousel', 'كاروسيل · Carousel')]


class UellowHomePage(models.Model):
    _name = 'uellow.home.page'
    _description = 'Uellow Home Page (configurable)'
    _order = 'sequence, id'

    name        = fields.Char(string='الاسم', required=True, default='الصفحة الرئيسية')
    sequence    = fields.Integer(default=10)
    active      = fields.Boolean(string='نشط', default=True)
    is_live     = fields.Boolean(string='هي الرئيسية الحالية', default=False,
                                 help='عند التفعيل، يخدم / (staging عبر /home-preview).')

    section_ids = fields.One2many('uellow.home.section', 'page_id', string='أقسام الصفحة')
    section_count = fields.Integer(compute='_compute_section_count', string='عدد الأقسام')

    # SEO
    meta_title_en       = fields.Char(string='SEO Title [EN]')
    meta_title_ar       = fields.Char(string='عنوان SEO [ع]')
    meta_description_en = fields.Char(string='SEO Description [EN]')
    meta_description_ar = fields.Char(string='وصف SEO [ع]')
    og_image            = fields.Binary(string='صورة المشاركة (OG)', attachment=True)
    og_image_url        = fields.Char(string='رابط صورة OG')

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
    _description = 'Uellow Home Page Section'
    _order = 'sequence, id'

    page_id      = fields.Many2one('uellow.home.page', string='الصفحة', required=True, ondelete='cascade')
    sequence     = fields.Integer(string='الترتيب', default=10)
    active       = fields.Boolean(string='نشط', default=True)
    name         = fields.Char(string='اسم القسم (داخلي)', required=True)
    section_type = fields.Selection(SECTION_TYPES, string='نوع القسم', required=True, default='product_row')

    # heading
    show_title   = fields.Boolean(string='إظهار العنوان', default=True)
    title_en     = fields.Char(string='العنوان [EN]')
    title_ar     = fields.Char(string='العنوان [ع]')
    subtitle_en  = fields.Char(string='وصف [EN]')
    subtitle_ar  = fields.Char(string='وصف [ع]')

    # product_row / category_strip
    product_source = fields.Selection(PRODUCT_SOURCE, string='مصدر المنتجات', default='newest')
    category_id    = fields.Many2one('product.public.category', string='القسم')
    product_ids    = fields.Many2many('product.template', string='منتجات مختارة يدويًا')
    limit          = fields.Integer(string='عدد العناصر', default=12)
    columns        = fields.Integer(string='أعمدة (شبكة)', default=2)
    style          = fields.Selection(STYLE, string='الشكل', default='rail')

    # hero slider
    slider_id    = fields.Many2one('uellow.home.slider', string='السلايدر')

    # banner / custom
    image        = fields.Binary(string='صورة', attachment=True)
    image_url    = fields.Char(string='رابط الصورة')
    image_url_ar = fields.Char(string='رابط الصورة (عربي)')
    html_en      = fields.Html(string='HTML [EN]', sanitize=False)
    html_ar      = fields.Html(string='HTML [ع]', sanitize=False)

    # link / cta
    link_url       = fields.Char(string='رابط', default='/shop')
    link_label_en  = fields.Char(string='نص الرابط [EN]', default='View all')
    link_label_ar  = fields.Char(string='نص الرابط [ع]', default='عرض الكل')
    show_link      = fields.Boolean(string='إظهار رابط "الكل"', default=True)

    # styling
    bg_color     = fields.Char(string='لون الخلفية', default='')
    pad_y        = fields.Integer(string='هامش رأسي (px)', default=18)

    # ── new-user bonus panel (new_user_bonus) ──
    panel_icon   = fields.Char(string='أيقونة البانل (إيموجي)', default='🎁')
    panel_btn_en = fields.Char(string='نص الزر [EN]', default='Go')
    panel_btn_ar = fields.Char(string='نص الزر [ع]', default='اذهب')
    panel_link   = fields.Char(string='رابط الزر', default='/web/signup')
    panel_color1 = fields.Char(string='لون البانل 1', default='#FFD24D')
    panel_color2 = fields.Char(string='لون البانل 2', default='#F4A100')
    min_discount = fields.Integer(string='أقل نسبة خصم %', default=0,
                                  help='للمصدر "عروض": يعرض فقط منتجات بخصم ≥ هذه النسبة المئوية.')

    # ── hero layout (hero_slider) ──
    cat_width    = fields.Integer(string='عرض عمود الأقسام (px)', default=250)
    hero_height  = fields.Integer(string='ارتفاع الهيرو (px)', default=620)

    # ── flash deals (flash_deals) ──
    flash_label_en = fields.Char(string='نص العدّاد [EN]', default='Ends in')
    flash_label_ar = fields.Char(string='نص العدّاد [ع]', default='تنتهي خلال')
    flash_color1   = fields.Char(string='لون الفلاش 1', default='#E63946')
    flash_color2   = fields.Char(string='لون الفلاش 2', default='#F26A2E')
    flash_end      = fields.Datetime(string='نهاية العدّاد (اختياري)',
                                     help='وقت انتهاء العرض. اتركه فارغًا للعدّ حتى منتصف الليل يوميًا.')
    flash_daily    = fields.Boolean(string='تصفير يومي للعدّاد', default=True)
    flash_sort     = fields.Selection([
        ('disc_desc', 'الأعلى خصمًا · Biggest discount'),
        ('newest',    'الأحدث · Newest'),
        ('price_asc', 'الأرخص · Cheapest'),
        ('price_desc','الأغلى · Most expensive'),
    ], string='ترتيب المنتجات', default='disc_desc')
    flash_btn_en   = fields.Char(string='زر الفلاش [EN]', default='View all')
    flash_btn_ar   = fields.Char(string='زر الفلاش [ع]', default='عرض الكل')

    # ── cards / badges ──
    show_save_badge     = fields.Boolean(string='إظهار بادچ التوفير', default=True)
    show_discount_badge = fields.Boolean(string='إظهار نسبة الخصم %', default=True)

    def title(self, lang):
        self.ensure_one()
        return (self.title_en if lang == 'en' else self.title_ar) or self.title_en or self.title_ar or ''
