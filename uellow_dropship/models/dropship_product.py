# -*- coding: utf-8 -*-
"""dropship.product — lightweight source catalog ("display don't store").

Millions of provider listings can live here cheaply (indexed, few columns, JSON
blob for the rest). A real ``product.template`` is created ONLY when an order is
placed (:meth:`_materialize`), idempotent by (provider_id, source_id). This is
what keeps the DB from bloating with listings that never sell.
"""
import json
import logging
import re

from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# English -> Arabic map for the provider category names (the store is EN-primary
# + AR: breadcrumbs and shop category chips must read Arabic in Arabic mode).
# Bounded (~80 provider categories) unlike the per-product titles. Used both to
# translate the eCommerce public category (ar_001) at materialize time and to
# label the storefront category chips.
CATEGORY_AR = {
    'Fashion Jewelry': 'مجوهرات عصرية',
    'Electrical Equipment & Supplies': 'معدات ولوازم كهربائية',
    'Fine Jewelry': 'مجوهرات فاخرة',
    'Eyewear & Accessories': 'نظارات وإكسسوارات',
    'Jewelry Making': 'صناعة المجوهرات',
    'Fishing': 'صيد الأسماك',
    'Cycling': 'دراجات هوائية',
    'New Headwear': 'إكسسوارات الرأس',
    'Arts,Crafts & Sewing': 'فنون وحِرف وخياطة',
    'Makeup': 'مكياج',
    'Home Decor': 'ديكور المنزل',
    'Garden Tools': 'أدوات الحدائق',
    'Hardware': 'أدوات ومعدّات',
    'Games & Accessories': 'ألعاب وإكسسوارات',
    'Nail Art & Tools': 'فنون وأدوات الأظافر',
    'Drill Bits, Saw Blades & Cutting Tools': 'لقم ثقب وشفرات ومناشير',
    'Kitchen,Dining & Bar': 'مطبخ ومائدة',
    'Dental Supplies': 'مستلزمات طب الأسنان',
    'Family Intelligence System': 'أنظمة ذكية للمنزل',
    'Office Electronics': 'إلكترونيات مكتبية',
    'Motorcycle Parts': 'قطع الدراجات النارية',
    'Car Electronics': 'إلكترونيات السيارات',
    'Synthetic Hair(For White)': 'شعر صناعي',
    'Plumbing': 'سباكة',
    'Accessories & Parts': 'إكسسوارات وقطع',
    'Watches Accessories': 'إكسسوارات الساعات',
    'Interior Accessories': 'إكسسوارات داخلية للسيارة',
    'Personal Care Appliances': 'أجهزة العناية الشخصية',
    'Games and Puzzles': 'ألعاب وألغاز',
    'Tablet Accessories & Parts': 'إكسسوارات وقطع التابلت',
    'Camera & Photo': 'كاميرات وتصوير',
    '3D Printing & Additive Manufacturing': 'الطباعة ثلاثية الأبعاد',
    'Pens, Pencils & Writing Supplies': 'أقلام ولوازم الكتابة',
    'Garden Supplies': 'مستلزمات الحدائق',
    'Tool Sets': 'أطقم أدوات',
    'Measurement & Analysis Instruments': 'أجهزة القياس والتحليل',
    "Men's Watches": 'ساعات رجالية',
    'Storage Device': 'أجهزة التخزين',
    'Car Lock System': 'أنظمة أقفال السيارات',
    'Doors, Gates & Windows': 'أبواب وبوابات ونوافذ',
    'Portable Audio & Video': 'صوت وفيديو محمول',
    'Active Components': 'مكوّنات إلكترونية فعّالة',
    'Household Merchandises': 'مستلزمات منزلية',
    'new Scarf &Wrap': 'أوشحة ولفّات',
    'Engines & Engine Parts': 'محرّكات وقطعها',
    'Action & Toy Figures': 'مجسّمات ودمى',
    'Lighting Accessories': 'إكسسوارات الإضاءة',
    'Interior Parts': 'قطع داخلية للسيارة',
    'Arts & Crafts, DIY toys': 'فنون وحِرف وألعاب يدوية',
    'Entertainment': 'ترفيه',
    'Exterior Parts': 'قطع خارجية للسيارة',
    'Hunting': 'صيد',
    'Tapes, Adhesives & Fasteners': 'أشرطة ولواصق ومثبّتات',
    'Fitness & Body Building': 'لياقة وكمال أجسام',
    'Baby Clothing': 'ملابس الأطفال الرضّع',
    'Skin Care': 'العناية بالبشرة',
    'Shoe Accessories': 'إكسسوارات الأحذية',
    'Educational Equipment & Supplies': 'مستلزمات تعليمية',
    'Emergency Safety Supplies': 'مستلزمات السلامة والطوارئ',
    'Festive & Party Supplies': 'مستلزمات الحفلات والأعياد',
    'Computer Components': 'مكوّنات الكمبيوتر',
    'Health Care': 'الرعاية الصحية',
    'Shaving & Hair Removal': 'الحلاقة وإزالة الشعر',
    'Lighting Bulbs & Tubes': 'لمبات وأنابيب إضاءة',
    'Computer Peripherals': 'ملحقات الكمبيوتر',
    'Hand Tools': 'أدوات يدوية',
    'Other Vehicle Parts & Accessories': 'قطع وإكسسوارات مركبات أخرى',
    'Modification&Protection': 'تعديل وحماية',
    'Car Lights': 'إضاءة السيارات',
    'Welding Equipment & Supplies': 'معدّات ولوازم اللحام',
    'Stuffed Animals & Plush': 'دمى محشوّة',
    "Children's Clothing": 'ملابس الأطفال',
    'Home Storage & Organization': 'تخزين وتنظيم المنزل',
    'Pet Products': 'مستلزمات الحيوانات الأليفة',
    'Art Supplies': 'لوازم فنية',
    'Skirts': 'تنانير',
    'Wear Parts': 'قطع الاستبدال',
    'Home Audio & Video': 'صوت وفيديو منزلي',
    'Jewelry Tools & Equipments': 'أدوات صناعة المجوهرات',
    'Gloves & Mittens': 'قفازات',
    'Bathroom Fixture': 'تجهيزات الحمّام',
    # readable parent/top categories
    'Jewelry & Accessories': 'مجوهرات وإكسسوارات',
    'Home Improvement': 'تحسين المنزل',
    'Home Appliances': 'الأجهزة المنزلية',
    'Apparel Accessories': 'إكسسوارات الملابس',
    'Automobiles, Parts & Accessories': 'السيارات وقطعها',
    'Beauty & Health': 'الجمال والصحة',
    'Computer & Office': 'الكمبيوتر والمكتب',
    'Consumer Electronics': 'الإلكترونيات',
    'Electronic Components & Supplies': 'مكوّنات ولوازم إلكترونية',
    'Hair Extensions & Wigs': 'وصلات الشعر والباروكات',
    'Home & Garden': 'المنزل والحديقة',
    'Lights & Lighting': 'الإضاءة',
    'Mother & Kids': 'الأمومة والأطفال',
    'Motorcycle Equipments & Parts': 'معدّات وقطع الدراجات النارية',
    'Office & School Supplies': 'لوازم مكتبية ومدرسية',
    'Security & Protection': 'الأمن والحماية',
    'Shoes': 'أحذية',
    'Sports & Entertainment': 'الرياضة والترفيه',
    'Tools': 'أدوات',
    'Toys & Hobbies': 'الألعاب والهوايات',
    'Watches': 'الساعات',
    "Women's Clothing": 'ملابس نسائية',
}

# Per-category icon (emoji) shown on the Uellow World category tiles. Falls back
# to a generic tag icon for any unmapped category.
CATEGORY_ICON = {
    'Fashion Jewelry': '💍',
    'Electrical Equipment & Supplies': '🔌',
    'Fine Jewelry': '💎',
    'Eyewear & Accessories': '👓',
    'Jewelry Making': '🪡',
    'Fishing': '🎣',
    'Cycling': '🚲',
    'New Headwear': '🎀',
    'Arts,Crafts & Sewing': '🎨',
    'Makeup': '💄',
    'Home Decor': '🏠',
    'Garden Tools': '🌿',
    'Hardware': '🔧',
    'Games & Accessories': '🎮',
    'Nail Art & Tools': '💅',
    'Drill Bits, Saw Blades & Cutting Tools': '🪛',
    'Kitchen,Dining & Bar': '🍴',
    'Dental Supplies': '🦷',
    'Family Intelligence System': '🏡',
    'Office Electronics': '🖨️',
    'Motorcycle Parts': '🏍️',
    'Car Electronics': '🚗',
    'Synthetic Hair(For White)': '💇',
    'Plumbing': '🚿',
    'Accessories & Parts': '🔩',
    'Watches Accessories': '⌚',
    'Interior Accessories': '🚙',
    'Personal Care Appliances': '🧴',
    'Games and Puzzles': '🧩',
    'Tablet Accessories & Parts': '📱',
    'Camera & Photo': '📷',
    '3D Printing & Additive Manufacturing': '🖨️',
    'Pens, Pencils & Writing Supplies': '✏️',
    'Garden Supplies': '🌱',
    'Tool Sets': '🧰',
    'Measurement & Analysis Instruments': '📏',
    "Men's Watches": '⌚',
    'Storage Device': '💾',
    'Car Lock System': '🔐',
    'Doors, Gates & Windows': '🚪',
    'Portable Audio & Video': '🎧',
    'Active Components': '🔋',
    'Household Merchandises': '🧹',
    'new Scarf &Wrap': '🧣',
    'Engines & Engine Parts': '⚙️',
    'Action & Toy Figures': '🧸',
    'Lighting Accessories': '💡',
    'Interior Parts': '🚙',
    'Arts & Crafts, DIY toys': '🎨',
    'Entertainment': '🎭',
    'Exterior Parts': '🚗',
    'Hunting': '🏹',
    'Tapes, Adhesives & Fasteners': '📎',
    'Fitness & Body Building': '🏋️',
    'Baby Clothing': '👶',
    'Skin Care': '🧴',
    'Shoe Accessories': '👟',
    'Educational Equipment & Supplies': '🎓',
    'Emergency Safety Supplies': '🚨',
    'Festive & Party Supplies': '🎉',
    'Computer Components': '🖥️',
    'Health Care': '🩺',
    'Shaving & Hair Removal': '🪒',
    'Lighting Bulbs & Tubes': '💡',
    'Computer Peripherals': '🖱️',
    'Hand Tools': '🔨',
    'Other Vehicle Parts & Accessories': '🚐',
    'Modification&Protection': '🛡️',
    'Car Lights': '🔦',
    'Welding Equipment & Supplies': '🔥',
    'Stuffed Animals & Plush': '🧸',
    "Children's Clothing": '👕',
    'Home Storage & Organization': '📦',
    'Pet Products': '🐾',
    'Art Supplies': '🖌️',
    'Skirts': '👗',
    'Wear Parts': '🔧',
    'Home Audio & Video': '📺',
    'Jewelry Tools & Equipments': '🛠️',
    'Gloves & Mittens': '🧤',
    'Bathroom Fixture': '🛁',
    # parents
    'Jewelry & Accessories': '💍',
    'Home Improvement': '🛠️',
    'Home Appliances': '🏠',
    'Apparel Accessories': '🧢',
    'Automobiles, Parts & Accessories': '🚗',
    'Beauty & Health': '💄',
    'Computer & Office': '💻',
    'Consumer Electronics': '📱',
    'Electronic Components & Supplies': '🔋',
    'Hair Extensions & Wigs': '💇',
    'Home & Garden': '🏡',
    'Lights & Lighting': '💡',
    'Mother & Kids': '👶',
    'Motorcycle Equipments & Parts': '🏍️',
    'Office & School Supplies': '✏️',
    'Security & Protection': '🛡️',
    'Shoes': '👟',
    'Sports & Entertainment': '⚽',
    'Tools': '🔧',
    'Toys & Hobbies': '🧸',
    'Watches': '⌚',
    "Women's Clothing": '👗',
}


