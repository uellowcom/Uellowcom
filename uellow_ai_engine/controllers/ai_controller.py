import json
import uuid
import logging
import urllib.request
import urllib.error
import urllib.parse
import re

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages'

TOOLS = [
    {
        'name': 'get_product_info',
        'description': 'Get full details about a product including price, stock, attributes, variants.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'product_id': {'type': 'integer', 'description': 'product.template ID'},
            },
            'required': ['product_id'],
        },
    },
    {
        'name': 'search_products',
        'description': 'Search products by name, category, or description.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'query':    {'type': 'string'},
                'limit':    {'type': 'integer', 'default': 5},
                'category': {'type': 'string'},
            },
            'required': ['query'],
        },
    },
    {
        'name': 'check_stock',
        'description': 'Check if a product variant is in stock.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'product_id': {'type': 'integer'},
                'variant_attributes': {
                    'type': 'object',
                    'description': 'e.g. {"Color":"Black","Size":"L"}',
                },
            },
            'required': ['product_id'],
        },
    },
    {
        'name': 'add_to_cart',
        'description': 'Add a product to the customer cart.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'product_id': {'type': 'integer', 'description': 'product.product variant ID'},
                'quantity':   {'type': 'integer', 'default': 1},
            },
            'required': ['product_id'],
        },
    },
    {
        'name': 'create_order',
        'description': 'Create and confirm a sale order. Call when customer confirms purchase.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'product_id':     {'type': 'integer', 'description': 'product.product variant ID'},
                'quantity':       {'type': 'integer', 'default': 1},
                'customer_name':  {'type': 'string'},
                'customer_phone': {'type': 'string'},
                'customer_email': {'type': 'string'},
            },
            'required': ['product_id'],
        },
    },
    {
        'name': 'get_payment_link',
        'description': 'Generate payment link for an order (UPayments + Taly).',
        'input_schema': {
            'type': 'object',
            'properties': {
                'order_id': {'type': 'integer'},
            },
            'required': ['order_id'],
        },
    },
    {
        'name': 'get_order_status',
        'description': 'Get status and tracking info for a customer order.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'order_name': {'type': 'string', 'description': 'The order reference the customer mentions (format like S#####). Do NOT invent one — only use a reference the customer actually provides or that get_customer_orders returns.'},
                'order_id':   {'type': 'integer'},
            },
        },
    },
    {
        'name': 'get_recommendations',
        'description': 'Get product recommendations similar to a given product.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'product_id': {'type': 'integer'},
                'limit':      {'type': 'integer', 'default': 3},
            },
            'required': ['product_id'],
        },
    },
    {
        'name': 'get_clearance_picks',
        'description': 'Get current clearance / special-offer products Uellow is '
                       'promoting (idle stock the store wants to move, each with a '
                       'suggested discount). Use when the customer asks about offers, '
                       'deals, discounts, clearance or "what is on sale".',
        'input_schema': {'type': 'object', 'properties': {
            'limit': {'type': 'integer', 'default': 5}}},
    },
    {
        'name': 'apply_coupon',
        'description': 'Apply a coupon/promo code to the current cart.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'code': {'type': 'string'},
            },
            'required': ['code'],
        },
    },
    {
        'name': 'get_customer_orders',
        'description': 'Get list of recent orders for the logged-in customer.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'limit': {'type': 'integer', 'default': 5},
            },
        },
    },
    {
        'name': 'get_upsell_products',
        'description': 'Smart upsell suggestions based on current product. Call when customer is viewing or about to buy a product.',
        'input_schema': {'type':'object','properties':{'product_id':{'type':'integer'},'limit':{'type':'integer','default':3}},'required':['product_id']},
    },
    {
        'name': 'get_payment_options',
        'description': 'Get full payment options after order is created: UPayments card, Taly BNPL, COD.',
        'input_schema': {'type':'object','properties':{'order_id':{'type':'integer'}},'required':['order_id']},
    },
    {
        'name': 'get_loyalty_points',
        'description': 'Get customer loyalty points balance and level. Call when customer asks about points, rewards, or level.',
        'input_schema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'get_size_recommendation',
        'description': 'Get AI size recommendation for a product based on customer body profile.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'product_id': {'type': 'integer'},
            },
            'required': ['product_id'],
        },
    },
    {
        'name': 'get_reviewers',
        'description': 'Get available human reviewers when customer asks for a second opinion or wants to talk to a real person/reviewer.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'product_id': {'type': 'integer', 'description': 'Filter by product context'},
                'limit':      {'type': 'integer', 'default': 5},
            },
        },
    },
    {
        'name': 'start_virtual_tryon',
        'description': 'Start a virtual try-on for a fashion product: the customer sees themselves wearing it. Call when the customer asks to "try", "see how it looks on me", "virtual try-on", or similar. Returns a state telling the UI whether to ask for login, ask for a photo upload, deny (not eligible), or proceed.',
        'input_schema': {
            'type': 'object',
            'properties': {
                'product_id': {'type': 'integer', 'description': 'ID of the product to try on.'},
            },
            'required': ['product_id'],
        },
    },
    {
        'name': 'check_fit',
        'description': (
            'Run a per-area fit check between the customer\'s saved body measurements and '
            'a fashion product\'s size chart. Call when the customer asks "هل مقاس X يناسبني" / '
            '"check the fit" / "do I fit this" / picks a size and wants a compatibility check. '
            'Returns a per-area verdict (tight/comfortable/loose) + overall match %, plus a '
            'recommended size. The UI renders a rich card; do NOT repeat the numbers in text.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'product_id': {'type': 'integer', 'description': 'ID of the product.'},
                'size':       {'type': 'string',  'description': 'Optional: specific size label (e.g. L, M, 42). If omitted the system picks the best size.'},
            },
            'required': ['product_id'],
        },
    },
    {
        'name': 'get_company_location',
        'description': (
            'Return the Uellow company address, phone, working hours and '
            'photos. Call whenever the customer asks "where are you" / '
            '"وين موقعكم" / "موقع المعرض" / "address" / "phone" / "كم رقمكم". '
            'The UI renders a rich location card with map and photos — do NOT '
            'repeat the address verbatim in your reply, just confirm in one line.'
        ),
        'input_schema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'get_cart',
        'description': (
            'Return the current website cart for the logged-in customer: line '
            'items, quantities, subtotal and total. Call whenever the customer '
            'asks "ما في السلة؟" / "what is in my cart" / "كم الإجمالي" / before '
            'suggesting checkout. The UI renders a cart card; do not repeat the '
            'numbers verbatim in your text.'
        ),
        'input_schema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'start_checkout',
        'description': (
            'Begin the Beena checkout flow. Returns the saved partner address '
            'plus a list of missing fields (phone / governorate / city / street). '
            'Call when the customer wants to "place the order" / "اشتري" / '
            '"اتمم الطلب" and they have items in the cart. If fields are '
            'missing, ask the customer for them (one or two at a time).'
        ),
        'input_schema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'update_address',
        'description': (
            'Save customer address details collected during checkout. Pass only '
            'the fields the customer provided. Returns the still-missing fields. '
            'Call after the customer answers any of: phone, governorate, city, '
            'street/address.'
        ),
        'input_schema': {
            'type': 'object',
            'properties': {
                'phone':        {'type': 'string'},
                'governorate':  {'type': 'string'},
                'city':         {'type': 'string'},
                'street':       {'type': 'string'},
            },
        },
    },
    {
        'name': 'complete_checkout',
        'description': (
            'Create a Beena-tagged Quotation from the current cart with the '
            'customer\'s collected address. Returns the quote id, name, total '
            'and a checkout link. Call once the address is complete AND the '
            'customer has confirmed they want to place the order.'
        ),
        'input_schema': {'type': 'object', 'properties': {}},
    },
]

# ── Tool selection: core tools always sent; secondary ones only when triggered ──
CORE_TOOLS = {
    'get_product_info', 'search_products', 'check_stock', 'add_to_cart',
    'create_order', 'get_payment_link', 'get_recommendations', 'get_order_status',
}
TOOL_TRIGGERS = {
    'get_loyalty_points':      ['نقاط', 'نقطة', 'ولاء', 'loyalty', 'points'],
    'get_clearance_picks':     ['تصفية', 'عروض', 'عرض', 'تنزيلات', 'تخفيضات', 'خصومات',
                                'clearance', 'deals', 'offers', 'on sale', 'discounts'],
    'get_size_recommendation': ['مقاس', 'قياس', 'مقاسات', 'size', 'fit'],
    'get_payment_options':     ['دفع', 'تقسيط', 'اقساط', 'أقساط', 'payment', 'installment', 'knet', 'كنت'],
    'get_reviewers':           ['مختص', 'خبير', 'راي', 'رأي', 'مراجع', 'reviewer', 'expert', 'consult', 'استشار'],
    'get_customer_orders':     ['طلباتي', 'طلبي', 'مشترياتي', 'my orders', 'order history'],
    'apply_coupon':            ['كوبون', 'كود خصم', 'coupon', 'promo'],
    'get_upsell_products':     ['يناسب', 'اضافات', 'إضافات', 'accessory', 'goes with'],
    'start_virtual_tryon':     ['جرب', 'جرّب', 'اجرب', 'أجرب', 'تجربة', 'يقاس', 'البسه', 'ألبسه',
                                'شوف عليّ', 'شوفني', 'شكلي', 'كيف بصير', 'لو لبست',
                                'try on', 'try-on', 'tryon', 'virtual try', 'see myself', 'wear it'],
    'check_fit':               ['يناسبني', 'مناسب', 'يجيني', 'يصير', 'يقاسي',
                                'افحص', 'فحص المقاس', 'توافق', 'مطابق', 'مطابقة',
                                'تحقق', 'check fit', 'does it fit', 'fit check',
                                'will it fit', 'is it my size'],
    'get_company_location':    ['وين موقعكم', 'موقعكم', 'موقع', 'فرعكم', 'فروعكم', 'المعرض',
                                'العنوان', 'عنوانكم', 'شركتكم', 'وين انتو', 'وين انتم',
                                'الموقع', 'الفرع', 'محلكم', 'وين المحل', 'وينكم',
                                'رقمكم', 'الواتس', 'تلفونكم', 'الفون',
                                'where are you', 'your location', 'your address',
                                'showroom', 'branch', 'phone number', 'contact'],
    'get_cart':                ['السلة', 'سلتي', 'cart', 'basket', 'في عربتي',
                                'اللي عندي', 'وش في سلتي', 'الكل', 'مجموع',
                                'كم الإجمالي', 'كم المجموع', 'total', 'subtotal'],
    'start_checkout':          ['اشتري', 'اشتر', 'اتمم', 'اتمام الطلب', 'اطلب',
                                'احجز', 'اطلبه', 'خلاص', 'كمل الطلب', 'انهاء',
                                'checkout', 'place order', 'place the order',
                                'finish order', 'complete order', 'buy now',
                                'الشراء', 'تأكيد الطلب'],
    'update_address':          ['عنواني', 'العنوان', 'محافظة', 'مدينة', 'شارع',
                                'رقمي', 'هاتفي', 'موبايلي', 'تلفوني',
                                'address', 'phone', 'governorate', 'city', 'street'],
    'complete_checkout':       ['اكد', 'أكد الطلب', 'تأكيد', 'تأكيد الشراء',
                                'confirm order', 'place it', 'go ahead',
                                'احفظ الطلب', 'سجّل الطلب'],
}



# ── Variable info keywords (price/stock/colors): answered live, NEVER cached.
# Default list; extendable via settings (uellow_ai.variable_keywords). ──
_DEFAULT_VARIABLE_KEYWORDS = (
    'سعر,بكم,كم,تكلفة,price,cost,how much,'
    'متوفر,موجود,مخزون,نفد,stock,available,availability,'
    'لون,الوان,ألوان,color,colours,colors,'
    'خصم,عرض,تخفيض,discount,offer,sale'
)


