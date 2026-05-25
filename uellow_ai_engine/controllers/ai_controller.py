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
                'order_name': {'type': 'string', 'description': 'e.g. S00042'},
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
        'name': 'award_review_points',
        'description': 'Award 50 loyalty points when customer writes a product review.',
        'input_schema': {'type':'object','properties':{'product_id':{'type':'integer'}},'required':['product_id']},
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
]


class UellowAIController(http.Controller):

    def _get_param(self, key, default=''):
        return request.env['ir.config_parameter'].sudo().get_param(
            f'uellow_ai.{key}', default
        )

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

        lang_instruction = {
            'auto': '''Detect the customer language automatically and ALWAYS respond in the exact same language and dialect they use.
Examples:
- Customer writes in Kuwaiti Arabic → respond in Kuwaiti Arabic
- Customer writes in Egyptian Arabic → respond in Egyptian Arabic  
- Customer writes in Saudi Arabic → respond in Saudi Arabic
- Customer writes in English → respond in English
- Customer writes in Urdu → respond in Urdu
- Customer writes in Hindi → respond in Hindi
- Customer writes in Tagalog → respond in Tagalog
- Customer writes in Bengali → respond in Bengali
- Customer writes in any language → respond in that same language
Never switch languages unless the customer switches first.
Uellow serves Kuwait and GCC region with diverse nationalities.''',
            'ar':   'Always respond in Arabic, matching the customer dialect (Kuwaiti, Egyptian, Saudi, etc).',
            'en':   'Always respond in English.',
        }.get(lang, 'Detect customer language and always respond in the same language they use.')

        product_ctx = ''
        if product:
            product_ctx = f"""
Current product the customer is viewing:
- Name: {product.name}
- Price: {product.list_price:.3f} KD
- Description: {(product.description_sale or '')[:300]}
- Category: {product.categ_id.name if product.categ_id else 'N/A'}
- In Stock: {'Yes' if product.virtual_available > 0 else 'No'}
- Product ID: {product.id}
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
- If search_products returns empty products list → tell customer no results found, suggest alternatives
- If search_products returns error → try searching with shorter keyword
- ALWAYS try search_products before giving up — never refuse to search
- When searching, use SHORT keywords (1-2 words) not full product names
- Example: customer says "Anker R50i" → search "Anker R50" or just "Anker"
- Example: customer says "سماعات بلوتوث" → search "سماعات" 
- If first search returns nothing, try a shorter/different keyword
- After finding products, use the variant_id (not id) for add_to_cart
- Always confirm with customer before adding to cart or creating order

{product_ctx}{partner_ctx}

Payment options after order creation:
1. UPayments — pay now with card/KNET
2. Taly BNPL — split into 4 installments (0% interest)
3. Cash on Delivery (COD) — pay when the order arrives

STRICT FORMATTING RULES:
- NO markdown: no **, no *, no #, no ---, no backticks
- NO "state:" or technical words in your response text
- Plain text only, line breaks for separation
- Short and conversational
- When order is created, show order number and amount clearly

When customer asks about product specs not available in catalog:
- Tell them you'll search the web for more info
- Use get_product_info first, then suggest web search if specs missing

When customer asks about their points, rewards, or loyalty level:
- Use get_loyalty_points to show their balance
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

When customer asks about referral or inviting friends:
- Explain they earn 200 points per successful referral
- Direct them to /loyalty for their referral link

When customer asks for a human opinion, reviewer, or second opinion:
- Use get_reviewers to show available reviewers
- Keywords: ريفيور، رأي بشري، رأي شخص، شخص يساعدني، اريد رأي، second opinion

When customer sends an image (visual search):
- Confirm what you see in the image
- Search for similar products using extracted keywords
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
                'award_review_points': self._fn_award_review,
                'apply_coupon':        self._fn_apply_coupon,
                'get_customer_orders': self._fn_get_customer_orders,
                'get_upsell_products':      self._fn_get_upsell,
                'get_payment_options':      self._fn_get_payment_options,
                'get_loyalty_points':       self._fn_get_loyalty_points,
                'get_size_recommendation': self._fn_get_size_recommendation,
                'get_reviewers':        self._fn_get_reviewers,
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
            'description': (product.description_sale or '')[:500],
            'category': product.categ_id.name if product.categ_id else '',
            'in_stock': product.virtual_available > 0,
            'variants': variants,
        }

    def _fn_search_products(self, args):
        query    = (args.get('query') or '').strip()
        limit    = int(args.get('limit', 5))
        category = (args.get('category') or '').strip()

        env = request.env['product.template'].sudo()
        cr  = request.env.cr

        # Build search variants: original + transliterated
        search_terms = set()
        if query:
            search_terms.add(query)
            # Add individual words
            for w in query.split():
                if len(w) > 1:
                    search_terms.add(w)
            # Arabic/English transliteration common cases
            replacements = {
                'انكر': 'anker', 'انكور': 'anker',
                'سامسونج': 'samsung', 'سامسنج': 'samsung',
                'ابل': 'apple', 'آبل': 'apple',
                'هواوي': 'huawei', 'هواويي': 'huawei',
                'سوني': 'sony', 'شاومي': 'xiaomi',
                'جي بي ال': 'jbl', 'jbl': 'jbl',
                'بوز': 'bose', 'فيليبس': 'philips',
            }
            q_lower = query.lower()
            for ar, en in replacements.items():
                if ar in q_lower:
                    search_terms.add(en)
                if en in q_lower:
                    search_terms.add(ar)

        found_ids = []
        try:
            conditions = []
            params     = []
            for term in search_terms:
                conditions.append(
                    "(pt.name::text ILIKE %s "
                    "OR COALESCE(pt.description_sale::text,'') ILIKE %s)"
                )
                params += [f'%{term}%', f'%{term}%']

            if category:
                conditions.append("pc.complete_name ILIKE %s")
                params.append(f'%{category}%')

            if not conditions:
                return {'products': [], 'total': 0}

            where = '(' + ' OR '.join(conditions) + ')'
            params.append(limit)

            cr.execute(
                "SELECT DISTINCT pt.id FROM product_template pt "
                "LEFT JOIN product_category pc ON pc.id = pt.categ_id "
                "WHERE pt.is_published = true AND " + where + " "
                "ORDER BY pt.id LIMIT %s",
                params
            )
            found_ids = [r[0] for r in cr.fetchall()]
        except Exception as e:
            _logger.warning('Search SQL failed: %s', e)
            try:
                dom = [('is_published', '=', True)]
                if query:
                    dom += ['|', ('name', 'ilike', query), ('description_sale', 'ilike', query)]
                found_ids = env.search(dom, limit=limit).ids
            except Exception as e2:
                _logger.error('Search ORM failed: %s', e2)
                return {'products': [], 'total': 0}

        result_list = []
        for p in env.browse(found_ids[:limit]):
            try:
                variant = p.product_variant_ids[:1]
                result_list.append({
                    'id':         p.id,
                    'variant_id': variant.id if variant else None,
                    'name':       p.name,
                    'price':      p.list_price,
                    'category':   p.categ_id.name if p.categ_id else '',
                    'in_stock':   p.virtual_available > 0,
                    'image_url':  f'/web/image/product.template/{p.id}/image_128',
                })
            except Exception:
                pass

        _logger.info('Search "%s" terms=%s found=%d', query, search_terms, len(result_list))
        return {'products': result_list, 'total': len(result_list)}

    def _fn_check_stock(self, args):
        pid     = int(args.get('product_id', 0))
        attrs   = args.get('variant_attributes', {})
        product = request.env['product.template'].sudo().browse(pid)
        if not product.exists():
            return {'error': 'Product not found'}
        if not attrs:
            return {'in_stock': product.virtual_available > 0,
                    'qty': max(0, int(product.virtual_available))}
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
            order._cart_update(product_id=variant_id, add_qty=qty)
            return {'success': True, 'product': product.name, 'quantity': qty,
                    'cart_count': int(order.cart_quantity), 'cart_total': order.amount_total,
                    'cart_url': '/shop/cart', 'message': f'تمت إضافة {product.name} للسلة'}
        except Exception as e:
            import traceback
            return {'success': False, 'error': str(e), 'traceback': traceback.format_exc()[-300:]}


    def _fn_create_order(self, args):
        try:
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
            vals = {}
            if name:  vals['name']  = name
            if phone: vals['phone'] = phone
            if email: vals['email'] = email
            if vals:
                partner.sudo().write(vals)
            website = request.env['website'].sudo().search([], limit=1)
            if not website:
                return {'error': 'No website found'}
            order = website.sale_get_order(force_create=True)
            if not order:
                return {'error': 'Could not create order'}
            order._cart_update(product_id=product.id, add_qty=qty)
            upay_url = request.env['ir.config_parameter'].sudo().get_param(
                'upay_payment_link_url', f'/shop/payment?sale_order_id={order.id}'
            )
            return {'success': True, 'order_id': order.id, 'order_name': order.name,
                    'amount': order.amount_total, 'upay_url': upay_url, 'cart_url': '/shop/cart'}
        except Exception as e:
            import traceback
            return {'error': str(e), 'traceback': traceback.format_exc()[-300:]}


    def _fn_get_payment_link(self, args):
        oid   = int(args.get('order_id', 0))
        order = request.env['sale.order'].sudo().browse(oid)
        if not order.exists():
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

        return {
            'order_name':      order.name,
            'amount':          order.amount_total,
            'state':           state_map.get(order.state, order.state),
            'delivery_status': delivery_map.get(delivery_status, delivery_status or 'غير محدد'),
            'date_order':      str(order.date_order)[:16] if order.date_order else '',
            'partner':         order.partner_id.name,
            'driver':          driver_info,
            'eta':             eta,
            'can_cancel':      order.state in ('draft', 'sent'),
        }

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

    def _fn_award_review(self, args):
        pid = int(args.get('product_id', 0))
        LoyaltyAccount = request.env.get('loyalty.account')
        if not LoyaltyAccount:
            return {'available': False}
        public_user = request.env.ref('base.public_user')
        if request.env.user.id == public_user.id:
            return {'error': 'Login required'}
        partner = request.env.user.partner_id
        acc = LoyaltyAccount.sudo().get_or_create(partner.id)
        existing = request.env['loyalty.transaction'].sudo().search([
            ('account_id', '=', acc.id),
            ('reason', '=', 'مراجعة منتج'),
            ('reference', '=', str(pid)),
        ], limit=1)
        if existing:
            return {'already_awarded': True, 'message': 'سبق وحصلت على نقاط لهذا المنتج'}
        acc.add_points(50, 'مراجعة منتج', ref=str(pid))
        return {
            'success': True,
            'points_awarded': 50,
            'new_balance': acc.points_balance,
            'message': 'شكراً على مراجعتك! ربحت 50 نقطة',
        }

    def _fn_apply_coupon(self, args):
        code  = args.get('code', '')
        order = request.env["website"].sudo().search([], limit=1).sale_get_order()
        if not order:
            return {'error': 'No active cart'}
        try:
            order._cart_update_pricelist(pricelist_id=None)
            promo = request.env['sale.coupon.apply.code'].sudo().create({
                'coupon_code': code
            })
            promo.process_coupon()
            return {'success': True, 'message': f'تم تطبيق الكوبون {code}'}
        except Exception as e:
            return {'error': str(e), 'message': 'الكوبون غير صحيح أو منتهي الصلاحية'}

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
        return {'orders': [
            {'name': o.name, 'amount': o.amount_total,
             'state': o.state, 'date': str(o.date_order)[:10]}
            for o in orders
        ]}

    # ── Claude API ────────────────────────────────────────────────────────────

    def _call_claude(self, messages, system_prompt, model, max_tokens):
        api_key = self._get_param('claude_api_key', '')
        if not api_key:
            return None, 'Claude API key not configured'

        payload = {
            'model':      model,
            'max_tokens': int(max_tokens),
            'system':     system_prompt,
            'messages':   messages,
            'tools':      TOOLS,
        }
        data    = json.dumps(payload).encode('utf-8')
        headers = {
            'Content-Type':      'application/json',
            'x-api-key':         api_key,
            'anthropic-version': '2023-06-01',
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

        if not message:
            return {'error': 'Empty message', 'state': 'idle'}

        session = self._get_or_create_session(session_id, product_id)
        session.add_message('user', message)

        product = None
        if product_id:
            p = request.env['product.template'].sudo().browse(int(product_id))
            if p.exists():
                product = p

        system_prompt = self._build_system_prompt(product)
        model         = self._get_param('claude_model', 'claude-sonnet-4-6')
        max_tokens    = int(self._get_param('max_tokens', '1024'))
        messages      = session.get_messages()

        final_text  = ''
        final_state = 'talking'
        fn_results  = []

        for _ in range(5):
            response, error = self._call_claude(messages, system_prompt, model, max_tokens)

            if error:
                _logger.error('Claude error: %s', error)
                return {
                    'reply':      'عذراً، حدث خطأ. حاول مرة ثانية.',
                    'state':      'sad',
                    'session_id': session_id,
                }

            stop_reason = response.get('stop_reason')
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
            elif nm == 'get_loyalty_points':
                extra['loyalty'] = res
            elif nm == 'get_upsell_products':
                extra['upsell'] = res.get('products', [])
            elif nm == 'get_payment_options':
                extra['payment_options'] = res
            elif nm == 'add_to_cart' and res.get('success'):
                extra['cart'] = res

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
        return {
            'enabled':      True,
            'name':         self._get_param('assistant_name',    'Beena'),
            'subtitle':     self._get_param('assistant_subtitle','مساعدة Uellow الذكية'),
            'welcome':      self._get_param('welcome_message',   'أهلاً! أنا Beena 🐝'),
            'button_color': self._get_param('button_color',      '#F5C320'),
            'float_button': self._get_param('float_button',      'True') in ('True','1','true'),
            'buy_with_ai':  self._get_param('buy_with_ai',       'True') in ('True','1','true'),
            'nudge':        self._get_param('proactive_nudge',   'True') in ('True','1','true'),
            'nudge_delay':  int(self._get_param('nudge_delay',   '30')),
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