class DropshipProduct(models.Model):
    _name = 'dropship.product'
    _description = 'Dropship Source Product'
    _order = 'id desc'
    _rec_name = 'title_en'

    provider_id = fields.Many2one('dropship.provider', required=True, ondelete='cascade', index=True)
    source_id = fields.Char(required=True, index=True, help="Provider's product id.")

    title_en = fields.Char(string="Title (EN)")
    title_ar = fields.Char(string="Title (AR)")
    description_html = fields.Html(string="Description")
    description_ar = fields.Html(string="Description (AR)")

    base_cost = fields.Float(string="Base Cost", help="Provider cost in provider currency.")
    currency_code = fields.Char(default="USD")
    landed_price = fields.Float(help="Cost + shipping + customs, in KWD (computed at listing time).")
    sale_price = fields.Float(help="Landed price + markup, shown to the customer.")

    image_url = fields.Char()
    image_urls = fields.Text(help="JSON list of gallery image URLs.")
    main_image_index = fields.Integer(
        string="Main Image #", default=0,
        help="Which gallery image (see the numbers in the Gallery tab) is the "
             "main product image. 0 = the AliExpress default. Click "
             "“Set as Main” to apply.")
    video_url = fields.Char(help="Provider product video (mp4/hls), shown in the gallery.")
    category = fields.Char(index=True, help="Provider category code.")
    category_name = fields.Char(help="Readable category name (never a raw code).")
    category_parent = fields.Char(help="Readable parent/top category name.")
    category_id = fields.Many2one(
        'dropship.category', string="Category (picker)", index=True,
        help="Pick the category from the imported AliExpress category tree "
             "instead of typing it. Fills the code / name / parent below.")

    @api.onchange('category_id')
    def _onchange_category_id(self):
        """Selecting a category fills the readable code/name/parent used by the
        storefront, dashboard grouping and search."""
        for rec in self:
            c = rec.category_id
            if not c:
                continue
            rec.category = c.ext_id or c.code or rec.category
            rec.category_name = c.name or rec.category_name
            rec.category_parent = (c.parent_id.name if c.parent_id
                                   else rec.category_parent)
    source_url = fields.Char(string="Source Link", compute='_compute_source_url',
                             help="Original product page on the provider (e.g. AliExpress).")

    # deals / discount
    original_price = fields.Float(help="Provider list price before discount (for a strike-through).")
    discount_percent = fields.Float(help="Computed deal % vs original_price.")
    is_deal = fields.Boolean(index=True, help="Eligible for the deals/offers rail.")
    variants_json = fields.Text(help="JSON list of unified variant dicts.")
    raw_json = fields.Text(help="Untouched provider payload for audit.")

    # --- full-detail enrichment (fetched lazily at open/materialize) ------- #
    # The feed only carries a thumbnail-level payload (title, image, price,
    # rating %, orders). The rich product page content — full description,
    # specifications, shipping options and the review/seller-rating summary —
    # only comes from the provider's product-detail call, so we fetch it once
    # (freshness-guarded) and cache it here to render on the Uellow product page.
    specs_json = fields.Text(help="JSON list of {name, value} specification rows.")
    reviews_json = fields.Text(help="JSON {reviews:[...], stats:{...}} of individual customer reviews.")
    shipping_json = fields.Text(help="JSON list of shipping options (service, cost, ETA).")
    store_json = fields.Text(help="JSON of the source store/seller + service ratings.")
    rating = fields.Float(help="Average product rating out of 5 (from the provider).")
    review_count = fields.Integer(help="Number of provider reviews/evaluations.")
    orders_text = fields.Char(help="Units sold on the provider, e.g. '700+'.")
    stock_qty = fields.Integer(
        string="Provider Stock", default=0, copy=False,
        help="Total available stock across the provider's variants (refreshed "
             "on price/detail sync).")
    in_stock = fields.Boolean(
        string="In Stock", compute='_compute_in_stock', store=True,
        help="False when the provider has 0 stock — such a product is auto-"
             "unpublished if 'Unpublish When Out of Stock' is on.")
    oos_unpublished = fields.Boolean(
        string="Auto-unpublished (OOS)", copy=False,
        help="Marks a product we unpublished because it went out of stock, so "
             "we can auto-republish it when the provider restocks.")

    @api.depends('stock_qty')
    def _compute_in_stock(self):
        for rec in self:
            rec.in_stock = (rec.stock_qty or 0) > 0

    def _apply_stock(self, qty):
        """Store the provider stock and auto-unpublish/republish per setting."""
        self.ensure_one()
        # Clamp to a sane ceiling: some providers report absurd stock counts
        # that exceed PostgreSQL's int4 range and raise NumericValueOutOfRange
        # on write. Anything above this just means "plenty in stock".
        try:
            qty = int(qty or 0)
        except (TypeError, ValueError):
            qty = 0
        self.stock_qty = max(0, min(qty, 999999))
        if self.env['ir.config_parameter'].sudo().get_param(
                'uellow_dropship.unpublish_oos', 'True') not in ('True', '1', 'true'):
            return
        tmpl = self.product_tmpl_id
        if not tmpl:
            return
        if self.stock_qty <= 0 and tmpl.is_published:
            tmpl.sudo().is_published = False
            self.oos_unpublished = True
        elif self.stock_qty > 0 and self.oos_unpublished and not tmpl.is_published:
            tmpl.sudo().is_published = True
            self.oos_unpublished = False

    @staticmethod
    def _stock_from_unified(unified):
        try:
            variants = unified.get('variants') or []
            if variants:
                return sum(int(v.get('stock') or 0) for v in variants)
        except Exception:  # noqa: BLE001
            pass
        return int(unified.get('stock') or 0)

    ship_country_ids = fields.Many2many(
        'res.country', 'dropship_product_ship_country_rel',
        'product_id', 'country_id', string="Ships to Countries", copy=False,
        help="Countries the provider actually ships this product to (checked on "
             "import). The storefront shows it only to customers in these "
             "countries when country filtering is on. Editable manually.")
    shippable = fields.Boolean(
        string="Ships to us", default=True, copy=False,
        help="False when the provider reports no delivery to the target country "
             "(e.g. AliExpress DELIVERY_NOT_AVAILABLE). Such products shouldn't "
             "be published — a customer could order something we can't fulfil.")

    # ── price intelligence ────────────────────────────────────────────────
    margin_pct = fields.Float(
        string="Margin %", compute='_compute_margin', store=True,
        help="(sale price − landed cost) / sale price. Provider cost changes "
             "shrink this — watch it in Price Intelligence.")
    cost_alert = fields.Boolean(
        string="Margin at risk", default=False, copy=False,
        help="Set when the margin fell below the Min Margin setting (usually "
             "after the provider raised the cost).")
    suggested_price = fields.Float(
        string="Suggested Price", compute='_compute_margin',
        help="Sale price that would restore the Min Margin target.")
    last_cost_change = fields.Datetime(readonly=True, copy=False)
    price_history_ids = fields.One2many(
        'dropship.price.history', 'product_id', string="Price History")

    @api.depends('sale_price', 'landed_price', 'base_cost')
    def _compute_margin(self):
        min_margin = float(self.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.min_margin', 10.0) or 10.0)
        for rec in self:
            cost = rec.landed_price or rec.base_cost or 0.0
            sale = rec.sale_price or 0.0
            rec.margin_pct = round((sale - cost) * 100.0 / sale, 1) if sale else 0.0
            # price to restore the target margin: cost / (1 - m/100)
            denom = 1 - (min_margin / 100.0)
            rec.suggested_price = round(cost / denom, 3) if denom > 0 and cost else sale

    def action_reprice_to_margin(self):
        """Raise the sale price to the suggested (target-margin) price and push
        it to the live product. Clears the margin alert."""
        for rec in self:
            if rec.suggested_price and rec.suggested_price > (rec.sale_price or 0):
                rec.sale_price = rec.suggested_price
                if rec.product_tmpl_id:
                    rec.product_tmpl_id.sudo().list_price = rec.suggested_price
            rec.cost_alert = False
        return True

    def action_check_ship_coverage(self):
        """Deliberately verify which target countries the provider ships each
        selected product to, and store them in ship_country_ids. Capped per
        product to protect the provider API."""
        ICP = self.env['ir.config_parameter'].sudo()
        targets = [c.strip().upper() for c in
                   (ICP.get_param('uellow_dropship.target_countries', 'KW') or 'KW').split(',')
                   if c.strip()]
        cap = int(ICP.get_param('uellow_dropship.max_ship_checks', 20) or 20)
        targets = targets[:cap]
        Country = self.env['res.country'].sudo()
        for rec in self:
            prov = rec.provider_id
            if not prov or prov.code == 'manual':
                continue
            adapter = prov._adapter()
            codes = []
            for cc in targets:
                try:
                    if adapter.get_freight(rec.source_id, cc, 1):
                        codes.append(cc)
                except Exception:  # noqa: BLE001
                    pass
            countries = Country.search([('code', 'in', codes)]) if codes else Country.browse()
            rec.ship_country_ids = [(6, 0, countries.ids)]
            rec.shippable = bool(codes)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': 'Coverage checked',
                       'message': 'Shipping coverage updated for %d product(s).' % len(self),
                       'type': 'success', 'sticky': False},
        }

    def _log_price_change(self, old_cost, new_cost, note=''):
        """Record a provider-cost move + re-evaluate the margin alert."""
        self.ensure_one()
        if not old_cost and not new_cost:
            return
        change = round((new_cost - old_cost) * 100.0 / old_cost, 1) if old_cost else 0.0
        min_margin = float(self.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.min_margin', 10.0) or 10.0)
        cost = self.landed_price or new_cost or 0.0
        sale = self.sale_price or 0.0
        margin = round((sale - cost) * 100.0 / sale, 1) if sale else 0.0
        self.env['dropship.price.history'].sudo().create({
            'product_id': self.id,
            'old_cost': old_cost, 'new_cost': new_cost, 'change_pct': change,
            'sale_price': sale, 'margin_pct': margin,
            'currency_code': self.currency_code or 'USD', 'note': note,
        })
        self.last_cost_change = fields.Datetime.now()
        self.cost_alert = bool(sale and margin < min_margin)
        # optional auto-reprice to protect the margin
        if self.cost_alert and self.env['ir.config_parameter'].sudo().get_param(
                'uellow_dropship.auto_reprice') in ('True', '1', 'true'):
            self.action_reprice_to_margin()
    detail_synced = fields.Datetime(readonly=True,
                                    help="Last time the full detail was fetched.")
    price_synced = fields.Datetime(readonly=True,
                                   help="Last time the live provider price/stock "
                                        "was re-synced. Drives the sync crons' "
                                        "oldest-first ordering so every product is "
                                        "refreshed in turn without repetition.")

    state = fields.Selection([
        ('listed', 'Listed'),
        ('promoted', 'Promoted'),      # manually turned into a real Uellow product early
        ('materialized', 'Materialized'),  # a product.template exists (order placed)
    ], default='listed', index=True,
        help="Listed = source-only candidate, no real product, NOT on the "
             "storefront (costs nothing to keep). Promoted = you manually turned "
             "it into a live, published product early. Materialized = a real "
             "product was created (usually at order time). Promoted & "
             "Materialized both have a live product; only Listed does not.")
    product_tmpl_id = fields.Many2one('product.template', string="Materialized Product", readonly=True)
    published = fields.Boolean(
        string="Published (live in app)", compute='_compute_published',
        help="Whether the live product is published on Uellow World and visible "
             "in the app / storefront. Toggle with the Publish / Unpublish buttons.")

    @api.depends('product_tmpl_id', 'product_tmpl_id.is_published')
    def _compute_published(self):
        for rec in self:
            rec.published = bool(rec.product_tmpl_id and rec.product_tmpl_id.is_published)
    ai_rewritten = fields.Boolean(readonly=True)

    # ── engagement counters (real on-site, not provider) ──────────────────
    view_count = fields.Integer(
        string="Views", default=0, readonly=True, copy=False,
        help="Real number of times this product's page was opened on Uellow "
             "World (app + storefront). Incremented live on each detail view.")
    uellow_sold_count = fields.Integer(
        string="Sold (Uellow)", compute='_compute_uellow_sold', store=False,
        help="Units actually sold on Uellow for the materialized product "
             "(confirmed sale order lines). Separate from the provider's "
             "'units sold' text.")

    # ── A/B title test (time-sliced, no session state) ───────────────────
    ab_active = fields.Boolean(
        string="A/B Title Test", default=False, copy=False,
        help="When on, Uellow World alternates between the two titles below by "
             "time bucket and records which title converts better.")
    title_en_b = fields.Char(string="Title B (EN)", copy=False)
    title_ar_b = fields.Char(string="Title B (AR)", copy=False)
    ab_views_a = fields.Integer(string="A · Views", default=0, readonly=True, copy=False)
    ab_views_b = fields.Integer(string="B · Views", default=0, readonly=True, copy=False)
    ab_orders_a = fields.Integer(string="A · Orders", default=0, readonly=True, copy=False)
    ab_orders_b = fields.Integer(string="B · Orders", default=0, readonly=True, copy=False)
    ab_started = fields.Datetime(string="A/B Started", readonly=True, copy=False)
    ab_winner = fields.Char(string="A/B Result", compute='_compute_ab_winner')

    # ── backend rich previews (what the app / storefront shows) ───────────
    gallery_preview = fields.Html(
        string="Gallery", compute='_compute_previews', sanitize=False)
    specs_preview = fields.Html(
        string="Specifications", compute='_compute_previews', sanitize=False)
    reviews_preview = fields.Html(
        string="Reviews", compute='_compute_previews', sanitize=False)
    variants_preview = fields.Html(
        string="Variants", compute='_compute_previews', sanitize=False)
    shipping_preview = fields.Html(
        string="Shipping", compute='_compute_previews', sanitize=False)
    store_preview = fields.Html(
        string="Seller", compute='_compute_previews', sanitize=False)

    _sql_constraints = [
        ('provider_source_uniq', 'unique(provider_id, source_id)',
         'This source product already exists for this provider.'),
    ]

    # ------------------------------------------------------------------ #
    # engagement counters
    # ------------------------------------------------------------------ #
    def _register_view(self):
        """Atomically bump the real on-site view counter (best-effort).

        Called from the app product-detail serializer and the storefront
        product page. Uses a direct UPDATE so concurrent views never lock
        each other and a page render never fails on a counter write.
        Also credits the currently-serving A/B variant when a test is live.
        """
        for rec in self:
            if not rec.id:
                continue
            try:
                self.env.cr.execute(
                    "UPDATE dropship_product SET view_count "
                    "= COALESCE(view_count, 0) + 1 WHERE id = %s", (rec.id,))
                if rec.ab_active and rec.title_en_b:
                    col = ('ab_views_b' if rec._current_ab_variant() == 'b'
                           else 'ab_views_a')
                    self.env.cr.execute(
                        "UPDATE dropship_product SET %s = COALESCE(%s,0)+1 "
                        "WHERE id = %%s" % (col, col), (rec.id,))
            except Exception:  # noqa: BLE001 - a counter must never break a page
                pass

    # ------------------------------------------------------------------ #
    # A/B title test — the served title is a pure function of time, so any
    # view/order in a bucket provably saw that bucket's title (no sessions).
    # ------------------------------------------------------------------ #
    def _ab_bucket_hours(self):
        try:
            return max(1, int(self.env['ir.config_parameter'].sudo().get_param(
                'uellow_dropship.ab_bucket_hours', 12) or 12))
        except Exception:  # noqa: BLE001
            return 12

    def _current_ab_variant(self):
        """'a' or 'b' — flips every bucket, globally deterministic by clock."""
        secs = self._ab_bucket_hours() * 3600
        now = fields.Datetime.now()
        epoch = int(now.timestamp()) if hasattr(now, 'timestamp') else 0
        return 'b' if (epoch // secs) % 2 else 'a'

    def _ab_title(self, lang_ar=False):
        """The title to show right now, honouring a live A/B test."""
        self.ensure_one()
        a = self.title_ar if lang_ar else self.title_en
        if self.ab_active and self.title_en_b and self._current_ab_variant() == 'b':
            b = self.title_ar_b if lang_ar else self.title_en_b
            return b or a
        return a

    def record_ab_order(self):
        """Credit an order to whichever title is serving now (best-effort)."""
        for rec in self:
            if not (rec.id and rec.ab_active and rec.title_en_b):
                continue
            col = ('ab_orders_b' if rec._current_ab_variant() == 'b'
                   else 'ab_orders_a')
            try:
                self.env.cr.execute(
                    "UPDATE dropship_product SET %s = COALESCE(%s,0)+1 "
                    "WHERE id = %%s" % (col, col), (rec.id,))
            except Exception:  # noqa: BLE001
                pass

    @api.depends('ab_views_a', 'ab_views_b', 'ab_orders_a', 'ab_orders_b', 'ab_active')
    def _compute_ab_winner(self):
        for rec in self:
            va, vb = rec.ab_views_a or 0, rec.ab_views_b or 0
            oa, ob = rec.ab_orders_a or 0, rec.ab_orders_b or 0
            if not rec.ab_active and not (va or vb):
                rec.ab_winner = ''
                continue
            if va < 20 and vb < 20:
                rec.ab_winner = 'Gathering data (need ~20+ views/side)'
                continue
            ca = (oa * 100.0 / va) if va else 0.0
            cb = (ob * 100.0 / vb) if vb else 0.0
            if abs(ca - cb) < 0.01:
                rec.ab_winner = 'Tie · A %.1f%% vs B %.1f%%' % (ca, cb)
            elif ca > cb:
                rec.ab_winner = 'A winning · %.1f%% vs %.1f%%' % (ca, cb)
            else:
                rec.ab_winner = 'B winning · %.1f%% vs %.1f%%' % (cb, ca)

    def action_ab_generate(self):
        """AI-generate a punchier alternate title (EN+AR) and start the test."""
        Rule = self.env['dropship.text.rule']
        for rec in self:
            prompt = (
                "Give ONE alternative, punchier e-commerce product title for A/B "
                "testing in a Kuwaiti store. Keep the brand/model, stay honest (no "
                "fake claims), max ~70 chars. Return JSON {\"title_en\":\"...\","
                "\"title_ar\":\"...\"}.\n\nCurrent title: %s"
            ) % (rec.title_en or '')
            try:
                raw = rec._call_ai(prompt)
                data = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except Exception as e:  # noqa: BLE001
                raise UserError(_("AI title generation failed: %s") % e)
            ten = Rule._apply_all(data.get('title_en')) or ''
            tar = Rule._apply_all(data.get('title_ar')) or ''
            if not ten:
                raise UserError(_("AI returned no alternative title."))
            rec.write({
                'title_en_b': ten, 'title_ar_b': tar,
                'ab_active': True, 'ab_started': fields.Datetime.now(),
                'ab_views_a': 0, 'ab_views_b': 0,
                'ab_orders_a': 0, 'ab_orders_b': 0,
            })
        return True

    def action_ab_stop(self):
        self.write({'ab_active': False})
        return True

    def action_ab_promote_winner(self):
        """Adopt the better-converting title as the permanent title, end test."""
        for rec in self:
            va, vb = rec.ab_views_a or 0, rec.ab_views_b or 0
            ca = (rec.ab_orders_a or 0) * 100.0 / va if va else 0.0
            cb = (rec.ab_orders_b or 0) * 100.0 / vb if vb else 0.0
            if cb > ca and rec.title_en_b:
                rec.title_en = rec.title_en_b
                if rec.title_ar_b:
                    rec.title_ar = rec.title_ar_b
                if rec.product_tmpl_id:
                    rec.product_tmpl_id.sudo().name = rec.title_en_b
            rec.ab_active = False
        return True

    def _compute_uellow_sold(self):
        SOL = self.env['sale.order.line'].sudo()
        for rec in self:
            n = 0
            tmpl = rec.product_tmpl_id
            if tmpl:
                try:
                    lines = SOL.search([
                        ('product_id', 'in', tmpl.product_variant_ids.ids),
                        ('state', 'in', ('sale', 'done')),
                    ])
                    n = int(sum(lines.mapped('product_uom_qty')) or 0)
                except Exception:  # noqa: BLE001
                    n = 0
            rec.uellow_sold_count = n

    def sold_display(self):
        """Best 'units sold' number for cards/pages: real Uellow sales if any,
        otherwise the provider's units-sold figure (parsed from orders_text)."""
        self.ensure_one()
        real = self.uellow_sold_count or 0
        if real:
            return real
        try:
            return int(re.sub(r'[^\d]', '', self.orders_text or '') or 0)
        except Exception:  # noqa: BLE001
            return 0

    # ------------------------------------------------------------------ #
    # backend rich previews
    # ------------------------------------------------------------------ #
    def _gallery_urls(self):
        self.ensure_one()
        urls = []
        if self.image_url:
            urls.append(self.image_url)
        try:
            for u in (json.loads(self.image_urls or '[]') or []):
                if u and u not in urls:
                    urls.append(u)
        except Exception:  # noqa: BLE001
            pass
        return urls

    def _all_image_urls(self):
        """Stable, deterministic gallery order (independent of the chosen main)
        used for the numbered picker: the provider gallery as-is, with the
        original main image guaranteed present at the front."""
        self.ensure_one()
        try:
            gallery = json.loads(self.image_urls or '[]') or []
        except Exception:  # noqa: BLE001
            gallery = []
        urls = [u for u in gallery if u]
        if self.image_url and self.image_url not in urls:
            urls.insert(0, self.image_url)
        return urls

    def action_set_main_image(self):
        """Make the picked gallery image (main_image_index) the main product
        image everywhere. For a materialized product it also refreshes the live
        product.template photo so the app/website update immediately."""
        for rec in self:
            urls = rec._all_image_urls()
            i = rec.main_image_index or 0
            if not urls:
                continue
            if i < 0 or i >= len(urls):
                raise UserError(_("Pick a valid image number (0–%d).")
                                % (len(urls) - 1))
            rec.image_url = urls[i]
            if rec.product_tmpl_id:
                b64 = rec._download(urls[i])
                if b64:
                    rec.product_tmpl_id.sudo().image_1920 = b64
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Main image updated',
                       'message': 'The selected gallery image is now the main '
                                  'product image.',
                       'type': 'success', 'sticky': False},
        }

    def _ds_variants(self):
        self.ensure_one()
        try:
            data = json.loads(self.variants_json or '[]')
            return data if isinstance(data, list) else []
        except Exception:  # noqa: BLE001
            return []

    @api.depends('image_urls', 'image_url', 'specs_json', 'reviews_json',
                 'variants_json', 'shipping_json', 'store_json', 'rating')
    def _compute_previews(self):
        from odoo.tools import html_escape as esc
        for rec in self:
            # gallery — numbered so the admin can pick the main image by number
            imgs = rec._all_image_urls()
            if imgs:
                cur_main = rec.image_url
                cells = []
                for idx, u in enumerate(imgs[:24]):
                    is_main = (u == cur_main)
                    border = ('3px solid #2e7d32' if is_main
                              else '1px solid #eee')
                    badge = ('<div style="position:absolute;top:5px;left:5px;'
                             'background:%s;color:#fff;font-size:11px;font-weight:700;'
                             'border-radius:10px;padding:1px 7px">#%d%s</div>'
                             % ('#2e7d32' if is_main else '#412402', idx,
                                ' ★' if is_main else ''))
                    cells.append(
                        '<div style="position:relative;display:inline-block">'
                        '%s<a href="%s" target="_blank">'
                        '<img src="%s" style="width:110px;height:110px;'
                        'object-fit:cover;border-radius:8px;margin:3px;'
                        'border:%s"/></a></div>'
                        % (badge, esc(u), esc(u), border))
                rec.gallery_preview = (
                    '<div style="display:flex;flex-wrap:wrap">%s</div>'
                    '<div style="color:#888;margin-top:4px">%d image(s) · '
                    'the green ★ image is the current main. Type its number in '
                    '“Main Image #” and click “Set as Main”.</div>'
                    % (''.join(cells), len(imgs)))
            else:
                rec.gallery_preview = '<span style="color:#aaa">No images</span>'
            # specs
            specs = rec._ds_specs()
            if specs:
                rows = ''.join(
                    '<tr><td style="padding:4px 10px;color:#666;'
                    'border-bottom:1px solid #f0f0f0">%s</td>'
                    '<td style="padding:4px 10px;border-bottom:1px solid #f0f0f0">'
                    '%s</td></tr>' % (esc(str(s['name'])), esc(str(s['value'])))
                    for s in specs)
                rec.specs_preview = (
                    '<table style="border-collapse:collapse;width:100%%">%s</table>'
                    % rows)
            else:
                rec.specs_preview = '<span style="color:#aaa">No specifications</span>'
            # reviews
            reviews = rec._ds_reviews(limit=20)
            if reviews:
                cards = []
                for r in reviews:
                    stars = '★' * r['stars_full'] + '☆' * r['stars_empty']
                    photos = ''.join(
                        '<img src="%s" style="width:56px;height:56px;object-fit:'
                        'cover;border-radius:6px;margin:2px"/>' % esc(u)
                        for u in (r.get('images') or []))
                    cards.append(
                        '<div style="border:1px solid #eee;border-radius:8px;'
                        'padding:8px 10px;margin:5px 0">'
                        '<div><b>%s</b> <span style="color:#888">%s</span> '
                        '<span style="color:#F5C320">%s</span> '
                        '<span style="color:#aaa;font-size:11px">%s</span></div>'
                        '<div style="margin:3px 0">%s</div>%s</div>'
                        % (esc(r['name']), esc(r['country']), stars,
                           esc(r['date']), esc(r['text']), photos))
                rec.reviews_preview = ''.join(cards)
            else:
                rec.reviews_preview = '<span style="color:#aaa">No reviews</span>'
            # variants
            variants = rec._ds_variants()
            if variants:
                rows = []
                for v in variants[:60]:
                    label = v.get('name') or v.get('title') or v.get('sku') or '—'
                    price = v.get('price') or v.get('sale_price') or ''
                    sku = v.get('sku') or v.get('id') or ''
                    rows.append(
                        '<tr><td style="padding:4px 10px;border-bottom:1px solid '
                        '#f0f0f0">%s</td><td style="padding:4px 10px;color:#666;'
                        'border-bottom:1px solid #f0f0f0">%s</td><td style="padding:'
                        '4px 10px;border-bottom:1px solid #f0f0f0">%s</td></tr>'
                        % (esc(str(label)), esc(str(sku)), esc(str(price))))
                rec.variants_preview = (
                    '<table style="border-collapse:collapse;width:100%%">'
                    '<tr><th style="text-align:left;padding:4px 10px">Variant</th>'
                    '<th style="text-align:left;padding:4px 10px">SKU</th>'
                    '<th style="text-align:left;padding:4px 10px">Price</th></tr>'
                    '%s</table><div style="color:#888;margin-top:4px">%d variant(s)'
                    '</div>' % (''.join(rows), len(variants)))
            else:
                rec.variants_preview = '<span style="color:#aaa">No variants</span>'
            # shipping
            ship = rec._ds_shipping()
            if ship:
                rows = ''.join(
                    '<tr><td style="padding:4px 10px;border-bottom:1px solid '
                    '#f0f0f0">%s</td><td style="padding:4px 10px;border-bottom:'
                    '1px solid #f0f0f0">%s–%s days</td><td style="padding:4px 10px;'
                    'border-bottom:1px solid #f0f0f0">%s</td></tr>'
                    % (esc(str(o['service'])), o['days_min'], o['days_max'],
                       'Tracked' if o['tracking'] else '—') for o in ship)
                rec.shipping_preview = (
                    '<table style="border-collapse:collapse;width:100%%">%s</table>'
                    % rows)
            else:
                rec.shipping_preview = '<span style="color:#aaa">No shipping data</span>'
            # store / seller
            try:
                store = json.loads(rec.store_json or '{}') or {}
            except Exception:  # noqa: BLE001
                store = {}
            if store:
                rows = ''.join(
                    '<tr><td style="padding:4px 10px;color:#666;border-bottom:'
                    '1px solid #f0f0f0">%s</td><td style="padding:4px 10px;'
                    'border-bottom:1px solid #f0f0f0">%s</td></tr>'
                    % (esc(str(k)), esc(str(v))) for k, v in store.items()
                    if not isinstance(v, (dict, list)))
                rec.store_preview = (
                    '<table style="border-collapse:collapse;width:100%%">%s</table>'
                    % rows)
            else:
                rec.store_preview = '<span style="color:#aaa">No seller info</span>'

    # ------------------------------------------------------------------ #
    # ingest
    # ------------------------------------------------------------------ #
    @api.model
    def _upsert(self, provider, unified):
        """Insert/update one unified product dict. Returns the record."""
        Rule = self.env['dropship.text.rule']
        # brand-scrub every customer-visible text field before storing
        title_en = Rule._apply_all(unified.get('title_en'))
        title_ar = Rule._apply_all(unified.get('title_ar'))
        desc = Rule._apply_all(unified.get('description_html'))

        # deals: compute discount vs the provider's original/list price
        base = unified.get('price') or 0.0
        original = unified.get('original_price') or 0.0
        discount = 0.0
        if original and base and original > base:
            discount = round((original - base) / original * 100.0, 1)
        min_deal = float(self.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.deal_min_percent', 0.0) or 0.0)

        vals = {
            'provider_id': provider.id,
            'source_id': unified['source_id'],
            'title_en': title_en,
            'title_ar': title_ar,
            'description_html': desc,
            'base_cost': base,
            'original_price': original,
            'discount_percent': discount,
            'is_deal': bool(discount and discount >= min_deal),
            'currency_code': unified.get('currency') or 'USD',
            'image_url': unified.get('image_url'),
            'image_urls': json.dumps(unified.get('image_urls') or []),
            'video_url': unified.get('video_url'),
            'category': unified.get('category'),
            'category_name': unified.get('category_name'),
            'category_parent': unified.get('category_parent'),
            'variants_json': json.dumps(unified.get('variants') or []),
            'raw_json': json.dumps(unified.get('raw') or {}, ensure_ascii=False),
        }
        # keep the provider's social proof so we can rank/filter by quality
        # without a detail fetch (feed gives rating as a % + units-sold text).
        _rt = unified.get('rating')
        if _rt not in (None, '', 0):
            try:
                _rn = float(str(_rt).replace('%', '').strip())
                # store as 0-5 stars (feed % ÷ 20); a real star rating (≤5)
                # is kept as-is.
                vals['rating'] = round(_rn / 20.0, 2) if _rn > 5 else round(_rn, 2)
            except (TypeError, ValueError):
                pass
        if unified.get('orders_text'):
            vals['orders_text'] = str(unified['orders_text'])[:32]
        if unified.get('review_count') not in (None, '', 0):
            try:
                vals['review_count'] = min(2000000000, int(re.sub(r'[^\d]', '',
                                                  str(unified['review_count'])) or 0))
            except (TypeError, ValueError):
                pass
        # auto-match the local category (same taxonomy as AliExpress): resolve
        # by the provider category id (ext_id) first, then by readable name.
        cat_rec = self._match_local_category(unified)

        rec = self.search([
            ('provider_id', '=', provider.id),
            ('source_id', '=', unified['source_id']),
        ], limit=1)
        if rec:
            # never clobber a category the admin changed by hand — only fill a
            # blank one on re-sync.
            if cat_rec and not rec.category_id:
                vals['category_id'] = cat_rec.id
            rec.write(vals)
        else:
            if cat_rec:
                vals['category_id'] = cat_rec.id
            rec = self.create(vals)
        rec._compute_prices()
        return rec

    @api.model
    def _match_local_category(self, unified):
        """Map an imported product to one of our dropship.category records
        (our tree mirrors AliExpress, so the provider category id matches an
        ext_id exactly). Falls back to readable name, then parent name."""
        Category = self.env['dropship.category'].sudo()
        ext = str(unified.get('category') or '').strip()
        if ext:
            hit = Category.search([('ext_id', '=', ext)], limit=1)
            if hit:
                return hit
        name = (unified.get('category_name') or '').strip()
        if name:
            hit = Category.search([('name', '=ilike', name)], limit=1)
            if hit:
                return hit
        parent = (unified.get('category_parent') or '').strip()
        if parent:
            hit = Category.search([('name', '=ilike', parent)], limit=1)
            if hit:
                return hit
        return Category.browse()

    def _to_unified(self):
        self.ensure_one()
        return {
            'source_id': self.source_id,
            'title_en': self.title_en,
            'title_ar': self.title_ar,
            'description_html': self.description_html,
            'price': self.base_cost,
            'currency': self.currency_code,
            'image_url': self.image_url,
            'image_urls': json.loads(self.image_urls or '[]'),
            'video_url': self.video_url,
            'original_price': self.original_price,
            'category': self.category,
            'category_name': self.category_name,
            'category_parent': self.category_parent,
            'variants': json.loads(self.variants_json or '[]'),
            'raw': json.loads(self.raw_json or '{}'),
        }

    @api.depends('raw_json', 'source_id', 'provider_id')
    def _compute_source_url(self):
        """Link to the ORIGINAL product page on the provider (backend only).

        Prefers the exact URL from the provider payload; falls back to the
        canonical AliExpress item URL built from the source id.
        """
        for rec in self:
            url = ''
            try:
                raw = json.loads(rec.raw_json or '{}')
                url = (raw.get('product_detail_url') or raw.get('detail_url')
                       or raw.get('productDetailUrl') or '')
            except Exception:  # noqa: BLE001
                url = ''
            if not url and rec.source_id and (rec.provider_id.code or '') == 'aliexpress':
                url = 'https://www.aliexpress.com/item/%s.html' % rec.source_id
            if url and url.startswith('//'):
                url = 'https:' + url
            rec.source_url = url

    # provider CDN hosts whose <img> URLs inside the description HTML get
    # rewritten to the Uellow media proxy (no provider-CDN leak + no hot-link
    # rate-limiting). Mirrors the controller's _IMG_HOST_OK allow-list.
    _CDN_HOSTS = ('alicdn.com', 'aliexpress-media.com', 'aliexpress.com',
                  'ae01.alicdn.com', 'ae-pic', 'kwcdn.com', 'cjdropshipping')

    @api.model
    def _proxy_description_images(self, html):
        """Rewrite provider-CDN <img> URLs in description HTML to /dropship/media.

        Only allow-listed provider hosts are rewritten; anything else (already a
        Uellow URL, or an unknown host) is left untouched. Idempotent — a URL
        already pointing at /dropship/media has no provider host so it is skipped.
        """
        if not html:
            return html
        import base64

        def _repl(m):
            attr, url = m.group(1), m.group(2)
            if url.startswith('/dropship/media'):   # already proxied — idempotent
                return m.group(0)
            full = ('https:' + url) if url.startswith('//') else url
            if any(h in full for h in self._CDN_HOSTS):
                # base64 the URL so no provider hostname string survives in the
                # page source (keeps the "zero provider CDN string" guarantee);
                # the /dropship/media route decodes it to fetch+cache once.
                tok = base64.urlsafe_b64encode(full.encode('utf-8')).decode('ascii')
                return '%s="/dropship/media?u=%s"' % (attr, tok)
            return m.group(0)

        return re.sub(r'(src|data-src)="([^"]+)"', _repl, html)

    def _proxy_media_url(self, url):
        """Return a /dropship/media proxy URL for a single provider-CDN image.

        Keeps the "zero provider-CDN string in page source" guarantee for review
        photos too. Non-provider / already-proxied / empty URLs pass through.
        """
        if not url or not isinstance(url, str):
            return url
        if url.startswith('/dropship/media'):
            return url
        import base64
        full = ('https:' + url) if url.startswith('//') else url
        if any(h in full for h in self._CDN_HOSTS):
            tok = base64.urlsafe_b64encode(full.encode('utf-8')).decode('ascii')
            return '/dropship/media?u=%s' % tok
        return url

    # ------------------------------------------------------------------ #
    # full-detail enrichment: description + specs + shipping + reviews
    # ------------------------------------------------------------------ #
    def _enrich_detail(self, force=False):
        """Fetch the rich product-detail once and cache it on the record.

        Populates the full description, the specifications table, the shipping
        options and the review/seller-rating summary — everything the provider's
        own product page shows — so the Uellow product page can render them.

        Fully fail-soft: any provider/API error leaves the record untouched and
        never blocks opening or buying the product. Freshness-guarded: skips if
        fetched within the last ``detail_ttl_hours`` (default 12h) unless forced.
        """
        self.ensure_one()
        provider = self.provider_id
        if not provider or provider.code == 'manual':
            return False
        ICP = self.env['ir.config_parameter'].sudo()
        # freshness guard — avoid a live call on every product open
        ttl = int(ICP.get_param('uellow_dropship.detail_ttl_hours', 12) or 12)
        if not force and self.detail_synced:
            age = fields.Datetime.now() - self.detail_synced
            if age.total_seconds() < ttl * 3600:
                return False

        adapter = provider._adapter()
        Rule = self.env['dropship.text.rule']
        vals = {'detail_synced': fields.Datetime.now()}

        # 1. full product detail (description + specs + rating summary + store)
        try:
            unified = adapter.get_product(self.source_id)
        except Exception as e:  # noqa: BLE001 - never block on a detail fetch
            _logger.info("detail fetch failed for %s: %s", self.source_id, e)
            unified = None
        if unified:
            # provider stock → availability (auto-unpublish when it hits 0)
            try:
                self._apply_stock(self._stock_from_unified(unified))
            except Exception:  # noqa: BLE001
                pass
            desc = Rule._apply_all(unified.get('description_html'))
            desc = self._proxy_description_images(desc)
            if desc and len(desc) > len(self.description_html or ''):
                vals['description_html'] = desc
            if unified.get('specs'):
                vals['specs_json'] = json.dumps(unified['specs'], ensure_ascii=False)
            if unified.get('store'):
                vals['store_json'] = json.dumps(unified['store'], ensure_ascii=False)
            if unified.get('variants'):
                vals['variants_json'] = json.dumps(unified['variants'], ensure_ascii=False)
            rating = unified.get('rating')
            if rating:
                try:
                    vals['rating'] = float(str(rating).replace('%', '').strip())
                except (TypeError, ValueError):
                    pass
            rc = unified.get('review_count')
            if rc:
                try:
                    vals['review_count'] = min(2000000000, int(re.sub(r'[^\d]', '', str(rc)) or 0))
                except (TypeError, ValueError):
                    pass
            if unified.get('orders_text'):
                vals['orders_text'] = str(unified['orders_text'])[:32]

        # 2. live shipping to the provider's primary country (ONE fast call on
        # import). Full per-country coverage is filled on demand by the
        # "Check shipping coverage" action, not on every import.
        default_country = provider.default_country or 'KW'
        try:
            opts = adapter.get_freight(self.source_id, default_country, 1) or []
        except Exception as e:  # noqa: BLE001
            _logger.info("freight fetch failed for %s: %s", self.source_id, e)
            opts = []
        vals['shippable'] = bool(opts)
        if opts:
            country = self.env['res.country'].sudo().search(
                [('code', '=', default_country)], limit=1)
            if country and country not in self.ship_country_ids:
                vals['ship_country_ids'] = [(4, country.id)]
            opts = sorted(opts, key=lambda o: o.get('cost') or 0)[:4]
            vals['shipping_json'] = json.dumps(opts, ensure_ascii=False)

        # 3. individual customer reviews (public feedback endpoint), gated by
        # the import_reviews setting + a minimum-stars quality filter.
        if ICP.get_param('uellow_dropship.import_reviews', 'True') in ('True', '1', 'true') \
                and hasattr(adapter, 'get_reviews'):
            min_stars = float(ICP.get_param('uellow_dropship.min_review_stars', 0.0) or 0.0)
            try:
                rev = adapter.get_reviews(self.source_id) or {}
            except Exception as e:  # noqa: BLE001
                _logger.info("reviews fetch failed for %s: %s", self.source_id, e)
                rev = {}
            revs = [r for r in (rev.get('reviews') or [])
                    if (r.get('stars') or 0) >= min_stars]
            # reviews WITH photos first (more convincing social proof), keeping
            # the higher-star ones ahead within each group — so the stored top-20
            # is photo-rich.
            revs.sort(key=lambda r: (0 if r.get('images') else 1,
                                     -(r.get('stars') or 0)))
            # brand-scrub the customer-visible review text (and reviewer name)
            # so provider names ("AliExpress", ...) never reach the app. Counted.
            Rule = self.env['dropship.text.rule']
            for r in revs[:60]:
                if r.get('text'):
                    r['text'] = Rule._apply_all(r['text'], count=True)
                if r.get('name'):
                    r['name'] = Rule._apply_all(r['name'], count=True)
            if revs or rev.get('stats'):
                vals['reviews_json'] = json.dumps(
                    {'reviews': revs[:60], 'stats': rev.get('stats') or {}},
                    ensure_ascii=False)

        self.write(vals)

        # push a freshly-fetched full description onto an already-materialized
        # product so the page updates without a re-materialize.
        if self.product_tmpl_id and vals.get('description_html'):
            tmpl = self.product_tmpl_id.sudo()
            dvals = {}
            if 'website_description_en' in tmpl._fields:
                dvals['website_description_en'] = vals['description_html']
            if self.description_ar and 'website_description_ar' in tmpl._fields:
                dvals['website_description_ar'] = self.description_ar
            if dvals:
                tmpl.write(dvals)
        return True

    # ------------------------------------------------------------------ #
    # render helpers for the product page (called from QWeb)
    # ------------------------------------------------------------------ #
    def _ds_specs(self):
        """Return the specifications as a list of {name, value} dicts."""
        self.ensure_one()
        try:
            data = json.loads(self.specs_json or '[]')
            return [d for d in data if d.get('name') and d.get('value')]
        except Exception:  # noqa: BLE001
            return []

    def _ds_shipping(self):
        """Return shipping options with a customer-facing ETA (safety buffer added).

        Cost stays informational; the customer price already includes freight, so
        the template frames this as delivery time, not an extra charge.
        """
        self.ensure_one()
        try:
            opts = json.loads(self.shipping_json or '[]')
        except Exception:  # noqa: BLE001
            return []
        buf = int(self.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.eta_extra_days', 3) or 3)
        out = []
        for o in opts:
            dmin = int(o.get('days_min') or 0)
            dmax = int(o.get('days_max') or 0)
            out.append({
                'service': o.get('service') or 'Standard',
                'days_min': (dmin + buf) if dmin else 0,
                'days_max': (dmax + buf) if dmax else 0,
                'tracking': bool(o.get('tracking')),
                'free': bool(o.get('free')),
            })
        return out

    def _ds_review_summary(self):
        """Return the review/seller-rating summary for the product page.

        Individual review comments are not exposed by the AliExpress DS API, so
        this is the rating average + evaluation count + units sold + the seller's
        service ratings — the same social-proof block the source page shows.
        """
        self.ensure_one()
        if not self.rating and not self.review_count:
            return None
        try:
            store = json.loads(self.store_json or '{}')
        except Exception:  # noqa: BLE001
            store = {}
        rating = round(self.rating or 0.0, 1)
        full = int(rating)
        half = 1 if (rating - full) >= 0.5 else 0
        empty = 5 - full - half
        # rating breakdown (5★/4★/3★/1-2★ bars) from the reviews stats, if fetched
        breakdown = None
        try:
            rv = json.loads(self.reviews_json or '{}')
            st = rv.get('stats') or {}
            total = st.get('total') or 0
            if total:
                def _pct(n):
                    return round((n or 0) * 100.0 / total, 0)
                breakdown = [
                    {'label': '5', 'n': st.get('five') or 0, 'pct': _pct(st.get('five'))},
                    {'label': '4', 'n': st.get('four') or 0, 'pct': _pct(st.get('four'))},
                    {'label': '3', 'n': st.get('three') or 0, 'pct': _pct(st.get('three'))},
                    {'label': '1-2', 'n': st.get('negative') or 0, 'pct': _pct(st.get('negative'))},
                ]
        except Exception:  # noqa: BLE001
            breakdown = None
        return {
            'rating': rating,
            'avg': rating,                       # app rating widgets read `avg`
            'stars_full': full,
            'stars_half': half,
            'stars_empty': max(empty, 0),
            'review_count': self.review_count or 0,
            'count': self.review_count or 0,     # + `count`
            'total': self.review_count or 0,     # + `total` (reviews UI)
            'orders_text': self.orders_text or '',
            'store': store or {},
            'breakdown': breakdown,
        }

    def _ds_reviews(self, limit=8):
        """Return individual customer reviews for the product page (list of
        {name, country, stars, date, text, sku}). Empty if none fetched."""
        self.ensure_one()
        try:
            rv = json.loads(self.reviews_json or '{}')
            revs = rv.get('reviews') or []
        except Exception:  # noqa: BLE001
            return []
        out = []
        Rule = self.env['dropship.text.rule']
        for r in revs[:limit]:
            if not r.get('text'):
                continue
            s = int(r.get('stars') or 5)
            imgs = [self._proxy_media_url(u) for u in (r.get('images') or []) if u][:4]
            # display-path safety net: scrub provider names even from reviews
            # imported before the ingest-time scrub existed. count=False so a
            # page view never writes/inflates the rule counters.
            out.append({
                'name': Rule._apply_all(r.get('name') or 'Shopper'),
                'country': r.get('country') or '',
                'stars_full': max(1, min(5, s)),
                'stars_empty': max(0, 5 - max(1, min(5, s))),
                'date': r.get('date') or '',
                'text': Rule._apply_all(r.get('text') or ''),
                'sku': r.get('sku') or '',
                'images': imgs,
            })
        return out

    # ------------------------------------------------------------------ #
    # pricing: provider cost -> customer sale price (in company currency)
    # ------------------------------------------------------------------ #
    def _compute_prices(self):
        """Fill landed_price + sale_price from settings (customs, FX, markup, rounding).

        Runs at listing time so the storefront can show a price without a live
        API call. Shipping is added per-destination at checkout via get_freight.
        """
        ICP = self.env['ir.config_parameter'].sudo()
        company_cur = self.env.company.currency_id
        customs = float(ICP.get_param('uellow_dropship.customs_percent', 0.0) or 0.0)
        fx_buffer = float(ICP.get_param('uellow_dropship.fx_buffer', 0.0) or 0.0)
        default_markup = float(ICP.get_param('uellow_dropship.default_markup', 0.0) or 0.0)
        rounding = ICP.get_param('uellow_dropship.price_rounding', '900')

        for rec in self:
            # convert base cost -> company currency (e.g. KWD)
            src_cur = self.env['res.currency'].search(
                [('name', '=', (rec.currency_code or 'USD'))], limit=1) or company_cur
            try:
                kwd_cost = src_cur._convert(rec.base_cost or 0.0, company_cur,
                                            self.env.company, fields.Date.today())
            except Exception:  # noqa: BLE001 - unknown currency -> assume already company cur
                kwd_cost = rec.base_cost or 0.0
            landed = kwd_cost * (1 + customs / 100.0) * (1 + fx_buffer / 100.0)
            markup = rec.provider_id.markup_percent or default_markup
            price = landed * (1 + markup / 100.0)
            rec.landed_price = landed
            rec.sale_price = rec._charm_round(price, rounding)

    @staticmethod
    def _charm_round(price, mode):
        """Round up to a psychological ending (.900/.990/.950) or plain."""
        if not price:
            return 0.0
        import math
        base = math.floor(price)
        endings = {'900': 0.900, '990': 0.990, '950': 0.950}
        if mode in endings:
            candidate = base + endings[mode]
            return round(candidate if candidate >= price else base + 1 + endings[mode], 3)
        return round(price, 3)

    # ------------------------------------------------------------------ #
    # materialize-on-order (the anti-bloat core)
    # ------------------------------------------------------------------ #
    def _materialize(self):
        """Create the real product.template (idempotent). Returns it."""
        self.ensure_one()
        if self.product_tmpl_id:
            return self.product_tmpl_id

        ICP = self.env['ir.config_parameter'].sudo()
        website_id = ICP.get_param('uellow_dropship.website_id')
        markup = self.provider_id.markup_percent or float(ICP.get_param('uellow_dropship.default_markup', 0.0))
        # real landed price at the point of purchase = (cost+customs+fx + live shipping) x markup
        price = self._landed_with_shipping(markup) or self.sale_price \
            or (self.landed_price or self.base_cost) * (1 + markup / 100.0)

        # create as SUPERUSER so a public "buy now" request can materialize the
        # product; is_storable=False keeps it off the warehouse (pure dropship).
        vals = {
            'name': self.title_en or (_("Dropship %s") % self.source_id),
            'type': 'consu',                     # "Goods" in v18
            'is_dropship': True,
            'dropship_product_id': self.id,
            # internal reference = the raw product number only (no provider name /
            # no "DS-" prefix) so it never leaks "aliexpress" into the display name
            # or the storefront slug. is_dropship=True is the real dropship flag.
            'default_code': self.source_id,
            'list_price': price,
            # strike-through "before" price so a discounted product shows the
            # old price + discount % on the card/page (only when it's a real
            # markdown vs our selling price).
            'compare_list_price': (self.original_price
                                   if self.original_price and self.original_price > price
                                   else 0.0),
            'standard_price': self.base_cost,
            'website_published': bool(ICP.get_param('uellow_dropship.auto_publish')),
            'website_id': int(website_id) if website_id else False,
            # company_id = the World website's OWN company, so World (dropship)
            # products stay isolated to that company and never leak into other
            # companies' backend views (smart connector, product lists, etc.).
            # This does NOT break app rendering: the mobile-app World APIs read
            # these products via sudo() (app_bridge World* controllers), which
            # bypasses multi-company record rules. Falls back to False only when
            # the World website / its company can't be resolved.
            'company_id': (self.env['website'].sudo().browse(int(website_id)).company_id.id
                           if website_id else False),
            'description_sale': self.description_html or False,
        }
        if 'is_storable' in self.env['product.template']._fields:
            vals['is_storable'] = False          # no inventory tracking for dropship
        # NOTE: dropship products deliberately get NO product.public.category — the
        # World taxonomy is a SEPARATE module-only model (dropship.category) so it
        # never pollutes the main store's shared category tree. The World storefront
        # renders its own category tiles from dropship.category.
        tmpl = self.env['product.template'].with_user(SUPERUSER_ID).create(vals)
        # bilingual name: the create() above set the current-lang value; write the
        # Arabic translation too so the product page reads AR in Arabic mode (the
        # store is EN-primary + AR, never English-only).
        ar_lang = self.env['res.lang'].sudo().search(
            [('code', 'like', 'ar%'), ('active', '=', True)], limit=1)
        # Write each language value EXPLICITLY (never rely on the ambient request
        # context lang, which on a materialize-during-request can be Arabic and would
        # otherwise land the English text in the ar_001 slot and vice-versa).
        if self.title_en and self.title_en.strip():
            tmpl.with_user(SUPERUSER_ID).with_context(lang='en_US').name = self.title_en
        if self.title_ar and self.title_ar.strip() and ar_lang:
            tmpl.with_user(SUPERUSER_ID).with_context(lang=ar_lang.code).name = self.title_ar
        # bilingual description on the product page. The Uellow product page
        # (product_page_custom / uellow_theme) renders the two PLAIN, non-translated
        # fields website_description_en / website_description_ar by lang — using the
        # standard translated website_description would collapse both languages into
        # one value (html_translate clobbers an empty source). Write the plain fields.
        dvals = {}
        if self.description_html:
            dvals['website_description_en'] = self.description_html
        if self.description_ar:
            dvals['website_description_ar'] = self.description_ar
        if dvals:
            tmpl.with_user(SUPERUSER_ID).write(dvals)
        # SEO meta description (plain translate field — write en_US source FIRST, then
        # the ar_001 translation; leave website_meta_title empty so it falls back to the
        # already-clean product name). Never set the raw provider title into meta.
        def _plain(html, limit=155):
            t = re.sub(r'<[^>]+>', ' ', html or '')
            t = re.sub(r'\s+', ' ', t).strip()
            return (t[:limit].rstrip() + '…') if len(t) > limit else t
        md_en = _plain(self.description_html) or (self.title_en or '')
        md_ar = _plain(self.description_ar) or (self.title_ar or '')
        if md_en:
            tmpl.with_user(SUPERUSER_ID).with_context(lang='en_US').website_meta_description = md_en
            tmpl.env.flush_all()
        if md_ar and ar_lang:
            tmpl.with_user(SUPERUSER_ID).with_context(lang=ar_lang.code).website_meta_description = md_ar
            tmpl.env.flush_all()
        # SEO meta title: the seo_manager autofills this on the name write above, but
        # only in the current (en_US) lang — leaving the AR page with an English title.
        # Set both langs explicitly from the clean provider titles (en source first).
        if self.title_en and self.title_en.strip():
            tmpl.with_user(SUPERUSER_ID).with_context(lang='en_US').website_meta_title = self.title_en[:70]
            tmpl.env.flush_all()
        if self.title_ar and self.title_ar.strip() and ar_lang:
            tmpl.with_user(SUPERUSER_ID).with_context(lang=ar_lang.code).website_meta_title = self.title_ar[:70]
        # media: main image + full gallery + video, so the standard Uellow product
        # page shows everything "inside" the product exactly like a normal product.
        self.with_user(SUPERUSER_ID)._attach_media(tmpl)
        # variants: rebuild the provider's Color/Size selectors + per-variant
        # images so the page offers the same options AliExpress shows. Fail-soft.
        try:
            self.with_user(SUPERUSER_ID)._apply_variants(tmpl)
        except Exception as e:  # noqa: BLE001 - variants never block materialize
            _logger.info("apply_variants failed for %s: %s", self.source_id, e)
        self.write({'product_tmpl_id': tmpl.id, 'state': 'materialized'})
        return tmpl

    # ------------------------------------------------------------------ #
    # variants: provider SKUs -> Odoo attributes/values + per-variant image
    # ------------------------------------------------------------------ #
    def _apply_variants(self, tmpl):
        """Build Color/Size selectors from the provider SKU list.

        * Uses DROPSHIP-OWNED attributes (is_dropship_attr, radio display) so the
          main store's attribute lists stay clean and there are no empty swatches.
        * UNIFORM pricing: AliExpress prices are per full SKU combination, which
          Odoo's additive price_extra cannot represent exactly — so we keep the
          single computed list_price to avoid mispricing at checkout.
        * Idempotent (skips if the template already has attribute lines) and
          guarded (only attributes that actually vary; combos capped).
        Returns True if variants were built.
        """
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.import_variants', 'True') \
                not in ('True', '1', 'true'):
            return False
        if tmpl.attribute_line_ids:
            return False
        # never restructure a product that already has sale order lines
        if tmpl.product_variant_ids and self.env['sale.order.line'].sudo().search_count(
                [('product_id', 'in', tmpl.product_variant_ids.ids)]):
            return False
        try:
            variants = json.loads(self.variants_json or '[]')
        except Exception:  # noqa: BLE001
            return False
        # ordered {attr_name: [values]} across all SKUs
        attr_values = {}
        for v in variants:
            for opt in v.get('options') or []:
                name, val = opt.get('name'), opt.get('value')
                if not name or not val:
                    continue
                attr_values.setdefault(name, [])
                if val not in attr_values[name]:
                    attr_values[name].append(val)
        # keep only attributes that actually vary
        attr_values = {k: vs for k, vs in attr_values.items() if len(vs) >= 2}
        if not attr_values:
            return False
        # explosion guard
        combos = 1
        for vs in attr_values.values():
            combos *= len(vs)
        cap = int(ICP.get_param('uellow_dropship.max_variants', 0) or 0)
        if cap and combos > cap:
            return False

        Attr = self.env['product.attribute'].sudo()
        Val = self.env['product.attribute.value'].sudo()
        lines = []
        for name, vals in attr_values.items():
            attr = Attr.search([('name', '=', name),
                                ('is_dropship_attr', '=', True)], limit=1)
            if not attr:
                attr = Attr.create({
                    'name': name, 'create_variant': 'always',
                    'display_type': 'radio', 'is_dropship_attr': True})
            value_ids = []
            for val in vals:
                av = Val.search([('attribute_id', '=', attr.id),
                                 ('name', '=', val)], limit=1)
                if not av:
                    av = Val.create({'attribute_id': attr.id, 'name': val})
                value_ids.append(av.id)
            lines.append((0, 0, {'attribute_id': attr.id,
                                 'value_ids': [(6, 0, value_ids)]}))
        tmpl.write({'attribute_line_ids': lines})
        try:
            self._apply_variant_images(tmpl, variants)
        except Exception as e:  # noqa: BLE001
            _logger.info("variant images failed for %s: %s", self.source_id, e)
        return True

    def _apply_variant_images(self, tmpl, variants):
        """Set each generated variant's image from the provider SKU option image.

        Matches a product.product to its provider SKU by the set of (attr, value)
        options, then downloads that SKU's option image (usually the colour photo)
        onto the variant so picking an option shows the right picture. Bounded +
        fail-soft; downloads run in parallel like the main gallery.
        """
        # provider variant lookup: frozenset{(attr,value)} -> best image url
        by_key = {}
        for v in variants:
            opts = v.get('options') or []
            key = frozenset((o.get('name'), o.get('value')) for o in opts
                            if o.get('name') and o.get('value'))
            img = next((o.get('image') for o in opts if o.get('image')), None)
            if key and img and key not in by_key:
                by_key[key] = img
        if not by_key:
            return
        targets = []   # (product.product, url)
        for pv in tmpl.product_variant_ids:
            key = frozenset(
                (ptav.attribute_id.name, ptav.product_attribute_value_id.name)
                for ptav in pv.product_template_attribute_value_ids)
            url = by_key.get(key)
            if url:
                targets.append((pv, url))
        if not targets:
            return
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(6, len(targets))) as pool:
            imgs = list(pool.map(lambda t: self._download(t[1]), targets))
        for (pv, _url), b64 in zip(targets, imgs):
            if b64:
                pv.sudo().image_1920 = b64

    # ------------------------------------------------------------------ #
    # media enrichment (images + video) on the real product
    # ------------------------------------------------------------------ #
    def _attach_media(self, tmpl):
        """Download main image + gallery + attach video onto the product.

        Fail-soft per asset: a slow/broken URL never blocks materialize. Runs
        only at materialize time (order/open) so it stays bounded — no bloat.

        Downloads run CONCURRENTLY (thread pool): the customer's "open product"
        request used to block ~8s while the main image + up to 8 gallery images
        were fetched one after another. Fetching them in parallel collapses that
        to roughly the single slowest image. DB writes stay sequential (one cursor).
        """
        self.ensure_one()
        ICP = self.env['ir.config_parameter'].sudo()
        max_imgs = int(ICP.get_param('uellow_dropship.max_gallery_images', 8) or 8)

        # ordered list of URLs to fetch: main first, then unique gallery images
        try:
            gallery = json.loads(self.image_urls or '[]')
        except Exception:  # noqa: BLE001
            gallery = []
        urls = []
        if self.image_url:
            urls.append(self.image_url)
        for url in gallery[:max_imgs]:
            if url and url != self.image_url and url not in urls:
                urls.append(url)
        if not urls:
            return

        # fetch all in parallel (fail-soft per url), preserving order for ranking
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
            results = list(pool.map(self._download, urls))

        Image = self.env['product.image'].sudo()
        poster = None
        rank = 0
        for url, b64 in zip(urls, results):
            if not b64:
                continue
            if url == self.image_url and poster is None:
                # main image -> the product's primary image
                poster = b64
                tmpl.write({'image_1920': b64})
                continue
            rank += 1
            if poster is None:
                poster = b64
                tmpl.write({'image_1920': b64})
                continue
            Image.create({
                'name': '%s #%s' % (self.title_en or 'Image', rank),
                'image_1920': b64,
                'product_tmpl_id': tmpl.id,
                'sequence': rank,
            })
        # Note: the product video (self.video_url) is a RAW mp4 from the provider,
        # which Odoo's product.image.video_url (YouTube/Vimeo embed_code only) can't
        # play — it would render as a dead static poster. Instead the storefront
        # template `dropship_product_video` renders a native HTML5 <video> player
        # from dropship_product_id.video_url, so no video product.image is created.

    @staticmethod
    def _download(url, timeout=12):
        """Fetch an image URL -> base64 bytes (or None on any failure)."""
        if not url:
            return None
        import base64
        import requests
        try:
            if url.startswith('//'):
                url = 'https:' + url
            resp = requests.get(url, timeout=timeout, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; UellowBot/1.0)'})
            if resp.status_code == 200 and resp.content:
                return base64.b64encode(resp.content)
        except Exception:  # noqa: BLE001 - fail-soft, media is best-effort
            return None
        return None

    def _landed_with_shipping(self, markup):
        """Live landed price incl. cheapest real shipping to the target country.

        Best-effort: on any provider/API error, returns None so the caller falls
        back to the pre-computed listing price (fail-soft, never blocks a sale).
        """
        self.ensure_one()
        if self.provider_id.code == 'manual':
            return None
        ICP = self.env['ir.config_parameter'].sudo()
        country = self.provider_id.default_country or 'KW'
        try:
            opts = self.provider_id._adapter().get_freight(self.source_id, country, 1)
        except Exception as e:  # noqa: BLE001 - never let shipping lookup block materialize
            _logger.info("freight lookup failed for %s: %s", self.source_id, e)
            return None
        if not opts:
            return None
        cheapest = min(opts, key=lambda o: o.get('cost') or 0)
        # convert shipping (provider currency) -> company currency
        company_cur = self.env.company.currency_id
        src_cur = self.env['res.currency'].search(
            [('name', '=', (cheapest.get('currency') or 'USD'))], limit=1) or company_cur
        try:
            ship_kwd = src_cur._convert(cheapest.get('cost') or 0.0, company_cur,
                                        self.env.company, fields.Date.today())
        except Exception:  # noqa: BLE001
            ship_kwd = cheapest.get('cost') or 0.0
        landed = (self.landed_price or self.base_cost) + ship_kwd
        return self._charm_round(landed * (1 + (markup or 0) / 100.0),
                                 ICP.get_param('uellow_dropship.price_rounding', '900'))

    @api.model
    def _cron_purge_stale(self):
        """Delete never-ordered listings older than the configured window."""
        days = int(self.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.purge_stale_days', 0) or 0)
        if not days:
            return
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        stale = self.search([('state', '=', 'listed'), ('create_date', '<', cutoff)])
        stale.unlink()

    @api.model
    def _cron_translate_names(self):
        """PHASE 2 — auto-translate imported product titles to Arabic. Batched
        (one AI call for many titles = credit-efficient), fail-soft (stops the
        run cleanly when Anthropic credits are out, retries next run). Gated by
        the autotranslate_names setting. Pushes the AR name onto a live product."""
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.autotranslate_names', 'True') not in ('True', '1', 'true'):
            return
        batch = int(ICP.get_param('uellow_dropship.translate_batch', 40) or 40)
        rounds = int(ICP.get_param('uellow_dropship.translate_rounds', 3) or 3)
        ar_lang = self.env['res.lang'].sudo().search(
            [('code', 'like', 'ar%'), ('active', '=', True)], limit=1)
        for _r in range(max(1, rounds)):
            prods = self.search([('title_en', '!=', False), ('title_ar', '=', False)],
                               limit=batch)
            if not prods:
                return
            payload = {str(p.id): (p.title_en or '')[:120] for p in prods}
            prompt = (
                "Translate each product title to natural Kuwaiti-Arabic e-commerce "
                "wording. Keep brand/model names in Latin. Return ONLY a JSON object "
                "mapping the same id to the Arabic title.\n\n" +
                json.dumps(payload, ensure_ascii=False))
            try:
                raw = prods[0]._call_ai(prompt)
                data = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except Exception as e:  # noqa: BLE001 - credits/API out → retry next run
                _logger.info("dropship translate paused: %s", str(e)[:120])
                return
            Rule = self.env['dropship.text.rule']
            for p in prods:
                ar = data.get(str(p.id))
                if not ar:
                    continue
                ar = Rule._apply_all(ar) or ar
                p.title_ar = ar
                if p.product_tmpl_id and ar_lang:
                    p.product_tmpl_id.with_user(SUPERUSER_ID).with_context(
                        lang=ar_lang.code).name = ar
            self.env.cr.commit()

    def action_promote(self):
        """Turn a bestseller into a real product early (demand radar)."""
        for rec in self:
            rec._materialize()
            rec.state = 'promoted'
        return True

    def action_publish(self):
        """Publish the product to Uellow World so it appears in the app / store.
        Creates the live product first if it doesn't exist yet. Skips products
        that can't ship to us (guarded by the require_shippable setting)."""
        require_ship = self.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.require_shippable', 'True') in ('True', '1', 'true')
        published = 0
        skipped = 0
        for rec in self:
            if require_ship and not rec.shippable:
                skipped += 1
                continue
            if not rec.product_tmpl_id:
                rec._materialize()          # Listed → creates the live product
            if rec.product_tmpl_id:
                rec.product_tmpl_id.sudo().write({'is_published': True,
                                                  'active': True})
                if rec.state == 'listed':
                    rec.state = 'materialized'
                published += 1
        msg = '%d product(s) are now live on Uellow World.' % published
        if skipped:
            msg += ' %d skipped — they don\'t ship to us.' % skipped
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Published',
                       'message': msg,
                       'type': 'warning' if skipped else 'success', 'sticky': bool(skipped)},
        }

    def action_unpublish(self):
        """Hide the product from Uellow World (app + store) WITHOUT deleting it —
        the live product is kept, just not visible. Re-publish anytime."""
        hidden = 0
        for rec in self:
            if rec.product_tmpl_id:
                rec.product_tmpl_id.sudo().write({'is_published': False})
                hidden += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Unpublished',
                       'message': '%d product(s) hidden from the app / store '
                                  '(still kept — re-publish anytime).' % hidden,
                       'type': 'warning', 'sticky': False},
        }

    def action_unpromote(self):
        """Undo a promote/materialize: unpublish + archive the live product and
        send the listing back to 'listed'. Refuses if the product already has
        confirmed orders (protects real sales data)."""
        SOL = self.env['sale.order.line'].sudo()
        reverted = 0
        for rec in self:
            tmpl = rec.product_tmpl_id
            if tmpl:
                if SOL.search_count([
                        ('product_id', 'in', tmpl.product_variant_ids.ids),
                        ('state', 'in', ('sale', 'done'))]):
                    raise UserError(_(
                        "“%s” already has confirmed orders — it can’t be "
                        "reverted. Archive it manually if needed.")
                        % (rec.title_en or rec.source_id))
                tmpl.sudo().write({'is_published': False, 'active': False})
            rec.write({'product_tmpl_id': False, 'state': 'listed'})
            reverted += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'title': 'Reverted',
                       'message': '%d product(s) sent back to Listed (the live '
                                  'product was unpublished + archived).' % reverted,
                       'type': 'success', 'sticky': False},
        }

    def action_open_source(self):
        """Open the product on the provider (used by the stat buttons)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.source_url or '#',
            'target': 'new',
        }

    # ------------------------------------------------------------------ #
    # deals: manual selection + frequent price/stock sync
    # ------------------------------------------------------------------ #
    def action_mark_deal(self):
        """Pin the selected products as deals (offers rail)."""
        self.write({'is_deal': True})
        return True

    def action_apply_slowmover_discount(self):
        """Cut the price of the selected slow movers by the configured % and
        put them on the deals rail — a one-click rescue for viewed-but-unsold
        products. Pushes the new price onto the live product too."""
        pct = float(self.env['ir.config_parameter'].sudo().get_param(
            'uellow_dropship.slowmover_discount', 15.0) or 15.0)
        if pct <= 0:
            return True
        for rec in self:
            if not rec.sale_price:
                continue
            new_price = round(rec.sale_price * (1 - pct / 100.0), 2)
            if new_price <= 0:
                continue
            if not rec.original_price or rec.original_price < rec.sale_price:
                rec.original_price = rec.sale_price   # keep a strike-through ref
            rec.sale_price = new_price
            rec.is_deal = True
            if rec.product_tmpl_id:
                rec.product_tmpl_id.sudo().list_price = new_price
        return True

    def action_unmark_deal(self):
        self.write({'is_deal': False})
        return True

    def _sync_price_stock(self):
        """Re-fetch the live provider price for this listing and push it onto
        the materialized product (list_price + cost). Used by the frequent
        deals-sync cron so offer prices never go stale."""
        self.ensure_one()
        provider = self.provider_id
        if not provider or provider.code == 'manual':
            return False
        try:
            unified = provider._adapter().get_product(self.source_id)
        except Exception as e:  # noqa: BLE001
            _logger.info("price sync failed for %s: %s", self.source_id, e)
            return False
        if not unified:
            # stamp the attempt so a permanently-failing product doesn't get
            # re-picked every single run (no repetition / no starving others)
            self.sudo().write({'price_synced': fields.Datetime.now()})
            return False
        base = unified.get('price') or 0.0
        original = unified.get('original_price') or 0.0
        old_cost = self.base_cost or 0.0
        # provider stock → availability (auto-unpublish when it hits 0)
        try:
            self._apply_stock(self._stock_from_unified(unified))
        except Exception:  # noqa: BLE001 - stock must not break price sync
            pass
        vals = {}
        if base:
            vals['base_cost'] = base
        if original:
            vals['original_price'] = original
        if base and original and original > base:
            disc = round((original - base) / original * 100.0, 1)
            vals['discount_percent'] = disc
            min_deal = float(self.env['ir.config_parameter'].sudo().get_param(
                'uellow_dropship.deal_min_percent', 0.0) or 0.0)
            vals['is_deal'] = bool(disc >= min_deal)
        if vals:
            self.write(vals)
            self._compute_prices()
            # price intelligence: log a provider-cost move + margin re-check
            if base and old_cost and abs(base - old_cost) / old_cost > 0.001:
                try:
                    self._log_price_change(old_cost, base, note='price sync')
                except Exception:  # noqa: BLE001 - intel must not break the sync
                    pass
            # keep the live product in step (price shown to customers)
            if self.product_tmpl_id:
                tmpl = self.product_tmpl_id.sudo()
                pvals = {}
                if self.sale_price:
                    pvals['list_price'] = self.sale_price
                if self.base_cost:
                    pvals['standard_price'] = self.base_cost
                if pvals:
                    tmpl.write(pvals)
        # always stamp the sync time (even when nothing changed) so the crons'
        # oldest-first ordering keeps advancing — never re-hits the same product.
        self.sudo().write({'price_synced': fields.Datetime.now()})
        return True

    def action_refresh_provider(self):
        """Manually re-fetch everything (details + live price) for the selected
        listings from the provider. Header button + bulk list action."""
        for rec in self:
            try:
                rec._enrich_detail(force=True)
            except Exception:  # noqa: BLE001
                pass
            rec._sync_price_stock()
        return True

    @api.model
    def _cron_auto_promote(self):
        """Idea: auto-promote proven sellers. Any listing whose provider units
        sold >= the threshold is turned into a live product early (demand radar)
        without waiting for the first on-site order. Gated + bounded."""
        import time as _time
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.enabled') not in ('True', '1', 'true'):
            return
        if ICP.get_param('uellow_dropship.autopromote', 'False') not in ('True', '1', 'true'):
            return
        threshold = int(ICP.get_param('uellow_dropship.autopromote_min_orders', 500) or 500)
        limit = int(ICP.get_param('uellow_dropship.autopromote_max_per_run', 50) or 50)
        candidates = self.search([('state', '=', 'listed')], limit=limit * 4)
        done = 0
        for rec in candidates:
            if done >= limit:
                break
            try:
                sold = int(re.sub(r'[^\d]', '', rec.orders_text or '') or 0)
            except Exception:  # noqa: BLE001
                sold = 0
            if sold >= threshold:
                try:
                    rec._materialize()
                    rec.state = 'promoted'
                    done += 1
                    self.env.cr.commit()
                except Exception:  # noqa: BLE001
                    self.env.cr.rollback()
        if done:
            _logger.info("dropship auto-promote: promoted %d bestsellers", done)
        return True

    @api.model
    def _cron_sync_deals(self):
        """Short-interval sync of DEAL products so their offer prices stay fresh.
        Oldest-first by ``price_synced`` (stamped every sync) so it advances
        through the whole set with no repetition; skips ones synced in the last
        `deal_sync_minutes` so a run never re-hits fresh products."""
        import time as _time
        from datetime import timedelta
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.enabled') not in ('True', '1', 'true'):
            return
        if ICP.get_param('uellow_dropship.deal_sync_enabled', 'True') not in ('True', '1', 'true'):
            return
        # never add load to a busy server — skip this run entirely if the box
        # is under pressure (same guard the auto-importer uses).
        if not self.env['dropship.import.service'].sudo()._load_ok(ICP):
            _logger.info("dropship deal-sync: server busy, skipping this run")
            return
        budget = int(ICP.get_param('uellow_dropship.deal_sync_budget', 60) or 60)
        rate_ms = int(ICP.get_param('uellow_dropship.rate_limit_ms', 300) or 300)
        fresh_min = int(ICP.get_param('uellow_dropship.deal_sync_minutes', 60) or 60)
        cutoff = fields.Datetime.now() - timedelta(minutes=fresh_min)
        deadline = _time.time() + budget
        # NB: '|' → price_synced is null OR older than the freshness cutoff.
        deals = self.search([('is_deal', '=', True),
                             ('state', 'in', ['materialized', 'promoted']),
                             '|', ('price_synced', '=', False),
                                  ('price_synced', '<', cutoff)],
                            order='price_synced asc nulls first')
        for i, rec in enumerate(deals):
            if _time.time() > deadline:
                break
            # re-check load periodically → bail out the moment the box gets busy
            if i and i % 20 == 0 and not self.env['dropship.import.service'].sudo()._load_ok(ICP):
                _logger.info("dropship deal-sync: load spiked, stopping run")
                break
            rec._sync_price_stock()
            self.env.cr.commit()
            if rate_ms:
                _time.sleep(rate_ms / 1000.0)
        return True

    @api.model
    def _cron_sync_all(self):
        """General price/stock sync for EVERY live (materialized/promoted)
        product — not just deals — so nothing goes stale beyond
        `sync_max_age_hours` (default 24h). Oldest-first by ``price_synced``
        with a stale cutoff, so each run advances through the backlog and never
        re-syncs a product that is already fresh (no repetition)."""
        import time as _time
        from datetime import timedelta
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow_dropship.enabled') not in ('True', '1', 'true'):
            return
        if ICP.get_param('uellow_dropship.full_sync_enabled', 'True') not in ('True', '1', 'true'):
            return
        Svc = self.env['dropship.import.service'].sudo()
        # skip entirely on a busy server (never compete with live customer traffic)
        if not Svc._load_ok(ICP):
            _logger.info("dropship full-sync: server busy, skipping this run")
            return
        budget = int(ICP.get_param('uellow_dropship.full_sync_budget', 120) or 120)
        rate_ms = int(ICP.get_param('uellow_dropship.rate_limit_ms', 300) or 300)
        max_age = int(ICP.get_param('uellow_dropship.sync_max_age_hours', 24) or 24)
        cutoff = fields.Datetime.now() - timedelta(hours=max_age)
        deadline = _time.time() + budget
        recs = self.search([('state', 'in', ['materialized', 'promoted']),
                            '|', ('price_synced', '=', False),
                                 ('price_synced', '<', cutoff)],
                           order='price_synced asc nulls first')
        done = 0
        for rec in recs:
            if _time.time() > deadline:
                break
            # abort mid-run the instant the server gets busy
            if done and done % 20 == 0 and not Svc._load_ok(ICP):
                _logger.info("dropship full-sync: load spiked, stopping run")
                break
            rec._sync_price_stock()
            self.env.cr.commit()
            done += 1
            if rate_ms:
                _time.sleep(rate_ms / 1000.0)
        if done:
            _logger.info("dropship full-sync: refreshed %d products", done)
        return True

    # ------------------------------------------------------------------ #
    # AI content rewrite (title + description, EN + AR) — website-ready
    # ------------------------------------------------------------------ #
    def action_ai_rewrite(self):
        """Rewrite title + description in clean EN + AR via Beena's Claude engine.

        Fills fields that map 1:1 to what the Uellow website uses, so the same
        rewrite is reusable when we later enable dropshipping on the website.
        """
        Rule = self.env['dropship.text.rule']
        for rec in self:
            payload = rec._ai_rewrite_one()
            # scrub AI output too, so provider names never slip back in
            rec.write({
                'title_en': Rule._apply_all(payload.get('title_en')) or rec.title_en,
                'title_ar': Rule._apply_all(payload.get('title_ar')) or rec.title_ar,
                'description_html': Rule._apply_all(payload.get('description_en')) or rec.description_html,
                'description_ar': Rule._apply_all(payload.get('description_ar')) or rec.description_ar,
                'ai_rewritten': True,
            })
            # keep an already-materialized product in sync (guard optional fields)
            if rec.product_tmpl_id:
                tmpl = rec.product_tmpl_id.sudo()
                sync = {'name': rec.title_en}
                if 'website_description_en' in tmpl._fields:
                    sync['website_description_en'] = payload.get('description_en')
                if 'website_description_ar' in tmpl._fields:
                    sync['website_description_ar'] = payload.get('description_ar')
                tmpl.write(sync)
        return True

    def _ai_rewrite_one(self):
        """Call the shared AI engine. Returns dict with the 4 rewritten fields.

        Isolated in one method so we can later expose the SAME call to the
        website product form.
        """
        self.ensure_one()
        prompt = (
            "Rewrite this dropshipping product for a Kuwaiti store. Return JSON with "
            "keys title_en, title_ar, description_en, description_ar. Clean, honest, "
            "no fake claims, concise marketing tone.\n\n"
            "Original title: %s\nOriginal description: %s"
        ) % (self.title_en or '', (self.description_html or '')[:4000])
        try:
            Ctrl = self.env['ir.config_parameter']  # engine call is wired in the AI controller
            raw = self._call_ai(prompt)
            data = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception as e:  # noqa: BLE001
            _logger.warning("AI rewrite failed for %s: %s", self.id, e)
            raise UserError(_("AI rewrite failed: %s") % e)
        return data

    def _call_ai(self, prompt):
        """Call Claude via the uellow_ai_engine credentials (returns raw text).

        Uses the same API key + model the Beena engine stores under
        ``uellow_ai.*``. Prefers an ``uellow.ai.claude`` helper model if one is
        ever added, else talks to the Anthropic Messages API directly so the
        AI buttons work without a separate bridge.
        """
        Claude = self.env.get('uellow.ai.claude')
        if Claude is not None and hasattr(Claude, 'complete_json'):
            return Claude.complete_json(prompt)
        import urllib.request
        import urllib.error
        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('uellow_ai.claude_api_key') or ''
        model = ICP.get_param('uellow_ai.claude_model') or 'claude-sonnet-4-6'
        if not api_key:
            raise UserError(_("No Claude API key configured (Beena AI settings)."))
        payload = json.dumps({
            'model': model,
            'max_tokens': 400,
            'messages': [{'role': 'user', 'content': prompt}],
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.anthropic.com/v1/messages', data=payload, headers={
                'Content-Type': 'application/json',
                'x-api-key': api_key,
                'anthropic-version': '2023-06-01',
            })
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            raise UserError(_("Claude API error %s: %s")
                            % (e.code, e.read().decode()[:200]))
        except Exception as e:  # noqa: BLE001
            raise UserError(_("Claude request failed: %s") % e)
        # concatenate the text blocks of the response
        parts = body.get('content') or []
        text = ''.join(b.get('text', '') for b in parts if isinstance(b, dict))
        # tolerate ```json fences the model sometimes adds
        text = re.sub(r'^```(?:json)?|```$', '', (text or '').strip(),
                      flags=re.MULTILINE).strip()
        return text