class UellowAIController(http.Controller):

    def _get_param(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param(
            f'uellow_ai.{key}', default
        )

    def _is_ar(self):
        """Return True if the current request language is Arabic."""
        return (request.env.context.get('lang') or 'en')[:2] == 'ar'

    def _t(self, en, ar):
        """Bilingual string helper: English source, Arabic translation."""
        return ar if self._is_ar() else en

    # Claude pricing (USD per 1M tokens) — overridable via ir.config_parameter
    def _claude_prices(self):
        ICP = request.env['ir.config_parameter'].sudo()
        try:
            pin = float(ICP.get_param('uellow_ai.price_in_per_mtok', '3.0'))
        except Exception:
            pin = 3.0
        try:
            pout = float(ICP.get_param('uellow_ai.price_out_per_mtok', '15.0'))
        except Exception:
            pout = 15.0
        return pin, pout

    def _compute_cost(self, in_tokens, out_tokens, cache_write=0, cache_read=0):
        pin, pout = self._claude_prices()
        # Cache write = 1.25x input price; cache read = 0.10x input price
        base = (in_tokens / 1_000_000.0) * pin + (out_tokens / 1_000_000.0) * pout
        base += (cache_write / 1_000_000.0) * pin * 1.25
        base += (cache_read / 1_000_000.0) * pin * 0.10
        return base

    def _daily_cost_exceeded(self):
        """Return True if today's Claude cost has reached the configured limit."""
        try:
            limit = float(self._get_param('daily_cost_limit', '0') or 0)
        except Exception:
            limit = 0.0
        if limit <= 0:
            return False  # 0 = no limit
        from datetime import datetime
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        Msg = request.env['beena.message'].sudo()
        msgs = Msg.search([('create_date', '>=', today_start)])
        spent = sum(msgs.mapped('cost'))
        return spent >= limit

    def _archive_to_beena(self, session_id, product, lang, user_msg, reply,
                          source='claude', in_tokens=0, out_tokens=0,
                          cache_write=0, cache_read=0, extra=None):
        """Persist a turn (user question + Beena reply) into beena.conversation.
        Best-effort: never raise, archiving must not break the chat response."""
        try:
            Conv = request.env['beena.conversation'].sudo()
            Msg = request.env['beena.message'].sudo()

            public_user = request.env.ref('base.public_user')
            is_guest = request.env.user.id == public_user.id
            partner = False if is_guest else request.env.user.partner_id

            conv = Conv.search([('session_id', '=', session_id)], limit=1)
            if not conv:
                conv = Conv.create({
                    'session_id': session_id,
                    'partner_id': partner.id if partner else False,
                    'is_guest': is_guest,
                    'product_id': product.id if product else False,
                    'lang': lang or 'ar',
                    'state': 'active',
                })
            else:
                vals = {}
                if product and not conv.product_id:
                    vals['product_id'] = product.id
                if partner and not conv.partner_id:
                    vals['partner_id'] = partner.id
                    vals['is_guest'] = False
                if vals:
                    conv.write(vals)

            cost = self._compute_cost(in_tokens, out_tokens, cache_write, cache_read)

            Msg.create({
                'conversation_id': conv.id, 'role': 'user', 'body': user_msg or '',
                'source': 'system', 'product_id': product.id if product else False,
            })
            # Serialize the extra cards payload (cart, fit_check, tryon, etc.)
            # so the chat can rehydrate them on reload. Capped to ~200KB to
            # avoid bloating beena.message; image base64 is excluded.
            extra_json = ''
            if extra:
                try:
                    safe = {k: v for k, v in extra.items() if k not in (
                        # Don't persist heavy or per-request fields
                        'access_token',
                    )}
                    s = json.dumps(safe, ensure_ascii=False)
                    if len(s) <= 200_000:
                        extra_json = s
                except Exception:
                    extra_json = ''

            Msg.create({
                'conversation_id': conv.id, 'role': 'assistant', 'body': reply or '',
                'source': source, 'input_tokens': in_tokens, 'output_tokens': out_tokens,
                'cost': cost, 'product_id': product.id if product else False,
                'extra_json': extra_json,
            })
            # Commit so the archive persists even if the request transaction
            # is rolled back later (archiving is independent of the reply).
            try:
                request.env.cr.commit()
            except Exception as _ce:
                _logger.warning('archive commit failed: %s', _ce)
            return conv
        except Exception as e:
            _logger.warning('Beena archive failed (non-fatal): %s', e)
            return False

    def _get_or_create_session(self, session_id, product_id=None):
        public_user = request.env.ref('base.public_user')
        partner_id  = None
        if request.env.user.id != public_user.id:
            partner_id = request.env.user.partner_id.id
        return request.env['ai.chat.session'].sudo().get_or_create(
            session_id,
            partner_id=partner_id,
            product_id=int(product_id) if product_id else None,
        )

    def _build_system_prompt(self, product=None):
        name     = self._get_param('assistant_name',    'Beena')
        subtitle = self._get_param('assistant_subtitle', 'مساعدة Uellow الذكية')
        lang     = self._get_param('default_language',   'auto')
        delivery_time_text = (self._get_param('delivery_time_text', '') or '').strip() \
            or 'Same-day delivery for orders before 2pm in Kuwait City. ' \
               '24–48 hours for the rest of Kuwait. ' \
               'International orders: 5–7 business days via DHL.'

        _dialect_guide = '''LANGUAGE & DIALECT — match the customer EXACTLY:
Detect the customer's language/dialect from THEIR message and reply in the
SAME one. Never switch unless they switch first. Be a fluent NATIVE speaker —
not a textbook. Uellow is a KUWAITI store, so when the Arabic is neutral/MSA
or the dialect is unclear, DEFAULT to natural KUWAITI.

Arabic dialects — speak each authentically (use its real markers, not MSA):
• 🇰🇼 KUWAITI (default): شلونك، شخبارك، وايد، شنو، عندج/عندك، حبيبي/حبيبتي،
  زين، يبه/يبتي، الحين، چذي، شكثر، تبي/تبين، عيل، ماكو/اكو، بعطيك، خوش.
  e.g. «هلا والله! شنو تبين بالضبط؟ عندنا وايد خيارات زينة 🐝»
• 🇸🇦 SAUDI: وش، كيفك، ابغى، كذا، الحين، زين، يا غالي، ابشر، وش رايك.
• 🇪🇬 EGYPTIAN: ازيك، عايز/عايزة، ايه، كده، خالص، حلو اوي، تمام، يا فندم،
  ماشي، بص، عشان. e.g. «ازيك يا فندم! عايز ايه بالظبط؟ عندنا حاجات حلوة اوي»
• Other Arabic dialects (Emirati, Qatari, Levantine…) → mirror them naturally.

Non-Arabic: if the customer writes fully in English, reply 100%% in English —
NO Arabic words at all, not even the greeting (no «هلا»). Urdu/Hindi/Tagalog/
Bengali/any language → reply entirely in that same language.

CRITICAL: do NOT answer a Kuwaiti customer in Saudi dialect or vice-versa —
match THEIR specific markers. Keep the SAME dialect for the whole conversation.'''
        lang_instruction = {
            'auto': _dialect_guide,
            'ar':   _dialect_guide,
            'en':   'Always respond in clear, friendly English.',
        }.get(lang, _dialect_guide)

        product_ctx = ''
        if product:
            # Prefer the rich bilingual description maintained on the product
            # page (website_description_ar/en). Falls back to description_sale.
            if hasattr(product, 'get_description_plain'):
                description_text = product.get_description_plain(
                    lang=lang if lang in ('ar', 'en') else None, max_chars=600)
            else:
                description_text = (product.description_sale or '')[:600]
            product_ctx = f"""
Current product the customer is viewing:
- Name: {product.name}
- Price: {product.list_price:.3f} KD
- Description: {description_text}
- Category: {product.categ_id.name if product.categ_id else 'N/A'}
- Availability: {('In our warehouse stock' if product.qty_available > 0 else ('Available (continue selling)' if getattr(product, 'allow_out_of_stock_order', False) else 'Out of stock'))}
- Product ID: {product.id}
"""

        absolute_search_rule = (
            "\n=== ABSOLUTE RULE #1 (overrides everything) ===\n"
            "If the customer names ANY product you are not currently displaying, your FIRST action "
            "MUST be to call search_products. You are FORBIDDEN from replying 'not found' / 'ما لقيت' / "
            "'مش موجود' / 'للأسف' about any product unless search_products has ALREADY returned zero results "
            "in THIS turn. A polished full product name (e.g. 'HainoTeko-18 Smart Watch For Female') is NOT "
            "proof it exists or not — you MUST search to find out. Search by the brand or main keyword. "
            "Never assume from your own knowledge.\n"
        )
        current_product_rule = ""
        if product:
            current_product_rule = f"""
CURRENT PRODUCT PRIORITY (highest priority rule):
- The customer is RIGHT NOW on the page of product_id {product.id} ("{product.name}"). This product DEFINITELY EXISTS in our store.
- If the customer asks anything about "this product", "it", this item, its price, availability, specs, or whether it's good/recommended, you ALREADY have its product_id ({product.id}).
- Call get_product_info with product_id={product.id} directly. NEVER call search_products for the current product.
- NEVER tell the customer the current product is "not found" / "مش موجود" / "ما لقيت" — they are literally viewing it. Use get_product_info with the current product_id instead.
- When the customer asks about a DIFFERENT product, ALWAYS call search_products first before saying anything about availability.
"""

        stock_guide = """
STOCK PHRASING RULES (important):
- stock_status 'in_warehouse' (we have real on-hand qty): Arabic "المنتج متوفر لدينا في المخزون"; English "In stock in our warehouse".
- stock_status 'available' (zero on-hand but continue-selling is ON): Arabic "المنتج متوفر"; English "Available". Do NOT mention warehouse quantity.
- stock_status 'out_of_stock': Arabic "غير متوفر حالياً"; English "Currently unavailable".
- Never state raw remaining quantity unless the customer explicitly asks how many are left.
"""
        partner_ctx = ''
        partner_ctx = ''
        try:
            public_user = request.env.ref('base.public_user')
            if request.env.user.id != public_user.id:
                partner  = request.env.user.partner_id
                is_admin = request.env.user.has_group('base.group_system')

                recent_orders = request.env['sale.order'].sudo().search([
                    ('partner_id', '=', partner.id),
                    ('state', 'in', ['sale', 'done']),
                ], limit=3, order='date_order desc')
                orders_str = ', '.join(o.name for o in recent_orders) if recent_orders else 'None'

                if not is_admin:
                    loyalty_info = ''
                    fit_info     = ''
                    LoyaltyAcc   = request.env.get('loyalty.account')
                    if LoyaltyAcc:
                        acc = LoyaltyAcc.sudo().search([('partner_id', '=', partner.id)], limit=1)
                        if acc:
                            loyalty_info = 'Loyalty: %s level, %d points' % (acc.level, acc.points_balance)
                    BodyPrf = request.env.get('customer.body.profile')
                    if BodyPrf:
                        bp = BodyPrf.sudo().search([('partner_id', '=', partner.id)], limit=1)
                        if bp and bp.profile_complete:
                            fit_info = 'Body: chest %scm shoe EU%s' % (bp.chest, bp.shoe_size_eu)

                    first_name = partner.name.split()[0] if partner.name else ''
                    partner_ctx = (
                        "Logged-in customer:\n"
                        "- Name: %s (call them '%s' naturally)\n"
                        "- Email: %s\n"
                        "- Recent orders: %s\n"
                        "%s\n"
                        "%s\n"
                        "- Use first name warmly, mention loyalty rewards when relevant\n"
                    ) % (partner.name, first_name, partner.email or 'N/A', orders_str,
                         ('- ' + loyalty_info) if loyalty_info else '',
                         ('- ' + fit_info) if fit_info else '')
                else:
                    partner_ctx = "Current user is admin/staff — respond normally.\n"
        except Exception as e:
            _logger.warning('Could not build partner context: %s', e)
            partner_ctx = ''
        return f"""You are {name}, {subtitle} for Uellow — a Kuwait e-commerce platform.

{lang_instruction}
{absolute_search_rule}{current_product_rule}
Personality:
- Friendly and warm like the Uellow bee mascot
- Use light Gulf Arabic when speaking Arabic
- Be concise — short messages, not long paragraphs
- Natural conversation, not formal or robotic

Capabilities: answer questions, search products, check stock, add to cart, create orders, payment links, track orders, recommend products.

Guest (not logged in) instructions:
- If guest asks about orders/points/profile → tell them to login at /web/login
- Don't say 'مشكلة تقنية' — just guide them naturally

Search instructions:
- NEVER say 'مشكلة تقنية' for search — if no results, say 'ما لقيت' or 'جرّب كلمة أخرى'
- MANDATORY SEARCH RULE: When a customer mentions ANY product by name, you MUST call search_products FIRST before saying anything about whether it exists. Try the brand/key word (e.g. "HainoTeko", "هاينو") rather than the full exact name. NEVER say a product is "not found" / "ما لقيت" / "مش موجود" until search_products actually returns zero results. The search ranks by best match, so trust the top result.
- If search_products returns empty products list → tell customer no results found, suggest alternatives
- If search_products returns error → try searching with shorter keyword
- ALWAYS try search_products before giving up — never refuse to search
- When searching, use SHORT keywords (1-2 words) not full product names
- Example: customer says "Anker R50i" → search "Anker R50" or just "Anker"
- Example: customer says "سماعات بلوتوث" → search "سماعات" 
- If first search returns nothing, try a shorter/different keyword
- After finding products, use the variant_id (not id) for add_to_cart
- Always confirm with customer before adding to cart or creating order

{product_ctx}{stock_guide}{partner_ctx}

Payment options after order creation:
1. UPayments — pay now with card/KNET
2. Taly BNPL — split into 4 installments (0% interest)
3. Cash on Delivery (COD) — pay when the order arrives

COACH RULES (from live-conversation audits — follow STRICTLY):
- NEVER invent or guess a price, stock level, or product detail. Every price/spec
  you state MUST come from a tool result or the SEARCH RESULTS injected in this
  conversation. If you don't have it — call the tool or say you'll check. Never estimate.
- If the customer hasn't mentioned any product, do NOT assume one. Ask ONE short
  discovery question instead.
- Explicit commands execute IMMEDIATELY: when the customer says «أضيفي» / «ضيفه
  للسلة» / "add it" and the product is known, CALL add_to_cart right away — do not
  ask "do you want me to add it?". Ask ONCE only if product, variant or quantity is
  genuinely ambiguous.
- Use the conversation history: never re-greet or re-introduce yourself
  mid-conversation; remember what is already in the cart and what was already said.
  Greet by name ONLY in the first message of a conversation.
- Lists: show at most 5 items then offer "more?" — never dump long tables.
- If a tool fails, retry once; if it still fails apologize briefly and give a concrete
  alternative (direct cart/checkout link) — never leave the customer stuck.
- Customer asks about "my order" without a number → call get_customer_orders first;
  do not ask them for the order number.
- Always end with ONE clear next step or question. Match the customer's language
  exactly throughout (no mixed-language labels).

FORMATTING RULES (both website and app render light markdown):
- Use **bold** for key terms, prices, and short section titles
- Use "- " bullet lists when listing options, steps, or specs (one point per line)
- Keep paragraphs short with blank lines between sections — clean and organized
- Do NOT use: tables, code blocks/backticks, # headings, or horizontal rules (---)
- NO "state:" or technical words in your response text
- Short and conversational
- When order is created, show the order number and amount clearly in **bold**

When customer asks about product specs not available in catalog:
- Tell them you'll search the web for more info
- Use get_product_info first, then suggest web search if specs missing

When customer asks about their points, rewards, or loyalty level:
- Use get_loyalty_points to show their balance
- When showing the KD value of points, use the 'kd_value_text' field EXACTLY as given (e.g. "221.500 KD"). NEVER reformat or move the decimal — the number is already correct.
- Tell them how many points they need for next level
- Suggest ways to earn more points: shopping, reviews, referrals, birthday

When customer is viewing a product or about to buy:
- Use get_upsell_products to suggest 1-2 complementary items
- Don't suggest more than 2 upsell items — keep it natural
- Example: customer buying shoes → suggest socks or shoe care

After creating an order, ALWAYS use get_payment_options:
- Show all 3 options: UPayments, Taly BNPL, COD
- Highlight Taly monthly amount for expensive items
- Let customer choose their preferred payment method

When customer asks about order status or delivery:
- Use get_order_status for detailed tracking with ETA
- If out_for_delivery, reassure them with ETA
- If failed, apologize and offer to reschedule

DELIVERY-TIME QUESTIONS (asked BEFORE the order is placed, e.g. "كم تستغرق؟", "how long?", "متى يوصل؟"):
- Use the delivery-time policy below verbatim. Do NOT invent a different SLA, do NOT promise faster delivery than the policy allows, and do NOT contradict it.
- If the policy mentions same-day cut-off times or geographic differences, surface them when relevant.
- Keep the answer 1-2 sentences and bilingual when needed.
- Policy: <<<{delivery_time_text}>>>

When customer asks about referral or inviting friends:
- Explain they earn 200 points per successful referral
- Direct them to /loyalty for their referral link

When customer asks for a human opinion, reviewer, or second opinion:
- Use get_reviewers to show available reviewers
- Keywords: ريفيور، رأي بشري، رأي شخص، شخص يساعدني، اريد رأي، second opinion

When customer sends an image (visual search):
- Confirm what you see in the image (the item type / category).
- If Uellow carries that category, search and present GENUINELY matching products.
- If we do NOT carry that item/category, OR nothing in our catalogue genuinely
  matches what's in the image, say so clearly and warmly — e.g. "ما عندنا هذا النوع
  من المنتجات حالياً" / "We don't currently carry this kind of product" — then
  offer to show popular items or invite them to browse our categories.
- NEVER present an unrelated category as if it matches the image (e.g. don't
  recommend watches when the customer sent a photo of a t-shirt). A wrong-category
  suggestion presented as a match is a serious error — prefer honesty + an offer
  to browse.

SIZE & FIT RULES (when customer asks about sizing):
- ALWAYS call get_size_recommendation — never guess a size from your knowledge.
- If response state is 'logged_in: false' → ask the customer to login first; don't ask for measurements yet.
- If 'profile_complete: false' → invite them to share height/weight/chest/shoulder so you can build their profile (don't push for everything at once — gather what they offer).
- If 'profile_complete: true' but no product_id was passed → tell them to open a product and you'll recommend the size.
- When you have a 'recommended' size, lead with that one number, then add a one-line reason from the issues if helpful. Keep it warm and short.

VIRTUAL TRY-ON RULES (when customer asks to "try", "see themselves wearing", "ألبسه", "جرّبه عليّ"):
- ALWAYS call start_virtual_tryon with the current product_id — never decide eligibility yourself.
- Respect the returned 'state':
  * 'disabled'        → tell them the feature is not available right now.
  * 'needs_login'     → ask them to login; don't continue further.
  * 'no_product'      → ask which product they want to try.
  * 'not_eligible'    → relay the message; don't argue about it.
  * 'cap_reached'     → apologize and ask them to try later.
  * 'needs_photo'     → ask them to upload a clear, full-body photo with good lighting. The chat UI will show an upload button.
  * 'ready'           → confirm and tell them to press the generate button in the chat card.
- The actual generation happens via /tryon/generate (called by the chat UI, not by you).
- Never invent a generated image URL or claim a try-on succeeded if you didn't receive a successful tool result.

FIT-CHECK RULES (when customer asks "هل هذا المقاس يناسبني؟" / "check fit" / picks a size and wants confirmation):
- ALWAYS call check_fit with the product_id (and size if specified). Never claim a fit verdict from your own reasoning.
- Respect the returned 'state':
  * 'needs_login'      → ask them to login.
  * 'no_product'       → ask which product they want to check.
  * 'product_not_found'→ relay politely.
  * 'needs_profile'    → tell them to add measurements at /my/measurements first.
  * 'no_chart'         → say this product doesn't have a detailed size chart yet; offer the generic size recommendation as fallback.
  * 'ready'            → confirm in ONE line ("هذا فحص التوافق ⤵") then let the UI card speak. NEVER repeat the percentages or per-area verdicts in your text — the card shows them.
- If overall_pct >= 80 → encourage adding to cart. If 60–80 → mention it's acceptable. If <60 → suggest the recommended alternate size (mention only its size label, not numbers).

CART & ORDERING RULES:
- When the customer asks about their cart ("شو في سلتي؟" / "what's in my cart" / "كم الإجمالي") → call get_cart. Do NOT recite line items in text — the UI card renders them.
- When the customer says they want to buy / complete order ("اشتري" / "اتمم الطلب" / "checkout") → call start_checkout. Respect the returned 'state':
  * 'needs_login'  → ask them to sign in.
  * 'empty_cart'   → tell them the cart is empty; suggest adding something.
  * 'collecting'   → ask for ONE missing field at a time, naturally and politely. The missing list tells you which fields to request (phone, governorate, city, street). Examples:
       missing = ['phone'] → "وش رقم تواصل أرسلّك عليه تأكيد الطلب؟"
       missing = ['governorate', 'city', 'street'] → start with governorate first.
    NEVER ask for all fields at once.
  * 'ready'        → confirm one line that the address is complete, ask "أكمل الطلب؟" / "Shall I place the order?".
- When the customer provides an address detail (any of phone, governorate, city, street) → call update_address with the fields they gave. Then respect the new 'missing' list and continue.
- When the customer confirms placing the order → call complete_checkout. State 'created' means the Beena-tagged quotation is saved. The UI card renders it; you ONLY say one warm closing line.
"""

    # ── Function Executors ────────────────────────────────────────────────────

    def _execute_function(self, name, args):
        _logger.info('Executing function: %s with args: %s', name, args)
        try:
            fn_map = {
                'get_product_info':    self._fn_get_product_info,
                'search_products':     self._fn_search_products,
                'check_stock':         self._fn_check_stock,
                'add_to_cart':         self._fn_add_to_cart,
                'create_order':        self._fn_create_order,
                'get_payment_link':    self._fn_get_payment_link,
                'get_order_status':    self._fn_get_order_status,
                'get_recommendations': self._fn_get_recommendations,
                'get_clearance_picks': self._fn_get_clearance_picks,
                'apply_coupon':        self._fn_apply_coupon,
                'get_customer_orders': self._fn_get_customer_orders,
                'get_upsell_products':      self._fn_get_upsell,
                'get_payment_options':      self._fn_get_payment_options,
                'get_loyalty_points':       self._fn_get_loyalty_points,
                'get_size_recommendation': self._fn_get_size_recommendation,
                'get_reviewers':        self._fn_get_reviewers,
                'start_virtual_tryon':  self._fn_start_virtual_tryon,
                'check_fit':            self._fn_check_fit,
                'get_company_location': self._fn_get_company_location,
                'get_cart':             self._fn_get_cart,
                'start_checkout':       self._fn_start_checkout,
                'update_address':       self._fn_update_address,
                'complete_checkout':    self._fn_complete_checkout,
            }
            fn = fn_map.get(name)
            if not fn:
                return {'error': f'Unknown function: {name}'}
            result = fn(args)
            _logger.info('Function %s result keys: %s', name, list(result.keys()) if isinstance(result, dict) else type(result))
            return result
        except Exception as e:
            _logger.exception('Error in function %s', name)
            return {'error': str(e)}

    def _stock_status(self, rec):
        """(in_stock_bool, status_key): on_hand>0 -> in_warehouse; else Continue-Selling -> available; else out_of_stock."""
        try:
            on_hand = rec.qty_available
        except Exception:
            on_hand = 0
        tmpl = rec if rec._name == 'product.template' else rec.product_tmpl_id
        cont = bool(getattr(tmpl, 'allow_out_of_stock_order', False))
        if on_hand > 0:
            return True, 'in_warehouse'
        if cont:
            return True, 'available'
        return False, 'out_of_stock'

    def _fn_get_reviewers(self, args):
        """Return available human reviewers/specialists for a product.
        Online first; if none online, fall back to approved offline so Beena
        can still recommend someone instead of saying 'none available'."""
        pid = int(args.get('product_id') or 0)
        Profile = request.env['reviewer.profile'].sudo()
        enabled = request.env['ir.config_parameter'].sudo().get_param(
            'uellow_reviewers.enabled', 'True') in ('True', '1', 'true')
        if not enabled:
            return {'reviewers': [], 'total': 0, 'enabled': False}

        product = request.env['product.template'].sudo().browse(pid) if pid else None

        base = [('state', '=', 'approved')]
        online = []
        # 1) online, category-matched first
        if product and product.exists() and product.categ_id:
            online = Profile.search(
                base + [('is_online', '=', True), ('specialty_ids', 'in', [product.categ_id.id])],
                limit=6, order='rating desc, review_count desc')
            if len(online) < 6:
                fill = Profile.search(
                    base + [('is_online', '=', True), ('id', 'not in', online.ids)],
                    limit=6 - len(online), order='rating desc, review_count desc')
                online = online | fill
        else:
            online = Profile.search(base + [('is_online', '=', True)],
                                    limit=6, order='rating desc, review_count desc')

        used = online
        any_online = bool(online)
        # 2) fallback: approved offline if nobody online
        if not used:
            used = Profile.search(base, limit=4, order='rating desc, review_count desc')

        level_labels = {'starter': '⭐ Starter', 'regular': '⭐⭐ Regular',
                        'expert': '⭐⭐⭐ Expert', 'elite': '⭐⭐⭐⭐ Elite'}
        def _ser(r):
            return {
                'id': r.id,
                'name': r.display_name or '',
                'level': r.level or 'starter',
                'level_label': level_labels.get(r.level, ''),
                'rating': round(r.rating, 1),
                'review_count': r.review_count,
                'is_online': r.is_online,
                'specialty_text': r.specialty_text or (', '.join(r.specialty_ids.mapped('name')) if r.specialty_ids else ''),
                'allow_written': r.allow_written,
                'allow_chat': r.allow_chat,
                'avatar_url': '/web/image/reviewer.profile/%d/avatar/64x64' % r.id,
            }

        # verdict stats for this product (if any)
        stats = {}
        if pid:
            Req = request.env['review.request'].sudo()
            done = Req.search([('product_id', '=', pid), ('state', '=', 'completed'),
                               ('reviewer_verdict', '!=', False)])
            rec = len(done.filtered(lambda x: x.reviewer_verdict == 'recommend'))
            tot = len(done)
            stats = {'recommend': rec, 'total': tot,
                     'recommend_pct': round((rec / tot) * 100) if tot else 0}

        return {
            'available': True,
            'reviewers': [_ser(r) for r in used],
            'total': len(used),
            'online_count': len(online),
            'all_offline': not any_online,
            'enabled': True,
            'stats': stats,
        }

    def _fn_get_upsell(self, args):
        """Upsell suggestions = reuse recommendations for the product."""
        try:
            res = self._fn_get_recommendations(args)
            recs = res.get('recommendations') or res.get('products') or []
            return {'products': recs, 'total': len(recs)}
        except Exception as e:
            _logger.warning('upsell fallback: %s', e)
            return {'products': [], 'total': 0}

    def _fn_get_loyalty_points(self, args):
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'available': True, 'logged_in': False,
                    'guest': True, 'message': 'سجّل دخولك لعرض نقاطك'}
        partner = request.env.user.partner_id
        # Read from loyalty.card — the LIVE system the account page shows,
        # so Beena always matches what the customer sees in their account.
        points = 0
        try:
            cards = request.env['loyalty.card'].sudo().search(
                [('partner_id', '=', partner.id)])
            points = int(round(sum(cards.mapped('points')))) if cards else 0
        except Exception as e:
            _logger.warning('loyalty.card read: %s', e)

        # Tier thresholds + redeem rate from the active uellow program (config only)
        silver_min, gold_min, plat_min = 1000, 5000, 15000
        redeem_rate = 100
        try:
            prog = request.env['uellow.loyalty.program'].sudo().search(
                [('active', '=', True)], limit=1)
            if prog:
                silver_min = int(prog.tier_silver_min or silver_min)
                gold_min = int(prog.tier_gold_min or gold_min)
                plat_min = int(prog.tier_platinum_min or plat_min)
                redeem_rate = int(prog.points_per_kd_redeem or redeem_rate) or 100
        except Exception as e:
            _logger.warning('loyalty program read: %s', e)

        # Derive tier from points against thresholds
        if points >= plat_min:
            tier, level_label = 'platinum', 'بلاتيني'
        elif points >= gold_min:
            tier, level_label = 'gold', 'ذهبي'
        elif points >= silver_min:
            tier, level_label = 'silver', 'فضي'
        else:
            tier, level_label = 'bronze', 'برونزي'

        tiers = [('bronze', 0), ('silver', silver_min),
                 ('gold', gold_min), ('platinum', plat_min)]
        cur_idx = [t[0] for t in tiers].index(tier)
        to_next = 0
        progress = 100
        if cur_idx < len(tiers) - 1:
            next_threshold = tiers[cur_idx + 1][1]
            cur_threshold = tiers[cur_idx][1]
            to_next = max(0, next_threshold - points)
            span = max(1, next_threshold - cur_threshold)
            progress = min(100, max(0, int(((points - cur_threshold) / span) * 100)))

        kd_value = round(points / redeem_rate, 3) if redeem_rate else 0
        kd_value_text = ('%.3f KD' % kd_value)  # ready-to-show, e.g. '221.500 KD'

        return {
            'available': True,
            'logged_in': True,
            'points': points,
            'tier': tier,
            'level': tier,
            'level_label': level_label,
            'lifetime_points': points,
            'kd_value': kd_value,
            'kd_value_text': kd_value_text,
            'to_next': to_next,
            'progress': progress,
            'partner': partner.name,
        }

    def _fn_get_size_recommendation(self, args):
        """Recommend a size by reading the customer's body profile and analyzing
        it against the product's size chart. Reuses uellow_smart_fit logic."""
        product_id = args.get('product_id')

        # 1) Guest → must register first
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'available': True, 'logged_in': False,
                    'message': 'عشان أنصحك بمقاسك المثالي، سجّل دخولك أول 🌟 وبعدها أجهّز لك التوصية.'}

        partner = request.env.user.partner_id

        # 2) Find / check body profile
        profile = request.env['customer.body.profile'].sudo().search(
            [('partner_id', '=', partner.id)], limit=1)
        if not profile or not profile.profile_complete:
            pct = profile.completion_pct if profile else 0
            return {'available': True, 'logged_in': True, 'profile_complete': False,
                    'completion_pct': pct,
                    'message': 'محتاج بياناتك عشان أحسب مقاسك بدقة 😊 عطني طولك، وزنك، '
                               'قياس صدرك والكتف (والوسط لو عندك). تقدر كمان تكمّل ملفك من صفحة Smart Fit.'}

        # 3) Have a complete profile — analyze against the product if given
        if not product_id:
            return {'available': True, 'logged_in': True, 'profile_complete': True,
                    'message': 'ملف قياساتك جاهز ✅ افتح المنتج اللي يعجبك وأنا أقترح لك المقاس المناسب.',
                    'profile': {
                        'height': profile.height, 'weight': profile.weight,
                        'chest': profile.chest, 'preferred_fit': profile.preferred_fit,
                    }}

        try:
            from odoo.addons.uellow_smart_fit.controllers.fit_controller import SmartFitController
            fit = SmartFitController()
            product = request.env['product.template'].sudo().browse(int(product_id))
            if not product.exists():
                return {'available': True, 'logged_in': True, 'error': 'product_not_found'}

            profile_data = {
                'chest': profile.chest, 'waist': profile.waist,
                'shoulder': profile.shoulder, 'hip': profile.hip,
                'height': profile.height, 'shoe_size_eu': profile.shoe_size_eu,
                'preferred_fit': profile.preferred_fit or 'regular',
            }
            sizes    = fit._get_product_sizes(product)
            category = fit._detect_category(product)
            results  = fit._analyze_fit(profile_data, sizes, category)

            return {
                'available': True, 'logged_in': True, 'profile_complete': True,
                'recommended': results[0]['size'] if results else None,
                'results': results[:3],
                'category': category,
                'product_name': product.name,
            }
        except Exception as e:
            _logger.warning('size recommendation failed: %s', e)
            return {'available': True, 'logged_in': True,
                    'message': 'صار خطأ بسيط وأنا أحلّل مقاسك، جرّب مرة ثانية 🙏'}

    def _fn_start_virtual_tryon(self, args):
        """Check whether the customer can start a virtual try-on for a product.
        Returns a state the JS card uses to show login/upload/deny/proceed.
        NOTE: this does NOT call Replicate — the JS card calls /tryon/generate
        directly after collecting the photo if needed."""
        product_id = args.get('product_id')

        # Master switch
        enabled = self._get_param('tryon_enabled', 'False') in ('True', '1', 'true')
        if not enabled:
            # v2.2.05 — honest "coming soon" + redirect to the size
            # recommendation (Coach findings 627/615: Beena kept retrying
            # a feature that isn't live yet).
            return {'available': False, 'state': 'disabled',
                    'do_not_retry': True,
                    'message': self._t(
                        "Virtual try-on is coming VERY soon 🚀 — meanwhile "
                        "I can recommend your perfect size for this product. "
                        "Want me to?",
                        "التجربة الافتراضية جاية قريباً جداً 🚀 — وبالوقت "
                        "الحالي أقدر أنصحك بمقاسك المثالي لهذا المنتج، "
                        "تبي؟",
                    )}

        # Guest → must register
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'available': True, 'state': 'needs_login',
                    'message': self._t(
                        "To try the product on yourself virtually, please sign in first 🌟 then I'll continue with you.",
                        "عشان تجرّب المنتج عليك افتراضياً، سجّل دخولك أول 🌟 وبعدها أكمل معاك.",
                    )}

        partner = request.env.user.partner_id

        if not product_id:
            return {'available': True, 'state': 'no_product',
                    'message': self._t(
                        "Open the product you want to try and I'll continue with you 😊",
                        "افتح المنتج اللي تبي تجرّبه وأنا أتابع معاك 😊",
                    )}

        product = request.env['product.template'].sudo().browse(int(product_id))
        if not product.exists():
            return {'available': True, 'state': 'product_not_found'}

        # Eligibility (category + min price)
        try:
            from odoo.addons.uellow_smart_fit.controllers.tryon_controller import TryOnController
            ctl = TryOnController()
            ok, reason, info = ctl._product_eligible(product)
            if not ok:
                msg_map = {
                    'price_below_min':          self._t("This product is below the minimum price for virtual try-on.", "هذا المنتج تحت الحد الأدنى للتجربة الافتراضية."),
                    'category_not_eligible':    self._t("Virtual try-on is currently available for clothing only.",     "التجربة الافتراضية متاحة حالياً للملابس فقط."),
                    'no_categories_configured': self._t("Virtual try-on is not configured yet.",                         "التجربة الافتراضية مو مُعدّة بعد."),
                }
                msg = msg_map.get(reason, self._t(
                    "This product is not eligible for virtual try-on.",
                    "هذا المنتج غير مؤهّل للتجربة الافتراضية.",
                ))
                return {'available': True, 'state': 'not_eligible',
                        'reason': reason, 'info': info, 'message': msg,
                        'product_id': product.id, 'product_name': product.name}

            # Caps
            ok, reason, info = ctl._check_caps(partner)
            if not ok:
                msg = self._t(
                    "We've reached today's try-on limit, please try later 🙏",
                    "وصلنا للحد الأقصى للتجارب اليوم، حاول لاحقاً 🙏",
                )
                return {'available': True, 'state': 'cap_reached',
                        'reason': reason, 'info': info, 'message': msg}

            # Photo?
            profile = request.env['customer.body.profile'].sudo().search(
                [('partner_id', '=', partner.id)], limit=1)
            has_photo = bool(profile and profile.tryon_photo)

            product_image_url = '/web/image/product.template/%s/image_512' % product.id
            try:
                price_kd = float(product.list_price or 0.0)
            except Exception:
                price_kd = 0.0

            if not has_photo:
                return {'available': True, 'state': 'needs_photo',
                        'product_id': product.id, 'product_name': product.name,
                        'product_image_url': product_image_url,
                        'product_price_kd': price_kd,
                        'has_photo': False,
                        'message': self._t(
                            "Upload a clear personal photo (full standing pose, good lighting) so I can try the product on you ✨",
                            "ارفع لي صورة شخصية واضحة (وقفة كاملة، إضاءة جيدة) عشان أجرّب المنتج عليك ✨",
                        )}

            # Ready
            photo_url = '/web/image/customer.body.profile/%s/tryon_photo' % profile.id
            return {'available': True, 'state': 'ready',
                    'product_id': product.id, 'product_name': product.name,
                    'product_image_url': product_image_url,
                    'product_price_kd': price_kd,
                    'has_photo': True,
                    'photo_url': photo_url,
                    'message': self._t(
                        "I found your saved photo 🌟 Ready to start! Press 'Try it on now' or change the photo if you like.",
                        "لقيت صورتك المحفوظة 🌟 جاهزين نبدأ! اضغط \"جرّب الآن\" أو غيّر الصورة لو حبيت.",
                    )}
        except Exception as e:
            _logger.warning('virtual tryon precheck failed: %s', e)
            return {'available': True, 'state': 'error',
                    'message': self._t(
                        "Small issue happened, please try again 🙏",
                        "صار خطأ بسيط، جرّب مرة ثانية 🙏",
                    )}

    def _fn_get_payment_options(self, args):
        # Only offer methods the store can actually process — otherwise Beena
        # promises Taly/COD that are disabled in settings.
        icp = request.env['ir.config_parameter'].sudo()
        opts = [{'name': 'UPayments', 'type': 'card', 'desc': 'بطاقة / KNET'}]
        if icp.get_param('taly.merchant_key', ''):
            opts.append({'name': 'Taly', 'type': 'bnpl', 'desc': 'قسّمها على دفعات'})
        if icp.get_param('uellow_ai.cod_enabled', 'True') in ('True', '1', 'true'):
            opts.append({'name': 'COD', 'type': 'cod', 'desc': 'الدفع عند الاستلام'})
        return {'options': opts}

    def _fn_check_fit(self, args):
        """Per-area fit check between customer profile and product size chart.
        Returns a state-driven payload for the JS card."""
        product_id = args.get('product_id')
        requested_size = (args.get('size') or '').strip()

        # Guest?
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'state': 'needs_login',
                    'message': self._t(
                        "Sign in so I can check the size fit against your body 🌟",
                        "سجّل دخولك عشان أقدر أفحص توافق المقاس مع جسمك 🌟",
                    )}

        if not product_id:
            return {'state': 'no_product',
                    'message': self._t(
                        "Open the product you want me to check.",
                        "افتح المنتج اللي تبي أفحص مقاسه.",
                    )}

        product = request.env['product.template'].sudo().browse(int(product_id))
        if not product.exists():
            return {'state': 'product_not_found'}

        partner = request.env.user.partner_id
        Profile = request.env['customer.body.profile'].sudo()
        profile = Profile.search([('partner_id', '=', partner.id)], limit=1)
        if not profile or (profile.completion_pct or 0) < 40:
            return {'state': 'needs_profile',
                    'product_id': product.id,
                    'product_name': product.name,
                    'measurements_url': '/my/measurements',
                    'message': self._t(
                        "Complete your measurements first (chest, waist, shoulder, ...) so I can give you an accurate result.",
                        "أكمل مقاساتك أول (الصدر، الوسط، الكتف، ...) عشان أعطيك نتيجة دقيقة.",
                    )}

        # Need a size chart on the product
        if not product.size_chart_ids:
            return {'state': 'no_chart',
                    'product_id': product.id,
                    'product_name': product.name,
                    'message': self._t(
                        "This product doesn't have a detailed size chart yet. I'll give you a rough recommendation from the available sizes.",
                        "هذا المنتج ما عنده جدول مقاسات تفصيلي بعد. أعطيك توصية تقريبية من المقاسات الموجودة.",
                    )}

        # Run analysis
        try:
            from odoo.addons.uellow_smart_fit.controllers.fit_controller import SmartFitController
            ctl = SmartFitController()
            category = ctl._detect_category(product)
            results  = ctl._analyze_with_chart(profile, product, category)
            if not results:
                return {'state': 'error',
                        'message': self._t(
                            "Couldn't analyze the size.",
                            "تعذّر تحليل المقاس.",
                        )}

            # Pick the requested size or the recommended
            chosen = None
            if requested_size:
                chosen = next((r for r in results if r['size'].lower() == requested_size.lower()), None)
            if not chosen:
                chosen = next((r for r in results if r.get('recommended')), results[0])
            chosen['category'] = category

            # Persist this check
            ctl._save_fit_check(profile, product, chosen, source='beena_check')

            # Build alt sizes (top 3 excluding chosen)
            alt = [r for r in results if r['size'] != chosen['size']][:3]
            alt_summary = [{
                'size': r['size'], 'overall_pct': r['overall_pct'],
                'fit_label': r['fit_label'], 'fit_color': r['fit_color'],
                'recommended': r.get('recommended', False),
            } for r in alt]

            # Variant for add-to-cart — use the SmartFit resolver which prefers
            # the linked product.attribute.value over fragile substring matching.
            chart_row = product.size_chart_ids.filtered(
                lambda r: (r.size_label or '').strip().lower() == (chosen['size'] or '').strip().lower()
            )[:1]
            variant_id = ctl._resolve_variant_id(product, chart_row) if chart_row else False

            return {
                'state':             'ready',
                'product_id':        product.id,
                'product_name':      product.name,
                'product_image_url': '/web/image/product.template/%s/image_512' % product.id,
                'product_price_kd':  float(product.list_price or 0.0),
                'category':          category,
                'size':              chosen['size'],
                'overall_pct':       chosen['overall_pct'],
                'fit_label':         chosen['fit_label'],
                'fit_color':         chosen['fit_color'],
                'areas':             chosen['areas'],
                'alternates':        alt_summary,
                'variant_id':        variant_id,
                'add_to_cart_url':   '/shop/cart',
                'message':           self._t(
                    "Here is the size compatibility check against your personal measurements.",
                    "هذا فحص توافق المقاس مع مقاساتك الشخصية.",
                ),
            }
        except Exception as e:
            _logger.warning('check_fit failed: %s', e)
            return {'state': 'error',
                    'message': self._t(
                        "Small issue happened, please try again 🙏",
                        "صار خطأ بسيط، حاول مرة ثانية 🙏",
                    )}

    def _fn_get_product_info(self, args):
        pid     = int(args.get('product_id', 0))
        product = request.env['product.template'].sudo().browse(pid)
        if not product.exists():
            return {'error': 'Product not found'}
        variants = []
        for v in product.product_variant_ids[:10]:
            attrs = {ptav.attribute_id.name: ptav.name
                     for ptav in v.product_template_attribute_value_ids}
            variants.append({
                'id': v.id, 'attributes': attrs,
                'price': v.lst_price,
                'in_stock': v.virtual_available > 0,
                'qty': max(0, int(v.virtual_available)),
            })
        return {
            'id': product.id, 'name': product.name,
            'price': product.list_price,
            'description': (product.get_description_plain(max_chars=500)
                            if hasattr(product, 'get_description_plain')
                            else (product.description_sale or '')[:500]),
            'category': product.categ_id.name if product.categ_id else '',
            'in_stock': self._stock_status(product)[0],
            'stock_status': self._stock_status(product)[1],
            'variants': variants,
        }

    _DEFAULT_SEARCH_TRANSLATIONS = (
        'انكر=anker\n'
        'سامسونج=samsung\n'
        'ابل=apple\n'
        'هواوي=huawei\n'
        'سوني=sony\n'
        'شاومي=xiaomi\n'
        'بوز=bose\n'
        'فيليبس=philips\n'
        'هاينو=haino\n'
        'تيكو=teko\n'
        'هاينوتيكو=hainoteko\n'
        'ساعة=watch\n'
        'نسائي=female\n'
        'نسائية=female\n'
        'رجالي=male\n'
        'ذكية=smart\n'
        'سماعة=headphone\n'
        'لابتوب=laptop\n'
        'جوال=phone'
    )

    def _variable_keywords(self):
        """Keywords marking a question as 'variable info' (live, never cached).
        Default list merged with extra keywords from settings."""
        extra = self._get_param('variable_keywords', '')
        combined = _DEFAULT_VARIABLE_KEYWORDS + ',' + (extra or '')
        kws = []
        for kw in combined.replace('\n', ',').split(','):
            kw = kw.strip().lower()
            if kw and kw not in kws:
                kws.append(kw)
        return kws

    def _search_translations(self):
        """Read translation pairs (ar=en per line) from settings, merged with defaults."""
        extra = self._get_param('search_translations', '')
        combined = self._DEFAULT_SEARCH_TRANSLATIONS + '\n' + (extra or '')
        pairs = {}
        for line in combined.split('\n'):
            line = line.strip()
            if not line or ('=' not in line and ':' not in line):
                continue
            sep = '=' if '=' in line else ':'
            ar, en = line.split(sep, 1)
            ar, en = ar.strip().lower(), en.strip().lower()
            if ar and en:
                pairs[ar] = en
        return pairs

    def _extract_product_color_size(self, product):
        """Return ([{name,hex,available}], [{name,available,recommended}]) for the
        Color and Size attribute values of a product.template. Skips quietly if
        attributes are missing or the model isn't installed."""
        colors, sizes = [], []
        try:
            lines = product.attribute_line_ids
            for ln in lines:
                attr_name = (ln.attribute_id.name or '').lower()
                is_color = 'color' in attr_name or 'لون' in attr_name
                is_size  = 'size'  in attr_name or 'مقاس' in attr_name or 'حجم' in attr_name
                if not (is_color or is_size):
                    continue
                # Build a quick {value_id: any_in_stock} from variants
                in_stock_by_value = {}
                for v in product.product_variant_ids:
                    avail = (v.virtual_available > 0) or v.qty_available > 0
                    for ptav in v.product_template_attribute_value_ids:
                        key = ptav.product_attribute_value_id.id
                        in_stock_by_value[key] = in_stock_by_value.get(key, False) or avail
                for val in ln.value_ids:
                    available = in_stock_by_value.get(val.id, True)
                    if is_color:
                        colors.append({
                            'name':      val.name,
                            'hex':       getattr(val, 'html_color', '') or '',
                            'available': available,
                        })
                    else:
                        sizes.append({
                            'name':      val.name,
                            'available': available,
                        })
        except Exception as _e:
            _logger.debug('extract color/size failed: %s', _e)
        return colors, sizes

    def _fn_search_products(self, args):
        query    = (args.get('query') or '').strip()
        limit    = int(args.get('limit', 5))
        category = (args.get('category') or '').strip()

        env = request.env['product.template'].sudo()
        cr  = request.env.cr

        replacements = self._search_translations()
        stop = {'for', 'the', 'a', 'an', 'of', 'with', 'و', 'في', 'من', 'ال'}

        words = set()
        q_lower = query.lower()
        for w in q_lower.replace('-', ' ').split():
            w = w.strip()
            if len(w) > 1 and w not in stop:
                words.add(w)
                for ar, en in replacements.items():
                    if w == ar or ar in w:
                        words.add(en)
                    if w == en or en in w:
                        words.add(ar)

        if not words:
            return {'products': [], 'total': 0}

        found = []
        try:
            score_sql = ' + '.join([
                "(CASE WHEN (pt.name::text ILIKE %s OR "
                "COALESCE(pt.description_sale::text,'') ILIKE %s) THEN 1 ELSE 0 END)"
                for _ in words
            ])
            params = []
            for w in words:
                params += [f'%{w}%', f'%{w}%']

            cat_cond = ''
            if category:
                cat_cond = "AND pc.complete_name ILIKE %s"

            sql = (
                "SELECT pt.id, (" + score_sql + ") AS score "
                "FROM product_template pt "
                "LEFT JOIN product_category pc ON pc.id = pt.categ_id "
                "WHERE pt.is_published = true " + cat_cond + " "
                "AND (" + score_sql + ") > 0 "
                "ORDER BY score DESC, pt.id DESC "
                "LIMIT %s"
            )
            full_params = list(params)
            if category:
                full_params.append(f'%{category}%')
            full_params += list(params)
            full_params.append(limit)
            cr.execute(sql, full_params)
            found = [(r[0], r[1]) for r in cr.fetchall()]
        except Exception as e:
            _logger.warning('Search scoring SQL failed: %s', e)
            try:
                dom = [('is_published', '=', True),
                       '|', ('name', 'ilike', query), ('description_sale', 'ilike', query)]
                found = [(i, 1) for i in env.search(dom, limit=limit).ids]
            except Exception as e2:
                _logger.error('Search ORM failed: %s', e2)
                return {'products': [], 'total': 0}

        result_list = []
        for pid, score in found[:limit]:
            prod = env.browse(pid)
            try:
                variant = prod.product_variant_ids[:1]
                qty_on_hand = max(0, int(prod.qty_available or 0))
                continue_sell = bool(getattr(prod, 'allow_out_of_stock_order', False))
                in_stock = qty_on_hand > 0 or continue_sell
                # Pull color / size attribute values for the rich UI chips.
                colors, sizes = self._extract_product_color_size(prod)
                result_list.append({
                    'id':            prod.id,
                    'variant_id':    variant.id if variant else None,
                    'name':          prod.name,
                    'price':         prod.list_price,
                    'category':      prod.categ_id.name if prod.categ_id else '',
                    'in_stock':      in_stock,
                    'qty_available': qty_on_hand,
                    'continue_sell': continue_sell,
                    # v2.2.05 — 512px (was 128 → blurry chat cards).
                    'image_url':     f'/web/image/product.template/{prod.id}/image_512',
                    'match_score':   score,
                    'colors':        colors,
                    'sizes':         sizes,
                })
            except Exception:
                pass

        _logger.info('Search "%s" words=%s found=%d', query, words, len(result_list))
        return {'products': result_list, 'total': len(result_list)}

    def _fn_check_stock(self, args):
        pid     = int(args.get('product_id', 0))
        attrs   = args.get('variant_attributes', {})
        product = request.env['product.template'].sudo().browse(pid)
        if not product.exists():
            return {'error': 'Product not found'}
        if not attrs:
            _ok, _st = self._stock_status(product)
            return {'in_stock': _ok, 'stock_status': _st,
                    'qty': max(0, int(product.qty_available))}
        for v in product.product_variant_ids:
            v_attrs = {ptav.attribute_id.name: ptav.name
                       for ptav in v.product_template_attribute_value_ids}
            if all(v_attrs.get(k) == val for k, val in attrs.items()):
                return {'in_stock': v.virtual_available > 0,
                        'qty': max(0, int(v.virtual_available)),
                        'variant_id': v.id}
        return {'error': 'Variant not found'}

    def _fn_add_to_cart(self, args):
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'success': False, 'guest': True, 'message': 'اضغط +سلة على المنتج مباشرة'}
        try:
            product_id = int(args.get('product_id') or 0)
            variant_id = int(args.get('variant_id') or 0)
            qty = int(args.get('quantity') or 1)
            if product_id and not variant_id:
                tmpl = request.env['product.template'].sudo().browse(product_id)
                if tmpl.exists() and tmpl.product_variant_ids:
                    variant_id = tmpl.product_variant_ids[0].id
            if not variant_id:
                return {'success': False, 'error': 'variant_id required'}
            product = request.env['product.product'].sudo().browse(variant_id)
            if not product.exists():
                return {'success': False, 'error': 'product not found'}
            website = request.env['website'].sudo().search([], limit=1)
            if not website:
                return {'success': False, 'error': 'no website'}
            order = website.sale_get_order(force_create=True)
            if not order:
                return {'success': False, 'error': 'no cart'}
            # Coach fix: a transient failure here used to abandon the whole
            # checkout flow mid-transaction. Retry once before giving up, and
            # on persistent failure return a concrete fallback the assistant
            # can offer instead of dead-ending the customer.
            try:
                order._cart_update(product_id=variant_id, add_qty=qty)
            except Exception:
                request.env.cr.rollback()
                order = website.sale_get_order(force_create=True)
                order._cart_update(product_id=variant_id, add_qty=qty)
            return {'success': True, 'product': product.name, 'quantity': qty,
                    'cart_count': int(order.cart_quantity), 'cart_total': order.amount_total,
                    'cart_url': '/shop/cart', 'message': f'تمت إضافة {product.name} للسلة'}
        except Exception:
            _logger.exception('Beena add_to_cart failed')
            return {'success': False, 'error': 'add_failed',
                    'fallback_url': '/shop/cart',
                    'message': 'تعذرت الإضافة تلقائياً — اعرض على العميل رابط السلة المباشر'}


    def _fn_create_order(self, args):
        try:
            public_user = request.env.ref('base.public_user')
            if request.env.user.id == public_user.id:
                return {'error': 'guest', 'guest': True,
                        'message': 'سجّل دخولك أو أكمل الشراء من صفحة المنتج'}
            pid   = int(args.get('product_id', 0))
            qty   = int(args.get('quantity', 1))
            name  = args.get('customer_name', '')
            phone = args.get('customer_phone', '')
            email = args.get('customer_email', '')
            product = request.env['product.product'].sudo().browse(pid)
            if not product.exists():
                tmpl = request.env['product.template'].sudo().browse(pid)
                if tmpl.exists() and tmpl.product_variant_ids:
                    product = tmpl.product_variant_ids[0]
                else:
                    return {'error': f'Product {pid} not found'}
            partner = request.env.user.partner_id
            # Only FILL BLANK contact fields from the chat — NEVER overwrite the
            # customer's real account name/phone/email (an "order it for Ahmad"
            # message must not rename the logged-in customer's own account).
            vals = {}
            if name and not partner.name:
                vals['name'] = name
            if phone and not (partner.phone or partner.mobile):
                vals['phone'] = phone
            if email and not partner.email:
                vals['email'] = email
            if vals:
                partner.sudo().write(vals)
            website = request.env['website'].sudo().search([], limit=1)
            if not website:
                return {'error': 'No website found'}
            order = website.sale_get_order(force_create=True)
            if not order:
                return {'error': 'Could not create order'}
            # Tag the order as originating from Beena (for analytics)
            if not order.origin or 'Beena' not in (order.origin or ''):
                order.sudo().write({'origin': 'Beena AI'})
            order._cart_update(product_id=product.id, add_qty=qty)
            upay_url = request.env['ir.config_parameter'].sudo().get_param(
                'upay_payment_link_url', f'/shop/payment?sale_order_id={order.id}'
            )
            return {'success': True, 'order_id': order.id, 'order_name': order.name,
                    'amount': order.amount_total, 'upay_url': upay_url, 'cart_url': '/shop/cart'}
        except Exception:
            _logger.exception('Beena create_order failed')
            return {'error': 'create_failed',
                    'message': 'تعذّر إنشاء الطلب — جرّب من صفحة المنتج مباشرة'}


    def _fn_get_company_location(self, args):
        """Return the company location + contact + photos configured in Settings."""
        name    = self._get_param('company_name',     'Uellow')
        address = self._get_param('company_address',  '')
        phone   = self._get_param('company_phone',    '')
        wa      = self._get_param('company_whatsapp', '')
        hours   = self._get_param('company_hours',    '')
        lat_s   = self._get_param('company_lat',      '0')
        lng_s   = self._get_param('company_lng',      '0')
        map_url = self._get_param('company_map_url',  '')
        photos  = self._get_param('company_photo_urls', '')
        try:    lat = float(lat_s)
        except Exception: lat = 0.0
        try:    lng = float(lng_s)
        except Exception: lng = 0.0
        # Split photo URLs (one per line)
        photo_list = [p.strip() for p in (photos or '').splitlines() if p.strip()]
        return {
            'name':       name,
            'address':    address,
            'phone':      phone,
            'whatsapp':   wa,
            'hours':      hours,
            'lat':        lat,
            'lng':        lng,
            'map_url':    map_url,
            'photos':     photo_list,
        }

    # ── Cart awareness + Beena-tagged checkout flow ──────────────────────

    def _fn_get_cart(self, args):
        """Return current website cart for the logged-in customer."""
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'success': False, 'guest': True,
                    'message': self._t('Please sign in to see your cart.',
                                       'سجّل دخولك عشان أعرض لك سلتك.')}
        try:
            website = request.env['website'].sudo().search([], limit=1)
            order = website.sale_get_order() if website else False
            if not order or not order.order_line:
                return {'success': True, 'empty': True,
                        'message': self._t('Your cart is empty.',
                                            'سلتك فاضية حالياً.')}
            lines = []
            for ln in order.order_line:
                if ln.display_type:
                    continue
                lines.append({
                    'id':          ln.id,
                    'product_id':  ln.product_id.id,
                    'name':        ln.product_id.display_name or ln.name or '',
                    'image_url':   '/web/image/product.product/%d/image_512' % ln.product_id.id,
                    'qty':         float(ln.product_uom_qty or 0),
                    'unit_price':  float(ln.price_unit or 0),
                    'subtotal':    float(ln.price_subtotal or 0),
                })
            return {
                'success':     True,
                'empty':       False,
                'order_id':    order.id,
                'order_name':  order.name,
                'lines':       lines,
                'item_count':  int(order.cart_quantity or 0),
                'amount_untaxed': float(order.amount_untaxed or 0),
                'amount_total':   float(order.amount_total or 0),
                'currency':       (order.currency_id.name if order.currency_id else 'KD'),
                'cart_url':       '/shop/cart',
                'checkout_url':   '/shop/checkout',
            }
        except Exception as e:
            _logger.warning('_fn_get_cart failed: %s', e)
            return {'success': False, 'error': 'cart_error'}

    def _partner_missing_fields(self, partner):
        """Return a list of address fields that are still missing on the partner."""
        missing = []
        if not (partner.phone or partner.mobile):
            missing.append('phone')
        if not partner.state_id and not partner.zip:
            missing.append('governorate')
        if not partner.city:
            missing.append('city')
        if not partner.street:
            missing.append('street')
        return missing

    def _fn_start_checkout(self, args):
        """Begin checkout: read the partner address, identify what's missing."""
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'state': 'needs_login',
                    'message': self._t('Please sign in to place the order.',
                                       'سجّل دخولك عشان أكمّل الطلب.')}

        website = request.env['website'].sudo().search([], limit=1)
        order = website.sale_get_order() if website else False
        if not order or not order.order_line:
            return {'state': 'empty_cart',
                    'message': self._t('Your cart is empty — add a product first.',
                                       'سلتك فاضية — أضف منتج أول.')}

        partner = request.env.user.partner_id
        missing = self._partner_missing_fields(partner)
        return {
            'state':       'collecting' if missing else 'ready',
            'order_id':    order.id,
            'item_count':  int(order.cart_quantity or 0),
            'amount_total':float(order.amount_total or 0),
            'currency':    (order.currency_id.name if order.currency_id else 'KD'),
            'address': {
                'phone':       partner.phone or partner.mobile or '',
                'governorate': partner.state_id.name if partner.state_id else '',
                'city':        partner.city or '',
                'street':      partner.street or '',
            },
            'missing':     missing,
        }

    def _fn_update_address(self, args):
        """Save provided address fields on the partner; return the new missing list."""
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'state': 'needs_login'}

        partner = request.env.user.partner_id
        vals = {}
        phone = (args.get('phone') or '').strip()
        if phone:
            vals['phone'] = phone
        gov = (args.get('governorate') or '').strip()
        if gov:
            # Try to resolve a country state by name (case-insensitive)
            State = request.env['res.country.state'].sudo()
            country = partner.country_id or request.env.ref('base.kw', raise_if_not_found=False)
            state_dom = [('name', '=ilike', gov)]
            if country:
                state_dom.append(('country_id', '=', country.id))
            s = State.search(state_dom, limit=1)
            if s:
                vals['state_id'] = s.id
                if country and not partner.country_id:
                    vals['country_id'] = country.id
            else:
                # Stash on zip-like field if no matching state
                vals['zip'] = gov
        city = (args.get('city') or '').strip()
        if city:
            vals['city'] = city
        street = (args.get('street') or '').strip()
        if street:
            vals['street'] = street
        if vals:
            try:
                partner.sudo().write(vals)
            except Exception as e:
                _logger.warning('update_address write failed: %s', e)
                return {'state': 'error', 'error': str(e)[:200]}

        partner = partner.sudo().browse(partner.id)  # refresh
        missing = self._partner_missing_fields(partner)
        return {
            'state':   'collecting' if missing else 'ready',
            'missing': missing,
            'address': {
                'phone':       partner.phone or partner.mobile or '',
                'governorate': partner.state_id.name if partner.state_id else (partner.zip or ''),
                'city':        partner.city or '',
                'street':      partner.street or '',
            },
            'saved': list(vals.keys()),
        }

    def _fn_complete_checkout(self, args):
        """Create a Beena-tagged Quotation from the current cart."""
        from datetime import datetime as _dt
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'state': 'needs_login'}

        website = request.env['website'].sudo().search([], limit=1)
        order = website.sale_get_order() if website else False
        if not order or not order.order_line:
            return {'state': 'empty_cart'}

        partner = request.env.user.partner_id
        missing = self._partner_missing_fields(partner)
        if missing:
            return {'state': 'collecting', 'missing': missing,
                    'message': self._t('Still need a few details before I can create the order.',
                                       'لسه باقي تفاصيل قبل ما أسجّل الطلب.')}

        # Tag the existing cart order as a Beena Order. We do NOT confirm it
        # automatically — it stays as a Quotation pending payment/admin review.
        try:
            session_id = (request.session.uid and str(request.session.sid or '')) or ''
        except Exception:
            session_id = ''

        vals = {
            'is_beena_order':   True,
            'beena_session_id': session_id[:40],
            'beena_created_at': _dt.now(),
            'beena_customer_phone':       partner.phone or partner.mobile or '',
            'beena_customer_governorate': partner.state_id.name if partner.state_id else (partner.zip or ''),
            'beena_customer_city':        partner.city or '',
            'beena_customer_street':      partner.street or '',
        }
        # Annotate origin if not already
        if not order.origin or 'Beena' not in (order.origin or ''):
            vals['origin'] = (order.origin or '') + (' · ' if order.origin else '') + 'Beena AI'
        try:
            order.sudo().write(vals)
            # Move from cart "no state" to sent so admin sees it queued
            if order.state == 'draft':
                try:
                    order.action_quotation_sent()
                except Exception:
                    pass
        except Exception as e:
            _logger.warning('complete_checkout tag failed: %s', e)
            return {'state': 'error', 'error': str(e)[:200]}

        return {
            'state':         'created',
            'order_id':      order.id,
            'order_name':    order.name,
            'amount_total':  float(order.amount_total or 0),
            'currency':      (order.currency_id.name if order.currency_id else 'KD'),
            'item_count':    int(order.cart_quantity or 0),
            'checkout_url':  '/shop/payment?sale_order_id=%d' % order.id,
            'order_url':     '/my/orders/%d' % order.id,
            'address': {
                'phone':       partner.phone or partner.mobile or '',
                'governorate': partner.state_id.name if partner.state_id else (partner.zip or ''),
                'city':        partner.city or '',
                'street':      partner.street or '',
            },
        }

    def _fn_get_payment_link(self, args):
        oid   = int(args.get('order_id', 0))
        order = request.env['sale.order'].sudo().browse(oid)
        if not order.exists():
            return {'error': 'Order not found'}
        # SECURITY: only mint a pay link / reveal the amount for the logged-in
        # customer own order (order_id comes from the chat).
        _pub = request.env.ref('base.public_user')
        if request.env.user.id == _pub.id:
            return {'error': 'login_required'}
        if not request.env.user.has_group('base.group_system'):
            _cp = request.env.user.partner_id.commercial_partner_id
            if order.partner_id.commercial_partner_id.id != _cp.id:
                return {'error': 'Order not found'}

        checkout_url = f'/shop/payment?sale_order_id={oid}'

        upay_base = request.env['ir.config_parameter'].sudo().get_param(
            'upay_payment_link_url', ''
        )
        taly_enabled = bool(request.env['ir.config_parameter'].sudo().get_param(
            'taly.merchant_key', ''
        ))
        cod_enabled = request.env['ir.config_parameter'].sudo().get_param(
            'uellow_ai.cod_enabled', 'True'
        ) in ('True', '1', 'true')

        return {
            'order_name':   order.name,
            'amount':       order.amount_total,
            'upay_url':     upay_base or checkout_url,
            'taly_enabled': taly_enabled,
            'cod_enabled':  cod_enabled,
            'checkout_url': checkout_url,
            'order_id':     order.id,
        }

    def _fn_get_order_status(self, args):
        order = None
        if args.get('order_id'):
            order = request.env['sale.order'].sudo().browse(int(args['order_id']))
        elif args.get('order_name'):
            order = request.env['sale.order'].sudo().search(
                [('name', '=', args['order_name'])], limit=1
            )
        if not order or not order.exists():
            return {'error': 'Order not found'}
        # SECURITY: order_id/order_name come straight from the chat, so only ever
        # reveal an order that belongs to the logged-in customer — never another
        # customer's status/address/driver (was an unscoped sudo lookup).
        _pub = request.env.ref('base.public_user')
        if request.env.user.id == _pub.id:
            return {'error': 'login_required'}
        if not request.env.user.has_group('base.group_system'):
            _cp = request.env.user.partner_id.commercial_partner_id
            if order.partner_id.commercial_partner_id.id != _cp.id:
                return {'error': 'Order not found'}

        state_map = {
            'draft':    'مسودة',
            'sent':     'مرسل',
            'sale':     'مؤكد',
            'done':     'مكتمل',
            'cancel':   'ملغي',
        }

        delivery_status = getattr(order, 'delivery_status', None)
        delivery_map = {
            'pending':          'في الانتظار',
            'arrived_sorting':  'وصل مركز الفرز',
            'assigned':         'تم تعيين سائق',
            'out_for_delivery': 'في الطريق إليك 🚚',
            'delivered':        'تم التسليم ✓',
            'failed':           'فشل التسليم',
            'failed_returned':  'مرتجع',
        }

        # Driver info if assigned
        driver_info = ''
        if delivery_status == 'assigned' and hasattr(order, 'driver_id'):
            try:
                if order.driver_id:
                    driver_info = f'السائق: {order.driver_id.name}'
            except Exception:
                pass

        # Estimated delivery
        eta = ''
        if delivery_status == 'out_for_delivery':
            eta = 'متوقع الوصول خلال 1-3 ساعات'
        elif delivery_status == 'assigned':
            eta = 'سيبدأ التوصيل قريباً'

        # Build a professional timeline showing every delivery step + which is current.
        STEPS = [
            ('pending',          self._t('Order received',      'تم استلام الطلب'),  '🧾'),
            ('arrived_sorting',  self._t('At sorting center',   'في مركز الفرز'),    '🏬'),
            ('assigned',         self._t('Driver assigned',     'تم تعيين سائق'),   '🧑‍✈️'),
            ('out_for_delivery', self._t('Out for delivery',    'في الطريق إليك'),   '🚚'),
            ('delivered',        self._t('Delivered',           'تم التسليم'),       '✓'),
        ]
        current = delivery_status or 'pending'
        current_idx = next((i for i, s in enumerate(STEPS) if s[0] == current), 0)
        if current in ('failed', 'failed_returned'):
            current_idx = len(STEPS) - 1
        timeline = []
        for i, (key, label, icon) in enumerate(STEPS):
            status = 'done' if i < current_idx else ('current' if i == current_idx else 'pending')
            if current in ('failed', 'failed_returned') and i == current_idx:
                status = 'failed'
            timeline.append({
                'key':    key,
                'label':  label,
                'icon':   icon,
                'status': status,
            })

        # Driver phone only AFTER Start Delivery (out_for_delivery)
        driver_phone = ''
        if (getattr(order, 'delivery_status', None) == 'out_for_delivery'
                and getattr(order, 'driver_id', False)):
            driver_phone = getattr(order.driver_id, 'phone', '') or getattr(order.driver_id, 'mobile', '')

        tracking_number = getattr(order, 'carrier_tracking_ref', '') or ''

        return {
            'order_name':       order.name,
            'order_id':         order.id,
            'amount':           order.amount_total,
            'currency':         (order.currency_id.name if order.currency_id else 'KD'),
            'state':            state_map.get(order.state, order.state),
            'state_key':        order.state,
            'delivery_status':  delivery_map.get(delivery_status, delivery_status or 'غير محدد'),
            'delivery_key':     delivery_status or '',
            'date_order':       str(order.date_order)[:16] if order.date_order else '',
            'partner':          order.partner_id.name,
            'driver':           driver_info,
            'driver_phone':     driver_phone,
            'tracking_number':  tracking_number,
            'eta':              eta,
            'can_cancel':       order.state in ('draft', 'sent'),
            'timeline':         timeline,
            'order_url':        '/my/orders/%d' % order.id,
            'is_failed':        current in ('failed', 'failed_returned'),
            'is_delivered':     current == 'delivered',
        }

    def _fn_get_clearance_picks(self, args):
        """Clearance / promote-able idle stock that Smart Connector flagged
        for Beena to surface (idea #26 tie-in). Empty list if the Smart
        Connector module isn't installed."""
        limit = int(args.get('limit') or 5)
        if 'uellow.dead.stock' not in request.env:
            return {'items': [], 'count': 0}
        try:
            rows = request.env['uellow.dead.stock'].sudo().beena_promotable_products(
                limit=limit)
        except Exception:
            rows = []
        return {'items': rows, 'count': len(rows)}

    def _fn_get_recommendations(self, args):
        pid     = int(args.get('product_id', 0))
        limit   = int(args.get('limit', 3))
        product = request.env['product.template'].sudo().browse(pid)
        categ   = product.categ_id.id if product.exists() and product.categ_id else False
        domain  = [('website_published', '=', True), ('id', '!=', pid)]
        if categ:
            domain.append(('categ_id', '=', categ))
        products = request.env['product.template'].sudo().search(domain, limit=limit)
        return {'recommendations': [
            {'id': p.id, 'name': p.name, 'price': p.list_price}
            for p in products
        ]}

    # DEPRECATED / REMOVED as a Beena tool (Coach 2026-07-22): this relied on the
    # `loyalty.account` + `loyalty.transaction` models, which do NOT exist in this
    # Odoo 18 install (the live loyalty system is `loyalty.card`). The old code
    # always returned {'available': False} yet its tool description advertised
    # "Award 50 loyalty points", which pushed Beena to promise review points she
    # could never grant (real case: conversation #254). Points for genuine reviews
    # are handled automatically by the store; there is no chat-triggered award.
    # Kept as a safe stub (unwired) instead of live code against a missing model.
    def _fn_award_review(self, args):
        return {'available': False,
                'message': 'نقاط المراجعات تُضاف تلقائياً بعد نشر مراجعة موثّقة.'}

    def _fn_apply_coupon(self, args):
        code = (args.get('code') or '').strip()
        if not code:
            return {'error': 'No coupon code'}
        order = request.env["website"].sudo().search([], limit=1).sale_get_order()
        if not order:
            return {'error': 'No active cart'}
        # Odoo 18: sale.coupon.apply.code was removed — use _try_apply_code,
        # then claim any rewards it returns but does not auto-apply.
        try:
            res = order.sudo()._try_apply_code(code)
        except Exception as e:
            return {'error': str(e), 'message': 'الكوبون غير صحيح أو منتهي الصلاحية'}
        if isinstance(res, dict) and res.get('error'):
            return {'error': res['error'],
                    'message': 'الكوبون غير صحيح أو منتهي الصلاحية'}
        try:
            if isinstance(res, dict):
                for coupon, rewards in res.items():
                    if hasattr(coupon, 'id'):
                        for rw in rewards:
                            order.sudo()._apply_program_reward(rw, coupon)
        except Exception:
            pass
        return {'success': True, 'message': f'تم تطبيق الكوبون {code} ✅'}

    def _fn_get_customer_orders(self, args):
        limit       = int(args.get('limit', 5))
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'error': 'Customer not logged in'}
        partner = request.env.user.partner_id
        orders  = request.env['sale.order'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done', 'sent']),
        ], limit=limit, order='date_order desc')
        # v2.1.81 — include id + delivery status so the app renders each order
        # with its status and a per-order Track button.
        _dlabels = {
            'pending':          {'en': 'Pending',          'ar': 'قيد المعالجة'},
            'arrived_sorting':  {'en': 'At sorting center', 'ar': 'في مركز الفرز'},
            'assigned':         {'en': 'Assigned',         'ar': 'تم الإسناد'},
            'out_for_delivery': {'en': 'Out for delivery', 'ar': 'في الطريق إليك'},
            'delivered':        {'en': 'Delivered',        'ar': 'تم التوصيل'},
            'failed':           {'en': 'Failed',           'ar': 'فشل التوصيل'},
            'failed_returned':  {'en': 'Returned',         'ar': 'تم الإرجاع'},
        }
        _lang = (request.env.context.get('lang') or 'ar')[:2]
        out = []
        for o in orders:
            dk = getattr(o, 'delivery_status', '') or ''
            lbl = _dlabels.get(dk, {}).get('ar' if _lang == 'ar' else 'en', '')
            out.append({
                'id': o.id, 'name': o.name, 'amount': o.amount_total,
                'state': o.state, 'date': str(o.date_order)[:10],
                'delivery_key': dk, 'delivery_status': lbl,
            })
        return {'orders': out}

    # ── Claude API ────────────────────────────────────────────────────────────

    def _select_tools(self, message):
        """Return core tools always, plus any secondary tool whose trigger
        words appear in the user's message. Fail-safe: returns all tools on error."""
        try:
            msg = (message or '').lower()
            selected = [t for t in TOOLS if t['name'] in CORE_TOOLS]
            for tool_name, triggers in TOOL_TRIGGERS.items():
                if any(kw.lower() in msg for kw in triggers):
                    extra = next((t for t in TOOLS if t['name'] == tool_name), None)
                    if extra and extra not in selected:
                        selected.append(extra)
            return selected or TOOLS
        except Exception:
            return TOOLS

    def _call_claude(self, messages, system_prompt, model, max_tokens, tools=None):
        api_key = self._get_param('claude_api_key', '')
        if not api_key:
            return None, 'Claude API key not configured'

        # Prompt caching (toggleable from settings): cache the large static
        # blocks (system prompt + tools) so repeat calls cost ~10% on them.
        active_tools = tools if tools is not None else TOOLS
        cache_on = self._get_param('prompt_cache_enabled', 'True') in ('True', '1', 'true')
        if cache_on:
            system_payload = [{
                'type': 'text',
                'text': system_prompt,
                'cache_control': {'type': 'ephemeral'},
            }]
            cached_tools = [dict(t) for t in active_tools]
            if cached_tools:
                cached_tools[-1] = dict(cached_tools[-1])
                cached_tools[-1]['cache_control'] = {'type': 'ephemeral'}
            tools_payload = cached_tools
        else:
            system_payload = system_prompt
            tools_payload = active_tools

        payload = {
            'model':      model,
            'max_tokens': int(max_tokens),
            'system':     system_payload,
            'messages':   messages,
            'tools':      tools_payload,
        }
        data    = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type':      'application/json',
            'x-api-key':         api_key,
            'anthropic-version': '2023-06-01',
            'anthropic-beta':    'prompt-caching-2024-07-31',
        }
        req = urllib.request.Request(CLAUDE_API_URL, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode('utf-8')), None
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            _logger.error('Claude API error %s: %s', e.code, body)
            return None, f'Claude API error {e.code}: {body[:200]}'
        except Exception as e:
            _logger.exception('Claude request failed')
            return None, str(e)

    def _clean_text(self, text):
        """Remove markdown and state keywords from Claude response."""
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*',     r'\1', text)
        text = re.sub(r'#{1,6}\s',       '',    text)
        text = re.sub(r'---+',           '',    text)
        text = re.sub(r'\*\*state:\s*\w+\*\*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'state:\s*\w+',   '',    text, flags=re.IGNORECASE)
        text = text.strip()
        return text

    def _detect_state(self, text, fn_name=None):
        if fn_name in ('create_order', 'get_payment_link'):
            return 'happy'
        if fn_name in ('search_products', 'get_recommendations', 'check_stock', 'get_customer_orders'):
            return 'thinking'
        if not text:
            return 'thinking'
        tl = text.lower()
        if any(k in tl for k in ['عرض', 'خصم', 'تخفيض', 'مجاني', 'offer', 'discount', 'free', '!']):
            return 'excited'
        if any(k in tl for k in ['مو موجود', 'نفدت', 'ما في', 'not available', 'out of stock', 'آسف', 'sorry']):
            return 'sad'
        if any(k in tl for k in ['تم الطلب', 'مبروك', 'order created', 'تم', 'ممتاز', 'شكراً']):
            return 'happy'
        return 'talking'

    # ── Main Chat Endpoint ────────────────────────────────────────────────────

    @http.route('/ai/chat', type='json', auth='public', methods=['POST'], csrf=False)
    def chat(self, **kwargs):
        enabled = self._get_param('enabled', 'True')
        if enabled not in ('True', '1', 'true'):
            return {'error': 'AI assistant is disabled', 'state': 'idle'}

        message    = (kwargs.get('message') or '').strip()
        session_id = kwargs.get('session_id') or str(uuid.uuid4())
        product_id = kwargs.get('product_id')
        category_id = kwargs.get('category_id')

        if not message:
            return {'error': 'Empty message', 'state': 'idle'}

        if self._daily_cost_exceeded():
            _lang = (request.env.context.get('lang') or 'ar')
            _msg = ("Beena has reached today's usage limit. Please try again later."
                    if _lang.startswith('en')
                    else "وصلت Beena للحد اليومي من الاستخدام. حاول لاحقاً من فضلك 🐝")
            return {'reply': _msg, 'state': 'sad',
                    'session_id': kwargs.get('session_id') or ''}

        session = self._get_or_create_session(session_id, product_id)
        session.add_message('user', message)

        product = None
        if product_id:
            p = request.env['product.template'].sudo().browse(int(product_id))
            if p.exists():
                product = p

        # ── Answer Cache lookup (serve repeats without Claude) ──
        _cache_on = self._get_param('cache_enabled', 'False') in ('True', '1', 'true')
        # v2.1.82 — context guard: short conversational turns («نعم», «طيب»,
        # «ok»…) depend on the running conversation and must NEVER be cached
        # or served from cache. Exception: short GENERIC questions («وين
        # فرعكم») are store-wide and stay cacheable.
        _Cache = request.env['beena.qa.cache'].sudo()
        _ctx_dependent = (len((message or '').split()) < 3
                          and not _Cache.is_generic(message))
        if _cache_on and not _ctx_dependent:
            try:
                _hit = _Cache.lookup(message, product_id, None)
                if _hit:
                    _avg_saved = 0.015  # approx cost of one Claude reply
                    _hit.register_hit(_avg_saved)
                    _arch_lang = (request.env.context.get('lang') or 'ar')[:5]
                    if self._get_param('archive_enabled', 'True') in ('True', '1', 'true'):
                        self._archive_to_beena(
                            session_id, product, _arch_lang, message, _hit.answer,
                            source='cache', in_tokens=0, out_tokens=0,
                        )
                    session.add_message('assistant', _hit.answer)
                    return {
                        'reply': _hit.answer,
                        'state': 'talking',
                        'session_id': session_id,
                        'extra': {},
                    }
            except Exception as _ce:
                _logger.warning('cache lookup failed (non-fatal): %s', _ce)

        # ── Forced product search: if no current product and the message looks like
        # a product query, search NOW and inject results so Claude can't deny it. ──
        forced_results = None
        if not product:
            try:
                _msg_l = message.lower()
                # v2.1.78 — don't inject a product rail under clearly NON-product
                # intents (loyalty, orders, location, reviewers, fit, try-on,
                # cart, checkout). It looked unprofessional (a watch rail under
                # "what's my loyalty balance"). Skip the forced search then.
                _NONPROD_TOOLS = (
                    'get_loyalty_points', 'get_order_status', 'get_customer_orders',
                    'get_company_location', 'get_reviewers', 'check_fit',
                    'get_size_recommendation', 'start_virtual_tryon', 'get_cart',
                    'start_checkout', 'complete_checkout', 'update_address',
                    'get_payment_options', 'get_payment_link')
                _is_nonprod = any(
                    any(kw.lower() in _msg_l for kw in TOOL_TRIGGERS.get(tn, []))
                    for tn in _NONPROD_TOOLS)
                _wc = len(message.split())
                _looks_like_product = (not _is_nonprod) and (_wc >= 2 or any(
                    kw in _msg_l for kw in self._search_translations().keys()
                ) or any(
                    kw in _msg_l for kw in self._search_translations().values()
                ))
                if _looks_like_product and len(message) >= 3:
                    sr = self._fn_search_products({'query': message, 'limit': 5})
                    if sr.get('products'):
                        forced_results = sr['products']
            except Exception as _fe:
                _logger.warning('forced search failed (non-fatal): %s', _fe)

        system_prompt = self._build_system_prompt(product)
        # ── Beena Coach learned lessons (admin-approved, one-click applied) ──
        try:
            _lessons = self._get_param('learned_lessons', '')
            if _lessons.strip():
                # v2.2.47 — feed Beena ALL of the Coach's approved lessons
                # (admin asked for EVERY change). Rebuilt from all 600 distinct
                # applied/approved findings (~133KB). With prompt caching the
                # large-but-stable block is written once then served cheaply
                # from cache on every later message. The 150KB cap is only a
                # runaway guard; if it ever trips we keep the MOST RECENT
                # lessons (line-aligned) since the Coach appends.
                # TODO: once the Anthropic credit is topped up, distill these
                # 600 lessons into ~40 crisp rules to slim the prompt.
                _ls = _lessons.strip()
                if len(_ls) > 150000:
                    _ls = _ls[-150000:]
                    _nl = _ls.find('\n')
                    if _nl != -1:
                        _ls = _ls[_nl + 1:]      # drop the partial first line
                system_prompt += (
                    "\n\n=== LEARNED LESSONS (approved by admin — follow strictly) ===\n"
                    + _ls)
            # v2.2.05 — PLATFORM FACTS: admin-editable knowledge about how
            # the store currently works (delivery pricing, features going
            # live, policies). Param: uellow_ai.platform_facts.
            _facts = self._get_param('platform_facts', '')
            if _facts.strip():
                system_prompt += (
                    "\n\n=== PLATFORM FACTS (current, authoritative) ===\n"
                    + _facts.strip()[:4000])
        except Exception:
            pass
        # v2.1.79 — category context when Beena is opened from a category page
        # (no specific product). Lets her tailor suggestions to that section.
        if category_id and not product:
            try:
                _cat = request.env['product.public.category'].sudo().browse(int(category_id))
                if not _cat.exists():
                    _cat = request.env['product.category'].sudo().browse(int(category_id))
                if _cat.exists():
                    system_prompt += (
                        "\n\n=== CURRENT SECTION ===\n"
                        "The customer is browsing the category: %s. "
                        "Prioritise products and help relevant to this section."
                        % _cat.name)
            except Exception as _ce:
                _logger.warning('category ctx failed (non-fatal): %s', _ce)
        if forced_results:
            _names = '\n'.join(
                '- %s (id=%s, %s KD)' % (
                    (pp['name'].get('en_US') if isinstance(pp.get('name'), dict) else pp.get('name')),
                    pp.get('id'), pp.get('price'))
                for pp in forced_results
            )
            system_prompt += (
                "\n\n=== SEARCH RESULTS (closest matches already fetched) ===\n"
                "These products EXIST in our store. If they genuinely match what "
                "the customer asked for (or sent as an image), present them "
                "confidently and NEVER say 'not found'. BUT if they are clearly a "
                "DIFFERENT category than what was requested/shown (e.g. the "
                "customer wants clothing but these are watches), do NOT pretend "
                "they match — tell the customer we don't currently carry that "
                "item, then offer these only as alternatives or invite them to "
                "browse:\n" + _names + "\n"
            )
        model         = self._get_param('claude_model', 'claude-sonnet-4-6')
        max_tokens    = int(self._get_param('max_tokens', '768'))
        messages      = session.get_messages()
        active_tools  = self._select_tools(message)

        final_text  = ''
        final_state = 'talking'
        fn_results  = []
        total_in_tokens  = 0
        total_out_tokens = 0
        total_cache_write = 0
        total_cache_read  = 0

        for _ in range(5):
            response, error = self._call_claude(messages, system_prompt, model, max_tokens, active_tools)

            if error:
                _logger.error('Claude error: %s', error)
                return {
                    'reply':      'عذراً، حدث خطأ. حاول مرة ثانية.',
                    'state':      'sad',
                    'session_id': session_id,
                }

            stop_reason = response.get('stop_reason')
            _usage = response.get('usage', {}) or {}
            total_in_tokens  += int(_usage.get('input_tokens', 0) or 0)
            total_out_tokens += int(_usage.get('output_tokens', 0) or 0)
            total_cache_write += int(_usage.get('cache_creation_input_tokens', 0) or 0)
            total_cache_read  += int(_usage.get('cache_read_input_tokens', 0) or 0)
            content     = response.get('content', [])
            text_parts  = []
            tool_calls  = []

            for block in content:
                if block.get('type') == 'text':
                    text_parts.append(block.get('text', ''))
                elif block.get('type') == 'tool_use':
                    tool_calls.append(block)

            if text_parts:
                final_text = ' '.join(text_parts)

            if stop_reason == 'end_turn' or not tool_calls:
                break

            messages.append({'role': 'assistant', 'content': content})
            tool_results = []
            for tc in tool_calls:
                fn_name   = tc.get('name')
                fn_args   = tc.get('input', {})
                fn_result = self._execute_function(fn_name, fn_args)
                fn_results.append({'name': fn_name, 'result': fn_result})
                tool_results.append({
                    'type':        'tool_result',
                    'tool_use_id': tc.get('id'),
                    'content':     json.dumps(fn_result, ensure_ascii=False),
                })
            messages.append({'role': 'user', 'content': tool_results})
            if tool_calls:
                final_state = self._detect_state(final_text, tool_calls[-1].get('name'))

        if not final_text:
            final_text = 'تفضل، كيف أقدر أساعدك؟'

        final_text  = self._clean_text(final_text)
        final_state = self._detect_state(
            final_text, fn_results[-1]['name'] if fn_results else None
        )

        session.add_message('assistant', final_text)
        session.last_state = final_state

        extra = {}
        # If we forced a product search before calling Claude, surface those
        # results to the JS so it can render color/size chips and stock badges
        # even when Claude doesn't explicitly call the search tool.
        if forced_results:
            extra['products'] = forced_results
        for fr in fn_results:
            nm, res = fr['name'], fr['result']
            if nm == 'create_order' and res.get('success'):
                extra['order'] = res
            elif nm == 'get_payment_link':
                extra['payment'] = res
            elif nm in ('search_products', 'get_recommendations'):
                extra['products'] = res.get('products') or res.get('recommendations', [])
            elif nm == 'get_order_status':
                extra['order_status'] = res
            elif nm == 'get_customer_orders':
                extra['orders_list'] = res.get('orders', [])
            elif nm == 'get_reviewers':
                extra['reviewers'] = res
            elif nm == 'get_size_recommendation':
                extra['size_rec'] = res
            elif nm == 'start_virtual_tryon':
                extra['tryon'] = res
            elif nm == 'check_fit':
                extra['fit_check'] = res
            elif nm == 'get_cart':
                extra['cart_view'] = res
            elif nm == 'get_company_location':
                extra['company_location'] = res
            elif nm == 'start_checkout':
                extra['checkout'] = res
            elif nm == 'update_address':
                extra['checkout'] = res
            elif nm == 'complete_checkout':
                extra['quote'] = res
            elif nm == 'get_loyalty_points':
                extra['loyalty'] = res
            elif nm == 'get_upsell_products':
                extra['upsell'] = res.get('products', [])
            elif nm == 'get_payment_options':
                extra['payment_options'] = res
            elif nm == 'add_to_cart' and res.get('success'):
                extra['cart'] = res

        # ── Answer Cache store (remember Claude's reply for repeats) ──
        try:
            _neg_markers = ['ما لقيت', 'للأسف', 'مش موجود', 'not found', 'غير متوفر',
                            'ما لقيتها', 'لا يوجد', 'مو موجود', 'حاول مرة', 'عذراً']
            _is_negative = any(m in (final_text or '') for m in _neg_markers)
            # Never cache questions about variable info (price/stock/colors) —
            # their answers change, so they must always be answered live.
            _is_variable = any(kw in (message or '').lower() for kw in self._variable_keywords())
            _Cache2 = request.env['beena.qa.cache'].sudo()
            _ctx_dep2 = (len((message or '').split()) < 3
                         and not _Cache2.is_generic(message))
            if (self._get_param('cache_enabled', 'False') in ('True', '1', 'true')
                    and final_text and not _is_negative and not _is_variable
                    and not _ctx_dep2):
                _saved = self._compute_cost(total_in_tokens, total_out_tokens,
                                            total_cache_write, total_cache_read)
                request.env['beena.qa.cache'].sudo().store(
                    message, final_text, product_id, None, _saved,
                )
        except Exception as _se:
            _logger.warning('cache store failed (non-fatal): %s', _se)

        try:
            _archive_on = self._get_param('archive_enabled', 'True') in ('True', '1', 'true')
            if _archive_on:
                _arch_lang = (request.env.context.get('lang') or 'ar')[:5]
                self._archive_to_beena(
                    session_id, product, _arch_lang, message, final_text,
                    source='claude', in_tokens=total_in_tokens, out_tokens=total_out_tokens,
                    cache_write=total_cache_write, cache_read=total_cache_read,
                    extra=extra,
                )
        except Exception as _e:
            _logger.warning('archive call failed (non-fatal): %s', _e)

        # ── Fit-check auto-replay ─────────────────────────────────────────
        # If the customer has a recent (≥30min, ≤90d) fit check for this
        # product, surface it as a passive banner — unless we just rendered
        # a fresh check in this turn.
        try:
            public_user = request.env.ref('base.public_user')
            if (product and request.env.user.id != public_user.id
                    and 'fit_check' not in extra):
                partner = request.env.user.partner_id
                profile = request.env['customer.body.profile'].sudo().search(
                    [('partner_id', '=', partner.id)], limit=1)
                if profile:
                    last = request.env['customer.fit.history'].sudo().search([
                        ('profile_id', '=', profile.id),
                        ('product_id', '=', product.id),
                    ], order='create_date desc', limit=1)
                    if last:
                        from datetime import datetime, timedelta
                        age = datetime.now() - (last.create_date or datetime.now())
                        if timedelta(minutes=30) < age < timedelta(days=90):
                            color_map = {'green':'green','yellow':'yellow','orange':'orange','red':'red'}
                            overall = last.overall_match_pct or 0
                            if   overall >= 85: fc = 'green'
                            elif overall >= 70: fc = 'yellow'
                            elif overall >= 50: fc = 'orange'
                            else:               fc = 'red'
                            extra['fit_replay'] = {
                                'product_id':    product.id,
                                'product_name':  product.name,
                                'size':          last.size_chosen or '',
                                'overall_pct':   overall,
                                'fit_color':     fc,
                                'ago_days':      max(1, age.days),
                                'check_id':      last.id,
                            }
        except Exception as _re:
            _logger.warning('fit_replay inject failed (non-fatal): %s', _re)

        return {
            'reply':      final_text,
            'state':      final_state,
            'session_id': session_id,
            'extra':      extra,
        }

    @http.route('/ai/config', type='json', auth='public', methods=['POST'], csrf=False)
    def get_config(self, **kwargs):
        enabled = self._get_param('enabled', 'True')
        if enabled not in ('True', '1', 'true'):
            return {'enabled': False}
        # Bools first (so we can fall back to int parsing safely)
        def _b(key, default='True'):
            return self._get_param(key, default) in ('True', '1', 'true')
        def _i(key, default):
            try:
                return int(self._get_param(key, str(default)) or default)
            except Exception:
                return int(default)
        return {
            'enabled':      True,
            'name':         self._get_param('assistant_name',    'Beena'),
            'subtitle':     self._get_param('assistant_subtitle','مساعدة Uellow الذكية'),
            'welcome':      self._get_param('welcome_message',   'أهلاً! أنا Beena 🐝'),
            'button_color': self._get_param('button_color',      '#F5C320'),
            'float_button': _b('float_button'),
            'buy_with_ai':  _b('buy_with_ai'),
            'nudge':            _b('proactive_nudge'),
            'nudge_delay':      _i('nudge_delay', 30),
            'nudge_auto_open':  _b('nudge_auto_open'),
            'nudge_message':    _b('nudge_message'),
            'autoopen_desktop_enabled': _b('autoopen_desktop_enabled', 'True'),
            'autoopen_desktop_seconds': _i('autoopen_desktop_seconds', 60),
            'autoopen_mobile_enabled':  _b('autoopen_mobile_enabled',  'False'),
            'autoopen_mobile_seconds':  _i('autoopen_mobile_seconds',  120),
            'nudge_mode':       (self._get_param('nudge_mode', 'message') or 'message'),
            'nudge_anim':       (self._get_param('nudge_anim', 'bounce') or 'bounce'),
            # ── Voice stack flags (no secrets, just feature switches) ────
            'voice_enabled':       _b('voice_enabled',         'False'),
            'voice_phase_a':       _b('voice_phase_a_enabled', 'True'),
            'voice_phase_b':       _b('voice_phase_b_enabled', 'False'),
            'voice_autoplay':      _b('voice_autoplay_replies','False'),
            'voice_providers': {
                'eleven': _b('voice_eleven_enabled', 'False'),
                'openai': _b('voice_openai_enabled', 'False'),
                'azure':  _b('voice_azure_enabled',  'False'),
                'google': _b('voice_google_enabled', 'False'),
            },
        }


    # ── Inline cart endpoints (no redirect) ─────────────────────────────────
    @http.route('/ai/cart_view', type='json', auth='public', methods=['POST'], csrf=False)
    def cart_view(self, **kw):
        """Return the live cart (same shape as _fn_get_cart) for inline updates."""
        return self._fn_get_cart({})

    @http.route('/ai/cart_set_qty', type='json', auth='public', methods=['POST'], csrf=False)
    def cart_set_qty(self, **kw):
        """Set the quantity of a cart line (0 → delete)."""
        try:
            line_id = int(kw.get('line_id') or 0)
            new_qty = max(0, int(kw.get('qty') or 0))
        except Exception:
            return {'success': False, 'error': 'bad_args'}
        if not line_id:
            return {'success': False, 'error': 'line_id_required'}

        website = request.env['website'].sudo().search([], limit=1)
        order = website.sale_get_order() if website else False
        if not order:
            return {'success': False, 'error': 'no_cart'}
        line = order.order_line.filtered(lambda l: l.id == line_id)
        if not line:
            return {'success': False, 'error': 'line_not_found'}
        try:
            if new_qty == 0:
                line.unlink()
            else:
                order._cart_update(product_id=line.product_id.id,
                                   line_id=line.id,
                                   set_qty=new_qty)
        except Exception as e:
            _logger.warning('cart_set_qty failed: %s', e)
            return {'success': False, 'error': str(e)[:200]}

        # Refresh and return the new cart
        return self._fn_get_cart({})

    # ── Direct checkout endpoints (called from JS, bypass Claude) ───────────
    @http.route('/beena/checkout/state', type='json', auth='user', methods=['POST'], csrf=False)
    def checkout_state(self, **kw):
        """Return cart + partner address — same shape as _fn_start_checkout."""
        return self._fn_start_checkout({})

    @http.route('/beena/checkout/save_address', type='json', auth='user', methods=['POST'], csrf=False)
    def checkout_save_address(self, **kw):
        """Save all four address fields at once from the editable form."""
        return self._fn_update_address({
            'phone':       kw.get('phone', ''),
            'governorate': kw.get('governorate', ''),
            'city':        kw.get('city', ''),
            'street':      kw.get('street', ''),
        })

    @http.route('/beena/checkout/place', type='json', auth='user', methods=['POST'], csrf=False)
    def checkout_place(self, **kw):
        """Mirror complete_checkout — directly callable from the JS card."""
        # Optionally update address in the same call (one-shot submit)
        if any(kw.get(k) for k in ('phone', 'governorate', 'city', 'street')):
            self._fn_update_address({
                'phone':       kw.get('phone', ''),
                'governorate': kw.get('governorate', ''),
                'city':        kw.get('city', ''),
                'street':      kw.get('street', ''),
            })
        return self._fn_complete_checkout({})

    @http.route('/beena/order/status/<int:order_id>', type='json', auth='user', methods=['POST'], csrf=False)
    def order_status(self, order_id, **kw):
        """Lightweight polling: returns the order's current state (draft|sent|sale|cancel|done)."""
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists():
            return {'success': False, 'error': 'not_found'}
        partner = request.env.user.partner_id
        if order.partner_id and order.partner_id.id != partner.id:
            return {'success': False, 'error': 'not_authorized'}
        return {
            'success':      True,
            'order_id':     order.id,
            'order_name':   order.name,
            'state':        order.state,
            'amount_total': float(order.amount_total or 0),
            'currency':     (order.currency_id.name if order.currency_id else 'KD'),
            'paid':         order.state in ('sale', 'done'),
        }

    # ── Chat history (server-side) ──────────────────────────────────────────
    @http.route('/ai/history', type='json', auth='public', methods=['POST'], csrf=False)
    def get_history(self, **kw):
        """Return the latest persisted messages for the current user, so the
        JS panel can rehydrate after refresh/logout. Limit defaults to 30."""
        try:
            limit = int(kw.get('limit') or 30)
        except Exception:
            limit = 30
        limit = max(1, min(100, limit))

        public_user = request.env.ref('base.public_user')
        partner_id  = (request.env.user.partner_id.id
                       if request.env.user.id != public_user.id else 0)

        if not partner_id:
            return {'logged_in': False, 'messages': []}

        Conv = request.env['beena.conversation'].sudo()
        # Latest conversation for this partner
        conv = Conv.search([('partner_id', '=', partner_id)],
                          order='create_date desc', limit=1)
        if not conv:
            return {'logged_in': True, 'messages': []}

        Msg = request.env['beena.message'].sudo()
        rows = Msg.search([('conversation_id', '=', conv.id)],
                          order='create_date asc', limit=limit)
        messages = []
        for m in rows:
            extra = None
            if m.role != 'user' and m.extra_json:
                try:
                    extra = json.loads(m.extra_json)
                except Exception:
                    extra = None
            messages.append({
                'type':  'user' if m.role == 'user' else 'ai',
                'text':  m.body or '',
                'ts':    m.create_date and m.create_date.isoformat() or None,
                'extra': extra or None,
            })
        return {
            'logged_in': True,
            'session_id': conv.session_id,
            'messages':  messages,
        }

    # ── Visual Search Endpoint ────────────────────────────────────────────────

    @http.route('/ai/visual_search', type='json', auth='public', methods=['POST'], csrf=False)
    def visual_search(self, **kwargs):
        """Accepts base64 image, sends to Claude Vision, returns matching products."""
        enabled = self._get_param('enabled', 'True')
        if enabled not in ('True', '1', 'true'):
            return {'error': 'AI disabled', 'state': 'idle'}

        image_b64  = kwargs.get('image_base64', '')
        session_id = kwargs.get('session_id') or str(uuid.uuid4())

        if not image_b64:
            return {'error': 'No image', 'state': 'sad'}

        # Extract media type and data
        if ',' in image_b64:
            header, data = image_b64.split(',', 1)
            media_type = 'image/jpeg'
            if 'png' in header:  media_type = 'image/png'
            elif 'gif' in header: media_type = 'image/gif'
            elif 'webp' in header: media_type = 'image/webp'
        else:
            data = image_b64
            media_type = 'image/jpeg'

        api_key = self._get_param('claude_api_key', '')
        if not api_key:
            return {'error': 'API key not configured', 'state': 'sad'}

        model = self._get_param('claude_model', 'claude-sonnet-4-6')

        # Ask Claude to analyze the image and extract search keywords
        vision_payload = {
            'model': model,
            'max_tokens': 300,
            'messages': [{
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': media_type,
                            'data': data,
                        },
                    },
                    {
                        'type': 'text',
                        'text': '''Analyze this product image and respond ONLY with a JSON object (no markdown):
{
  "product_type": "type in Arabic e.g. جاكيت / سماعات / حذاء",
  "color": "main color in Arabic",
  "keywords": ["keyword1", "keyword2"],
  "search_query": "short 1-2 word search query in Arabic or English"
}'''
                    }
                ],
            }],
        }

        vdata    = json.dumps(vision_payload).encode('utf-8')
        vheaders = {
            'Content-Type':      'application/json',
            'x-api-key':         api_key,
            'anthropic-version': '2023-06-01',
        }

        try:
            req = urllib.request.Request(CLAUDE_API_URL, data=vdata, headers=vheaders)
            with urllib.request.urlopen(req, timeout=30) as resp:
                vresponse = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            _logger.exception('Visual search vision call failed')
            return {
                'reply': 'تعذّر تحليل الصورة. حاول مرة ثانية.',
                'state': 'sad',
            }

        # Parse Claude's response
        vision_text = ''
        for block in vresponse.get('content', []):
            if block.get('type') == 'text':
                vision_text = block.get('text', '')
                break

        try:
            # Clean any markdown fences
            clean = re.sub(r'```json|```', '', vision_text).strip()
            vision_data = json.loads(clean)
        except Exception:
            vision_data = {'search_query': vision_text[:50]}

        search_query = vision_data.get('search_query', '')
        product_type = vision_data.get('product_type', '')
        color        = vision_data.get('color', '')

        _logger.info('Visual search: query=%s type=%s color=%s', search_query, product_type, color)

        # Search products using extracted keywords
        search_results = self._fn_search_products({
            'query': search_query or product_type,
            'limit': 5,
        })

        products = search_results.get('products', [])

        # Build reply
        if products:
            reply = f'وجدت {len(products)} منتج مشابه للصورة'
            if product_type:
                reply = f'شايف في الصورة: {product_type}'
                if color: reply += f' باللون {color}'
                reply += f'\n\nوجدت {len(products)} منتج مشابه:'
            state = 'excited'
        else:
            reply = f'ما وجدت منتج مشابه في المتجر'
            if product_type:
                reply += f' لـ {product_type}'
            reply += '\nجرّب تكتب اسم المنتج مباشرة أو وصف ما تبحث عنه'
            state = 'sad'

        return {
            'reply':      reply,
            'state':      state,
            'session_id': session_id,
            'extra':      {'products': products} if products else {},
        }

    # ── Web Search Endpoint ───────────────────────────────────────────────────

    @http.route('/ai/web_search', type='json', auth='public', methods=['POST'], csrf=False)
    def web_search_proxy(self, **kwargs):
        """Search web via Brave API for product specs not found in catalog."""
        enabled = self._get_param('web_search_enabled', 'False')
        if enabled not in ('True', '1', 'true'):
            return {'error': 'Web search disabled'}

        query   = kwargs.get('query', '').strip()
        api_key = self._get_param('brave_api_key', '')

        if not query or not api_key:
            return {'error': 'Missing query or API key'}

        url     = f'https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(query)}&count=5&country=KW&search_lang=ar'
        headers = {
            'Accept':              'application/json',
            'Accept-Encoding':     'gzip',
            'X-Subscription-Token': api_key,
        }

        try:
            import urllib.parse
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            results = []
            for item in data.get('web', {}).get('results', [])[:5]:
                results.append({
                    'title':       item.get('title', ''),
                    'description': item.get('description', '')[:200],
                    'url':         item.get('url', ''),
                })
            return {'results': results}

        except Exception as e:
            _logger.error('Web search error: %s', e)
            return {'error': str(e)}
