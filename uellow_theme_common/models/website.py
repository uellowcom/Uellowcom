# -*- coding: utf-8 -*-
# Copyright (c) 2019-Present Droggol Infotech Private Limited. (<https://www.droggol.com/>)

from odoo import _, api, fields, models
from odoo.http import request
from odoo.osv import expression
from odoo.tools.translate import html_translate

class Website(models.Model):
    _inherit = 'website'

    dr_sale_special_offer = fields.Html('Sale Special Offer', sanitize_attributes=False, translate=html_translate, sanitize_form=False)

    dr_product_tab_ids = fields.Many2many('dr.website.content', 'website_product_tab_rel', 'website_id', 'tab_id', string='Product Tabs')
    dr_product_info_ids = fields.Many2many('dr.website.content', 'website_product_info_rel', 'website_id', 'info_id', string='Product Info')

    dr_pwa_activated = fields.Boolean('PWA Activated')
    dr_pwa_name = fields.Char('PWA Name')
    dr_pwa_short_name = fields.Char('PWA Short Name')
    dr_pwa_background_color = fields.Char('PWA Background Color', default='#000000')
    dr_pwa_theme_color = fields.Char('PWA Theme Color', default='#FFFFFF')
    dr_pwa_icon_192 = fields.Binary('PWA Icon 192x192')
    dr_pwa_icon_512 = fields.Binary('PWA Icon 512x512')
    dr_pwa_start_url = fields.Char('PWA Start URL', default='/shop')
    dr_pwa_offline_page = fields.Boolean('PWA Offline Page')
    dr_pwa_version = fields.Integer('PWA Version')
    dr_pwa_screenshots = fields.One2many('dr.pwa.screenshots', 'website_id', string='Screenshots')
    dr_pwa_shortcuts = fields.One2many('dr.pwa.shortcuts', 'website_id', string='Shortcuts')
    dr_pwa_show_install_banner = fields.Boolean('PWA Show Install Banner', default=True)

    # ─── Uellow Theme — branding & header ──────────────────────────────
    # Per-website settings so each storefront (Uellow KW / SA / UAE …) can
    # carry its own logo, brand colours and welcome strap line without any
    # code edits in the future. All fields are surfaced from the standard
    # Website > Configuration > Settings page, under a "Uellow Theme" block.

    uc_logo_height = fields.Integer(
        'Logo Height (px)', default=40,
        help='Pixel height of the brand logo inside the main header bar. '
             'The width is computed proportionally. Range 24-80 looks best.')
    uc_logo_mobile = fields.Binary(
        'Mobile Logo',
        help='Smaller version of the logo used in the mobile header. '
             'Falls back to the regular website logo when empty.')
    uc_favicon = fields.Binary(
        'Favicon Override',
        help='Optional override for the browser tab icon. When empty the '
             'standard website favicon is used.')

    uc_header_bg = fields.Char(
        'Header Background', default='#131921',
        help='Hex colour for the dark top utility bar and main header. '
             'Default #131921 matches the marketplace look.')
    uc_header_yellow = fields.Char(
        'Header Accent (Yellow)', default='#F5C320',
        help='Hex colour for buttons, hover states and the Uellow brand '
             'accent. Default #F5C320 matches the Uellow logo.')

    uc_preheader_text = fields.Char(
        'Preheader Welcome Text', translate=True,
        default='Free shipping on orders above 15 KWD',
        help='Short message shown in the top utility bar of the header.')
    uc_preheader_phone = fields.Char(
        'Support Phone', default='1880-880',
        help='Phone number shown next to the welcome text.')
    uc_search_placeholder = fields.Char(
        'Search Bar Placeholder', translate=True,
        default='Search for products, brands and more...',
        help='Placeholder text inside the main header search input.')
    uc_trending_terms = fields.Char(
        'Trending Search Terms', translate=True,
        default='Smart Watch, Headphones, Perfume, Smart TV, AirPods, Laptop',
        help='Comma-separated list of trending search terms shown under '
             'the main search bar. Each becomes a clickable suggestion. '
             'About 6 terms reads best.')

    # ─── Today's Deals promo (in the catbar) ───────────────────────────
    uc_deals_active = fields.Boolean(
        "Show Deals Promo", default=True,
        help="Toggle the small promo pill at the end of the category bar.")
    uc_deals_label = fields.Char(
        "Deals Label", translate=True, default="Today's Deals",
        help="Text shown on the promo pill.")
    uc_deals_icon = fields.Char(
        "Deals Icon", default="fa-bolt",
        help="Font Awesome icon name (without the `fa fa-` prefix). "
             "Examples: fa-bolt, fa-fire, fa-percent, fa-tag.")
    uc_deals_target_type = fields.Selection(
        [('category', 'Product Category'),
         ('tag',      'Product Tag'),
         ('page',     'Website Page'),
         ('url',      'Custom URL'),
         ('search',   'Search Query')],
        string="Deals Target Type", default='search',
        help="What the deals pill links to.")
    uc_deals_category_id = fields.Many2one(
        'product.public.category', string="Deals Category",
        ondelete='set null')
    uc_deals_tag_id = fields.Many2one(
        'product.tag', string="Deals Tag",
        ondelete='set null')
    uc_deals_page_id = fields.Many2one(
        'website.page', string="Deals Page",
        ondelete='set null')
    uc_deals_url = fields.Char(
        "Deals URL",
        help="Used when target type is Custom URL.")
    uc_deals_query = fields.Char(
        "Deals Search Query", default="deals",
        help="Used when target type is Search Query — the value passed to /shop?search=…")

    # ─── Footer settings — app stores + copy ───────────────────────────
    uc_app_ios_url = fields.Char(
        "App Store URL",
        default="https://apps.apple.com/",
        help="iOS App Store link shown in the footer + preheader app card.")
    uc_app_android_url = fields.Char(
        "Google Play URL",
        default="https://play.google.com/",
        help="Google Play link shown in the footer + preheader app card.")
    uc_app_huawei_url = fields.Char(
        "AppGallery URL",
        help="Optional Huawei AppGallery link. Empty = badge hidden.")

    # ─── App-download popup (v2.2.46) ──────────────────────────────────
    uc_app_popup_enabled = fields.Boolean(
        "Show App-Download Popup", default=True,
        help="A polished centred popup inviting site visitors to install "
             "the Uellow app. Shown once per visit (per session).")
    uc_app_popup_delay = fields.Integer(
        "Popup Delay (seconds)", default=4,
        help="How long after the page loads before the popup appears.")
    uc_app_popup_title = fields.Char(
        "Popup Title", translate=True, default="Get the Uellow app",
        help="Headline of the app-download popup.")
    uc_app_popup_text = fields.Char(
        "Popup Subtitle", translate=True,
        default="Shop faster, track orders live and earn points — "
                "all in one app.",
        help="Supporting line under the popup headline.")

    # ─── App-download smart banner (sticky bar above the header) ───────
    uc_app_banner_enabled = fields.Boolean(
        "Show App-Download Banner", default=True,
        help="A slim sticky bar above the header inviting visitors to "
             "open/install the Uellow app. Dismissible for 7 days.")
    uc_app_banner_devices = fields.Selection(
        [('both', 'Mobile + Desktop'),
         ('mobile', 'Mobile only'),
         ('desktop', 'Desktop only')],
        string="Banner shows on", default='both',
        help="Which devices see the smart banner.")
    uc_app_banner_frequency = fields.Selection(
        [('always', 'Every visit'),
         ('daily', 'Once a day'),
         ('weekly', 'Once a week'),
         ('once', 'Once ever')],
        string="Banner frequency", default='daily',
        help="How often a returning visitor sees the banner again.")
    uc_app_banner_dismiss_days = fields.Integer(
        "Hide after dismiss (days)", default=7,
        help="When a visitor closes the banner, hide it for this many days.")
    uc_app_banner_ios_smart = fields.Boolean(
        "Use iOS native Smart Banner", default=True,
        help="On iOS Safari, show Apple's native Smart App Banner instead of "
             "the custom bar. It auto-hides if the app is already installed "
             "and deep-links the current page into the app.")

    uc_footer_about = fields.Text(
        "Footer About Text", translate=True,
        default="Curated marketplace for the Gulf — premium brands, "
                "fast delivery, exclusive deals.",
        help="Short brand description shown in the first column of the "
             "footer.")
    uc_footer_credit = fields.Char(
        "Footer Credit Line", translate=True,
        default="Built with care in Kuwait",
        help="Optional small line on the right of the copyright row.")
    uc_footer_newsletter_intro = fields.Char(
        "Newsletter Intro", translate=True,
        default="Faster checkout, member-only deals, instant order updates.",
        help="Short pitch above the newsletter input.")

    # ─── Per-website footer policy links ───────────────────────────────
    uc_policy_privacy_url = fields.Char(
        "Privacy URL", default="/page/privacy",
        help="Footer 'Privacy' link target for THIS storefront.")
    uc_policy_terms_url = fields.Char(
        "Terms URL", default="/page/terms",
        help="Footer 'Terms' link target for THIS storefront.")
    uc_policy_cookies_url = fields.Char(
        "Cookies URL", default="/page/cookies",
        help="Footer 'Cookies' link target for THIS storefront.")
    uc_policy_accessibility_url = fields.Char(
        "Accessibility URL", default="/page/accessibility",
        help="Footer 'Accessibility' link target for THIS storefront.")

    # ─── Beena AI mobile-nav icon override ──────────────────────────────
    uc_beena_icon = fields.Binary(
        "Beena Custom Icon",
        help="Optional PNG/SVG shown inside the mobile nav Beena disc "
             "instead of the default magic-wand icon. 1:1 transparent "
             "image works best.")

    # ─── Uellow Theme — header helpers ─────────────────────────────────

    @api.model
    def _uc_country_flag(self, code):
        """Return the regional-indicator flag emoji for a 2-letter ISO code.

        QWeb has no way to compose flag emojis from text, so this helper
        does the chr() arithmetic Python-side and the template just calls
        `website._uc_country_flag(partner.country_id.code)`. Falls back to
        a globe for unknown codes — never raises.
        """
        if not code or len(code) != 2 or not code.isalpha():
            return '\U0001F310'   # 🌐
        base = 0x1F1E6
        return chr(base + ord(code[0].upper()) - ord('A')) + \
               chr(base + ord(code[1].upper()) - ord('A'))

    # ─── Header UI labels — multi-language ─────────────────────────────
    # We expose a small inline phrasebook so the header speaks the user's
    # language out of the box, even before anyone exports .po files.
    # The fallback path still calls Odoo's gettext, so the user can OVERRIDE
    # or extend translations via the Translations app and they win.
    _UC_PHRASEBOOK = {
        'ar_001': {
            'Get the App':         'حمّل التطبيق',
            'Ship to':             'الشحن إلى',
            'Sign in':             'تسجيل الدخول',
            'Help':                'مساعدة',
            'Deliver to':          'التوصيل إلى',
            'Delivery destination':'وجهة التوصيل',
            'Switch to a saved address':'اختر عنوان محفوظ',
            'Manage addresses':    'إدارة العناوين',
            'Sign in to deliver':  'سجّل الدخول للتوصيل',
            'Choose your Uellow storefront':'اختر متجر Uellow',
            'Currency & prices update per storefront.':
                'العملة والأسعار تتغير حسب المتجر.',
            'Scan to install':     'مسح للتثبيت',
            'Uellow App':          'تطبيق Uellow',
            'Shop faster, exclusive deals, order tracking — all in your pocket.':
                'تسوّق أسرع، عروض حصرية، تتبع الطلبات — كل ذلك في جيبك.',
            'Search':              'بحث',
            'Trending':            'الأكثر بحثاً',
            'Ask':                 'اسأل',
            'Account':             'حسابي',
            'Your':                'قائمة',
            'Wishlist':            'المفضلة',
            'My':                  'سلتي',
            'Cart':                'السلة',
            'item':                'منتج',
            'items':               'منتجات',
            'Hello,':              'مرحباً،',
            'All Categories':      'كل الأقسام',
            'Today\'s Deals':      'عروض اليوم',
            'Shop':                'تسوق',
            'View all':            'عرض الكل',
            'Top brands':          'أبرز العلامات',
            'Browse the full collection':'تصفح المجموعة كاملة',
            'Featured':            'مميز',
            'Discover handpicked deals on':'اكتشف أفضل العروض على',
            'Shop now':            'تسوق الآن',
            'Register':            'تسجيل عضوية',
            'Email':               'البريد الإلكتروني',
            'Password':            'كلمة المرور',
            'Forgot password?':    'هل نسيت كلمة المرور؟',
            'Create account':      'إنشاء حساب',
            'Create your free Uellow account to track orders, save favourites and unlock member-only deals.':
                'أنشئ حساب Uellow مجاناً لتتبّع طلباتك، حفظ المفضلة، وعروض حصرية للأعضاء.',
            'Already a member? Switch to the Sign in tab.':
                'لديك حساب؟ افتح تبويب تسجيل الدخول.',
            'Create your Uellow account': 'إنشاء حساب Uellow',
            'Your cart':           'سلة المشتريات',
            'Loading your cart…':  'جارٍ تحميل سلتك…',
            'Open full cart':      'فتح السلة كاملة',
            'Checkout':            'إتمام الشراء',
            'Menu':                'القائمة',
            'or continue with':    'أو تابع باستخدام',
            'or sign up with':     'أو سجّل باستخدام',
            'Dashboard':           'لوحة الحساب',
            'My orders':           'طلباتي',
            'Invoices':            'الفواتير',
            'Support tickets':     'تذاكر الدعم',
            'Loyalty points':      'نقاط الولاء',
            'Addresses':           'العناوين',
            'Settings':            'الإعدادات',
            'Sign out':            'تسجيل الخروج',
            'Search for products, brands and more...':
                'ابحث عن منتجات وعلامات وأكثر…',
            # Footer
            'Secure payment':      'دفع آمن',
            'SSL encrypted checkout':'إتمام شراء مشفر SSL',
            'Free delivery':       'توصيل مجاني',
            'On qualifying orders':'على الطلبات المؤهلة',
            'Easy returns':        'استرجاع سهل',
            '14-day hassle-free returns':'استرجاع بدون متاعب خلال 14 يوم',
            '24/7 support':        'دعم 24/7',
            'Real humans, always on':'بشر حقيقيون، متاحون دائماً',
            'Faster shopping, better deals':'تسوّق أسرع وعروض أفضل',
            'Curated marketplace for the Gulf — premium brands, fast delivery, exclusive deals.':
                'متجر منتقى للخليج — علامات فاخرة، توصيل سريع، عروض حصرية.',
            'My account':          'حسابي',
            'Customer service':    'خدمة العملاء',
            'Contact us':          'تواصل معنا',
            'FAQ':                 'الأسئلة الشائعة',
            'Shipping & delivery': 'الشحن والتوصيل',
            'Returns & refunds':   'الاسترجاع والاسترداد',
            'Track my order':      'تتبع طلبي',
            'Discover':            'اكتشف',
            'All categories':      'كل الأقسام',
            'New arrivals':        'الجديد',
            'Blog':                'المدوّنة',
            'About Uellow':        'عن Uellow',
            'Careers':             'الوظائف',
            'Partners Program':    'برنامج الشركاء — اربح مع يلو',
            'Download the Uellow App': 'حمّل تطبيق يلو',
            'Faster checkout, member-only deals, instant order updates.':
                'إتمام شراء أسرع، عروض للأعضاء، إشعارات فورية بحالة الطلب.',
            'Download on the':     'حمّل من',
            'App Store':           'App Store',
            'Get it on':           'احصل عليه من',
            'Google Play':         'Google Play',
            'Newsletter':          'النشرة البريدية',
            'Email address':       'البريد الإلكتروني',
            'Subscribe':           'اشتراك',
            'We accept':           'نقبل',
            'All rights reserved.':'جميع الحقوق محفوظة.',
            'Privacy':             'الخصوصية',
            'Terms':               'الشروط',
            'Cookies':             'الكوكيز',
            'Accessibility':       'سهولة الوصول',
            'Built with care in Kuwait':'صُنع بعناية في الكويت',
            # Mobile bottom nav
            'Home':                'الرئيسية',
            'Shop':                'تسوق',
            'Beena':               'بينا',
            'Open Beena AI':       'افتح بينا',
            'Add to cart':         'أضف للسلة',
            'Fast buy':            'شراء سريع',
            'My cart':             'سلتي',
        },
        'fr_FR': {
            'Get the App':         "Télécharger l'app",
            'Ship to':             'Livrer à',
            'Sign in':             'Connexion',
            'Help':                'Aide',
            'Deliver to':          'Livrer à',
            'Delivery destination':'Destination de livraison',
            'Switch to a saved address':'Choisir une adresse enregistrée',
            'Manage addresses':    'Gérer les adresses',
            'Sign in to deliver':  'Connectez-vous pour livrer',
            'Choose your Uellow storefront':'Choisissez votre boutique Uellow',
            'Currency & prices update per storefront.':
                'Les devises et prix changent selon la boutique.',
            'Scan to install':     'Scanner pour installer',
            'Uellow App':          'App Uellow',
            'Shop faster, exclusive deals, order tracking — all in your pocket.':
                'Achetez plus vite, offres exclusives, suivi des commandes — dans votre poche.',
            'Search':              'Rechercher',
            'Trending':            'Tendances',
            'Ask':                 'Demander',
            'Account':             'Compte',
            'Your':                'Votre',
            'Wishlist':            'Favoris',
            'My':                  'Mon',
            'Cart':                'Panier',
            'item':                'article',
            'items':               'articles',
            'Hello,':              'Bonjour,',
            'All Categories':      'Toutes les catégories',
            'Today\'s Deals':      "Offres du jour",
            'Shop':                'Acheter',
            'View all':            'Tout voir',
            'Top brands':          'Marques phares',
            'Browse the full collection':'Voir toute la collection',
            'Featured':            'En vedette',
            'Discover handpicked deals on':'Découvrez les offres sur',
            'Shop now':            'Acheter',
            'Register':            "S'inscrire",
            'Email':               'Email',
            'Password':            'Mot de passe',
            'Forgot password?':    'Mot de passe oublié ?',
            'Create account':      'Créer un compte',
            'Create your free Uellow account to track orders, save favourites and unlock member-only deals.':
                'Créez votre compte Uellow gratuit pour suivre les commandes, enregistrer vos favoris et débloquer des offres membres.',
            'Already a member? Switch to the Sign in tab.':
                'Déjà membre ? Passez à l’onglet Connexion.',
            'Create your Uellow account': 'Créez votre compte Uellow',
            'Your cart':           'Votre panier',
            'Loading your cart…':  'Chargement du panier…',
            'Open full cart':      'Ouvrir le panier complet',
            'Checkout':            'Commander',
            'Menu':                'Menu',
            'or continue with':    'ou continuer avec',
            'or sign up with':     "ou s'inscrire avec",
            'Dashboard':           'Tableau de bord',
            'My orders':           'Mes commandes',
            'Invoices':            'Factures',
            'Support tickets':     'Tickets de support',
            'Loyalty points':      'Points fidélité',
            'Addresses':           'Adresses',
            'Settings':            'Paramètres',
            'Sign out':            'Déconnexion',
            'Search for products, brands and more...':
                'Recherchez produits, marques et plus…',
            # Footer
            'Secure payment':      'Paiement sécurisé',
            'SSL encrypted checkout':'Paiement chiffré SSL',
            'Free delivery':       'Livraison gratuite',
            'On qualifying orders':'Sur les commandes éligibles',
            'Easy returns':        'Retours faciles',
            '14-day hassle-free returns':'Retours sans souci sous 14 jours',
            '24/7 support':        'Support 24/7',
            'Real humans, always on':'De vraies personnes, toujours disponibles',
            'Faster shopping, better deals':'Achats plus rapides, meilleures offres',
            'Curated marketplace for the Gulf — premium brands, fast delivery, exclusive deals.':
                'Marketplace soigneusement sélectionnée pour le Golfe — marques premium, livraison rapide, offres exclusives.',
            'My account':          'Mon compte',
            'Customer service':    'Service client',
            'Contact us':          'Nous contacter',
            'FAQ':                 'FAQ',
            'Shipping & delivery': 'Expédition et livraison',
            'Returns & refunds':   'Retours et remboursements',
            'Track my order':      'Suivre ma commande',
            'Discover':            'Découvrir',
            'All categories':      'Toutes les catégories',
            'New arrivals':        'Nouveautés',
            'Blog':                'Blog',
            'About Uellow':        'À propos de Uellow',
            'Careers':             'Carrières',
            'Partners Program':    'Programme Partenaires',
            'Download the Uellow App': "Télécharger l'app Uellow",
            'Faster checkout, member-only deals, instant order updates.':
                'Paiement plus rapide, offres membres, mises à jour instantanées.',
            'Download on the':     'Télécharger sur',
            'App Store':           'App Store',
            'Get it on':           'Disponible sur',
            'Google Play':         'Google Play',
            'Newsletter':          'Newsletter',
            'Email address':       'Adresse email',
            'Subscribe':           "S'abonner",
            'We accept':           'Nous acceptons',
            'All rights reserved.':'Tous droits réservés.',
            'Privacy':             'Confidentialité',
            'Terms':               'Conditions',
            'Cookies':             'Cookies',
            'Accessibility':       'Accessibilité',
            'Built with care in Kuwait':'Fait avec soin au Koweït',
            # Mobile bottom nav
            'Home':                'Accueil',
            'Shop':                'Boutique',
            'Beena':               'Beena',
            'Open Beena AI':       'Ouvrir Beena',
            'Add to cart':         'Ajouter au panier',
            'Fast buy':            'Achat rapide',
            'My cart':             'Mon panier',
        },
    }

    @api.model
    def _uc_t(self, key):
        """Translate a header label to the current request language.

        Resolution order:
          1. Odoo's standard gettext (so users who export .po always win).
          2. The inline phrasebook above (ships with AR + FR by default,
             matched first by full code, then by 2-letter prefix so 'ar'
             still hits the 'ar_001' bucket).
          3. The English key as-is.
        """
        try:
            translated = self.env._(key)
            if translated and translated != key:
                return translated
        except Exception:
            pass
        # Collect candidate lang codes in preference order.
        candidates = []
        try:
            from odoo.http import request
            if request is not None:
                lang = getattr(request, 'lang', None)
                if lang and getattr(lang, 'code', None):
                    candidates.append(lang.code)
                ctx_lang = (request.context or {}).get('lang')
                if ctx_lang:
                    candidates.append(ctx_lang)
        except Exception:
            pass
        candidates.append(self.env.context.get('lang'))
        if self.env.user:
            candidates.append(self.env.user.lang)
        # Match: exact first, then 2-letter prefix.
        for cand in candidates:
            if not cand:
                continue
            if cand in self._UC_PHRASEBOOK:
                return self._UC_PHRASEBOOK[cand].get(key, key)
            head = cand[:2]
            for bucket in self._UC_PHRASEBOOK:
                if bucket.startswith(head):
                    return self._UC_PHRASEBOOK[bucket].get(key, key)
        return key

    def _uc_category_brands(self, category, limit=8):
        """Return brand attribute values that appear on this category's
        published products. Falls back to global brands when the category
        has no branded inventory (so the menu never looks empty)."""
        if not category:
            return self._get_brands(limit=limit)
        brand_attr_ids = self._get_brand_attributes().ids
        if not brand_attr_ids:
            return self.env['product.attribute.value']
        Product = self.env['product.template'].sudo()
        products = Product.search([
            ('public_categ_ids', 'child_of', category.id),
            ('is_published', '=', True),
            ('website_id', 'in', [False, self.id]),
        ])
        if not products:
            return self._get_brands(limit=limit)
        values = products.mapped('attribute_line_ids.value_ids').filtered(
            lambda v: v.attribute_id.id in brand_attr_ids
        )
        if not values:
            return self._get_brands(limit=limit)
        return values[:limit]

    # Maps each storefront name to a 2-letter ISO code used by flagcdn.com,
    # so the Ship-To dropdown can render PNG flags instead of emoji that not
    # every browser/OS supports.
    _UC_SITE_CODES = {
        'Uellow Us':       'us',
        'Uellow Saudia':   'sa',
        'Uellow Egypt':    'eg',
        'Uellow Qatar':    'qa',
        'Uellow UAE':      'ae',
        'Uellow Kuwait':   'kw',
        'Uellow Oman':     'om',
    }

    @api.model
    def _uc_site_code(self, name):
        """Return the 2-letter code for a storefront name (or '' for global)."""
        return self._UC_SITE_CODES.get((name or '').strip(), '')

    # Storefront country names per language (the "Choose your Uellow
    # storefront" dialog showed the raw English name in the Arabic UI).
    _UC_SITE_NAMES_EN = {
        'us': 'United States', 'sa': 'Saudi Arabia', 'eg': 'Egypt',
        'qa': 'Qatar', 'ae': 'United Arab Emirates', 'kw': 'Kuwait', 'om': 'Oman',
    }
    _UC_SITE_NAMES_AR = {
        'us': 'الولايات المتحدة', 'sa': 'السعودية', 'eg': 'مصر',
        'qa': 'قطر', 'ae': 'الإمارات', 'kw': 'الكويت', 'om': 'عُمان',
    }

    @api.model
    def _uc_is_arabic(self):
        """True when the current request/user language is Arabic."""
        try:
            from odoo.http import request
            lang = ''
            if request is not None and getattr(request, 'lang', None):
                lang = getattr(request.lang, 'code', '') or ''
            lang = lang or self.env.context.get('lang') or \
                (self.env.user.lang if self.env.user else '') or ''
            return lang.startswith('ar')
        except Exception:
            return (self.env.context.get('lang') or '').startswith('ar')

    @api.model
    def _uc_country_name(self, name):
        """Translated storefront/country display name for the store switcher."""
        is_ar = self._uc_is_arabic()
        code = self._uc_site_code(name)
        if code:
            table = self._UC_SITE_NAMES_AR if is_ar else self._UC_SITE_NAMES_EN
            return table.get(code) or (name or '').replace('Uellow', '').strip()
        base = (name or '').replace('Uellow', '').strip()
        if not base:
            return 'عالمي' if is_ar else 'Global'
        return base

    def _uc_deals_resolve(self):
        """Return {label, icon, url} for the Today's Deals promo pill.

        Routes by `uc_deals_target_type`: category, tag, page, custom URL,
        or a search query fallback. Returns None when the merchant has
        toggled the pill off, so the template skips rendering entirely.
        """
        self.ensure_one()
        if not self.uc_deals_active:
            return None
        t = self.uc_deals_target_type or 'search'
        url = '/shop?search=deals'
        if t == 'category' and self.uc_deals_category_id:
            url = '/shop/category/%s' % self.uc_deals_category_id.id
        elif t == 'tag' and self.uc_deals_tag_id:
            url = '/shop?tags=%s' % self.uc_deals_tag_id.id
        elif t == 'page' and self.uc_deals_page_id:
            url = self.uc_deals_page_id.url or '/'
        elif t == 'url' and self.uc_deals_url:
            url = self.uc_deals_url
        elif t == 'search':
            q = (self.uc_deals_query or 'deals').replace(' ', '+')
            url = '/shop?search=%s' % q
        return {
            'label': self.uc_deals_label or self._uc_t("Today's Deals"),
            'icon':  (self.uc_deals_icon or 'fa-bolt').strip(),
            'url':   url,
        }

    def _uc_socials(self):
        """List of {icon, url, label} for footer social row — only fields
        actually filled in on the website are returned."""
        fields_map = [
            ('social_facebook',  'facebook',  'Facebook'),
            ('social_instagram', 'instagram', 'Instagram'),
            ('social_twitter',   'x',         'X'),
            ('social_youtube',   'youtube',   'YouTube'),
            ('social_tiktok',    'tiktok',    'TikTok'),
            ('social_linkedin',  'linkedin',  'LinkedIn'),
            ('social_github',    'github',    'GitHub'),
        ]
        out = []
        for fname, icon, label in fields_map:
            val = getattr(self, fname, None)
            if val:
                out.append({'icon': icon, 'url': val, 'label': label})
        return out

    # Crisp brand-logo SVGs (Simple Icons paths, 24-grid, currentColor) so the
    # footer social row uses real, professional platform logos instead of the
    # generic Font Awesome glyphs (TikTok had a music note, X showed the old
    # Twitter bird).
    _UC_SOCIAL_PATHS = {
        'facebook': 'M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z',
        'instagram': 'M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z',
        'x': 'M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z',
        'youtube': 'M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z',
        'tiktok': 'M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z',
        'linkedin': 'M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z',
        'github': 'M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12',
    }

    @api.model
    def _uc_social_svg(self, slug):
        """Inline brand SVG (Markup) for a social slug — empty for unknown."""
        from markupsafe import Markup
        path = self._UC_SOCIAL_PATHS.get(slug or '')
        if not path:
            return Markup('')
        return Markup(
            '<svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" '
            'aria-hidden="true" focusable="false"><path d="%s"/></svg>' % path)

    def _uc_free_ship_line(self):
        """Per-website free-shipping strap line, sourced from the LIVE
        free-shipping engine (uellow.freeship.rule.bar_threshold) so the
        header label always matches the actual threshold for THIS storefront
        / country. Falls back to the static uc_preheader_text if no cart-scope
        free-ship rule applies. Returns a string or '' ."""
        self.ensure_one()
        try:
            amount = self.env['uellow.freeship.rule'].sudo().bar_threshold()
        except Exception:
            amount = None
        if not amount:
            return self.uc_preheader_text or ''
        cur = self.sudo().company_id.currency_id
        code = (cur.name if cur else '') or 'KWD'
        amt = ('%.0f' % amount) if float(amount).is_integer() else ('%.3f' % amount)
        ar = (self.env.context.get('lang') or '').startswith('ar')
        if ar:
            return 'شحن مجاني للطلبات فوق %s %s' % (amt, code)
        return 'Free shipping on orders above %s %s' % (amt, code)

    def _uc_trending_list(self, limit=8):
        """Trending search terms for the header — sourced from the SAME live
        data the mobile app uses (mobile.search.analytic). Falls back to the
        static uc_trending_terms field when analytics are empty (new sites)."""
        self.ensure_one()
        terms = []
        Model = self.env.get('mobile.search.analytic')
        if Model is not None:
            try:
                rows = Model.sudo().get_top_keywords(limit=limit, days=7)
                terms = [(r.get('keyword') or '').strip() for r in rows
                         if (r.get('keyword') or '').strip()]
            except Exception:
                terms = []
        if not terms:
            terms = [t.strip() for t in (self.uc_trending_terms or '').split(',')
                     if t.strip()]
        return terms[:limit]

    def _uc_footer_links(self, code):
        """Per-website editable footer column. Returns [{name,url}] from the
        children of the '/uc-footer/<code>' container menu under the site's
        separate 'UC Footer' root (NOT website.menu_id, so these never appear
        in the header nav). Empty list ⇒ the template renders its built-in
        static links (so untouched sites are unchanged)."""
        self.ensure_one()
        Menu = self.env['website.menu'].sudo()
        container = Menu.search([
            ('url', '=', '/uc-footer/%s' % code),
            ('website_id', 'in', [self.id, False]),
        ], limit=1)
        if not container:
            return []
        out = []
        for m in container.child_id.sorted('sequence'):
            out.append({'name': m.name, 'url': m.url or '#'})
        return out

    def _uc_live_flash(self):
        """The live flash sale for THIS storefront (mobile.flash.sale), used to
        drive the header's red 'deals' card — real title, real countdown to the
        sale's end_date, links to /flash-deals. Returns a dict compatible with
        _uc_deals_resolve() (label/icon/url) plus an ISO 'end', or None so the
        template falls back to the configured Today's-Deals pill."""
        self.ensure_one()
        Model = self.env.get('mobile.flash.sale')
        if Model is None:
            return None
        try:
            sales = Model.sudo().search(
                [('active', '=', True), ('website_id', 'in', [False, self.id])],
                order='sequence asc')
            ar = (self.env.context.get('lang') or '').startswith('ar')
            for s in sales:
                if not getattr(s, 'is_live', False):
                    continue
                label = (getattr(s, 'name_ar', '') if ar else '') or s.name or 'Flash Sale'
                end_iso = ''
                if s.end_date:
                    end_iso = fields.Datetime.to_string(s.end_date).replace(' ', 'T') + 'Z'
                return {'label': label, 'icon': 'fa-bolt',
                        'url': '/flash-deals', 'end': end_iso}
        except Exception:
            return None
        return None

    def _uc_oauth_buttons(self):
        """Return the enabled OAuth providers, mapped to compact display
        info for the header's auth popover. Each entry has:

          {id, label, icon, url}

        `icon` matches a Font Awesome name (`google`, `facebook`, `apple`,
        `sign-in`). When the provider has its own auth URL helper that
        works in our Odoo build, we expose that; otherwise the user lands
        on `/web/login`, where Odoo's standard OAuth buttons take over.
        """
        Provider = self.env.get('auth.oauth.provider')
        if Provider is None:
            return []
        out = []
        for p in Provider.sudo().search([('enabled', '=', True)]):
            lname = (p.name or '').lower()
            if 'google' in lname:
                icon = 'google'
            elif 'facebook' in lname:
                icon = 'facebook'
            elif 'apple' in lname:
                icon = 'apple'
            elif 'microsoft' in lname or 'azure' in lname:
                icon = 'windows'
            else:
                icon = 'sign-in'
            url = '/web/login'
            # Best-effort: when the provider exposes an auth URL builder,
            # link straight to the consent screen.
            for attr in ('_get_oauth_url', '_auth_oauth_url', '_get_oauth_signin_url'):
                fn = getattr(p, attr, None)
                if callable(fn):
                    try:
                        candidate = fn()
                        if candidate:
                            url = candidate
                            break
                    except Exception:
                        pass
            out.append({
                'id':    p.id,
                'label': p.name,
                'icon':  icon,
                'url':   url,
            })
        return out

    def _uc_storefronts(self):
        """Customer-facing storefronts for the Ship-To dropdown.

        Excludes anything whose name contains 'Mobile' or 'Mobil'
        (handles the existing 'Oman Mobil App' typo) and the B2B portal —
        those are not destinations a regular shopper would switch to.
        """
        return self.sudo().search([
            ('name', 'not ilike', 'Mobil'),
            ('name', 'not ilike', 'B2B'),
        ], order='name')

    def _uc_current_delivery(self):
        """Resolve a 'deliver to' summary for the header chip.

        Logged-in users with at least one saved address → return a dict
        describing it (city / country / full label / id). Otherwise fall
        back to the current storefront's country so guests still see a
        sensible 'Deliver to: 🇰🇼 Kuwait' chip instead of an empty one.

        Shape:
          {
            'kind': 'partner' | 'storefront',
            'city': str,
            'country_code': str,    # 2-letter ISO
            'country_name': str,
            'flag': str,            # emoji
            'short': str,           # what shows on the chip
            'full': str,            # full address one-liner
            'partner_id': int,      # 0 if guest
          }
        """
        self.ensure_one()
        user = self.env.user
        if not user._is_public():
            p = user.partner_id
            if p.country_id or p.city:
                code = (p.country_id.code or '').upper()
                return {
                    'kind': 'partner',
                    'city': p.city or '',
                    'country_code': code,
                    'country_name': p.country_id.name or '',
                    'flag': self._uc_country_flag(code),
                    'short': p.city or p.country_id.name or 'Address',
                    'full': ', '.join(filter(None, [
                        p.street, p.street2, p.city,
                        p.state_id.name, p.country_id.name,
                    ])),
                    'partner_id': p.id,
                }
        # Guest fallback: use the storefront's country if known
        c = self.company_id.country_id or self.env.user.company_id.country_id
        code = (c.code or '').upper() if c else ''
        return {
            'kind': 'storefront',
            'city': '',
            'country_code': code,
            'country_name': c.name if c else '',
            'flag': self._uc_country_flag(code),
            'short': (c.name if c else 'Select'),
            'full': 'Sign in to deliver to your address',
            'partner_id': 0,
        }

    def _uc_user_addresses(self):
        """Return the current user's saved delivery addresses (max 6)."""
        if self.env.user._is_public():
            return self.env['res.partner']
        partner = self.env.user.partner_id
        return self.env['res.partner'].sudo().search([
            '|', ('id', '=', partner.id),
                 '&', ('parent_id', '=', partner.id),
                      ('type', 'in', ('delivery', 'contact', 'other')),
        ], limit=6)

    def _get_brands(self, domain=[], limit=None, order=None):
        brand_attributes = self._get_brand_attributes().ids
        domain = expression.AND([domain, [('attribute_id', 'in', brand_attributes)]])
        return self.env['product.attribute.value'].search(domain, limit=limit, order=order)

    def _dr_has_b2b_access(self, record=None):
        if self._get_dr_theme_config('json_b2b_shop_config')['dr_enable_b2b']:
            return not self.env.user.has_group('base.group_public')
        return True

    def _get_brand_attributes(self):
        """ This will preserver the sequence """
        website = self or request.website
        # perf — this is called many times per storefront render (the theme's
        # QWeb t-cache around the brand filter misses constantly). The old code
        # materialised the ENTIRE published catalogue (~3.5k templates) into a
        # Python recordset and passed all their ids as a giant IN(...) on every
        # call. Use a subquery (`_search` → Query) so it's a single cheap SQL
        # with identical semantics (always live, no staleness).
        product_query = self.env['product.template'].sudo()._search(
            website.sale_product_domain())
        return self.env['product.attribute'].search(
            [('product_tmpl_ids', 'in', product_query), ('dr_is_brand', '=', True)])

    def get_dr_theme_config(self):
        return self._get_dr_theme_config()

    def _get_dr_theme_config(self, key=False):
        """ See dr.theme.config for more info"""
        self.ensure_one()
        website_config = self.env['dr.theme.config']._get_all_config(self.id)
        website_config['is_public_user'] = not self.env.user.has_group('website.group_website_restricted_editor')
        website_config['has_sign_up'] = False
        if website_config.get('json_b2b_shop_config')['dr_enable_b2b']:
            website_config['has_sign_up'] = self.env['res.users']._get_signup_invitation_scope() == 'b2c'
        if key:
            return website_config.get(key)
        return website_config

    def _get_current_pricelist(self):
        if self._get_dr_theme_config('json_b2b_shop_config')['dr_only_assigned_pricelist'] and not self.env.user.has_group('website.group_website_designer'):
            return self.env.user.partner_id.property_product_pricelist
        return super()._get_current_pricelist()

    def _dr_website_has_uellow_theme(self):
        return self._get_dr_theme_config('theme_installed')

    def get_pricelist_available(self, show_visible=False):
        if self._get_dr_theme_config('json_b2b_shop_config')['dr_only_assigned_pricelist'] and not self.env.user.has_group('website.group_website_designer'):
            return self.env.user.partner_id.property_product_pricelist
        return super().get_pricelist_available(show_visible=show_visible)

    @api.model
    def get_uellow_theme_shop_config(self):
        Website = self.get_current_website()
        return {
        'is_rating_active': Website.sudo().viewref('website_sale.product_comment').active,
        'is_buy_now_active': Website.sudo().viewref('website_sale.product_buy_now').active,
        'is_multiplier_active': Website.sudo().viewref('website_sale.product_quantity').active,
        'is_wishlist_active': Website.sudo().viewref('website_sale_wishlist.product_add_to_wishlist').active,
        'is_comparison_active': Website.sudo().viewref('website_sale_comparison.add_to_compare').active}

    def _get_website_category(self):
        return self.env['product.public.category'].search([('website_id', 'in', [False, self.id]), ('parent_id', '=', False)])

    def _get_uellow_theme_rating_template(self, rating_avg, rating_count=False):
        return self.env['ir.qweb']._render('uellow_theme.d_rating_widget_stars_static', values={
            'rating_avg': rating_avg,
            'rating_count': rating_count,
        }, minimal_qcontext=True)

    @api.model
    def get_uellow_theme_bottom_bar_action_buttons(self):
        # Add to cart, blog, checkout, pricelist, language,
        return {'tp_home': {'name': _("Home"), 'url': '/', 'icon': 'fa fa-home'}, 'tp_search': {'name': _("Search"), 'icon': 'dri dri-search', 'action_class': 'tp-search-sidebar-action'}, 'tp_wishlist': {'name': _("Wishlist"), 'icon': 'dri dri-wishlist', 'url': '/shop/wishlist'}, 'tp_offer': {'name': _("Offers"), 'url': '/offers', 'icon': 'dri dri-bolt'}, 'tp_brands': {'name': _("Brands"), 'icon': 'dri dri-tag-l ', 'url': '/shop/all-brands'}, 'tp_category': {'name': _("Category"), 'icon': 'dri dri-category', 'action_class': 'tp-category-action'}, 'tp_orders': {'name': _("Orders"), 'icon': 'fa fa-file-text-o', 'url': '/my/orders'}, 'tp_cart': {'name': _("Cart"), 'icon': 'dri dri-cart', 'url': '/shop/cart'}, 'tp_lang_selector': {'name': _("Language and Pricelist selector")}}

    def _is_snippet_used(self, snippet_module, snippet_id, asset_version, asset_type, html_fields):
        """ There is no versioning for all theme snippets (for the test case)"""
        if snippet_module and snippet_module.startswith('uellow_theme'):
            return True
        return super()._is_snippet_used(snippet_module, snippet_id, asset_version, asset_type, html_fields)

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['category_synonyms']:
            result.append(self.env['dr.category.synonyms']._search_get_detail(self, order, options))
        return result


class WebsiteSaleExtraField(models.Model):
    _inherit = 'website.sale.extra.field'

    dr_label = fields.Char('Display Label', translate=True)
    field_id = fields.Many2one('ir.model.fields', domain=[('model_id.model', '=', 'product.template'), '|', ('ttype', 'in', ['char', 'binary']), ('name', 'in', ['public_categ_ids'])])
