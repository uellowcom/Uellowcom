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
            ('social_facebook',  'facebook',        'Facebook'),
            ('social_instagram', 'instagram',       'Instagram'),
            ('social_twitter',   'twitter',         'X / Twitter'),
            ('social_youtube',   'youtube-play',    'YouTube'),
            ('social_tiktok',    'music',           'TikTok'),
            ('social_linkedin',  'linkedin',        'LinkedIn'),
            ('social_github',    'github',          'GitHub'),
        ]
        out = []
        for fname, icon, label in fields_map:
            val = getattr(self, fname, None)
            if val:
                out.append({'icon': icon, 'url': val, 'label': label})
        return out

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
        current_website_products = self.env['product.template'].search(website.sale_product_domain())
        return self.env['product.attribute'].search([('product_tmpl_ids', 'in', current_website_products.ids), ('dr_is_brand', '=', True)])

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
