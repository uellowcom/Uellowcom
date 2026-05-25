import json
import logging
import datetime

from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def _json(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        status=status,
        mimetype='application/json',
        headers={'Access-Control-Allow-Origin': '*'},
    )


def _err(msg, code=400):
    return _json({'success': False, 'error': msg}, code)


def _get_uid_from_token():
    token = request.httprequest.headers.get('X-Mobile-Token', '')
    if not token:
        return None
    param = request.env['ir.config_parameter'].sudo().search(
        [('key', '=', f'mobile_token_{token}')], limit=1
    )
    if not param:
        return None
    try:
        data    = json.loads(param.value)
        expires = datetime.datetime.fromisoformat(data['expires'])
        if datetime.datetime.now() > expires:
            return None
        return data['uid']
    except Exception:
        return None


def _auth_user():
    """Returns (user, partner) or (None, None)."""
    uid = _get_uid_from_token()
    if not uid:
        return None, None
    user    = request.env['res.users'].sudo().browse(uid)
    partner = user.partner_id
    return user, partner


class MobileAPIController(http.Controller):

    def _options(self):
        return Response(
            '', status=200,
            headers={
                'Access-Control-Allow-Origin':  '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-Mobile-Token',
            }
        )

    # ── Products ──────────────────────────────────────────────────────────────

    @http.route('/api/v1/products', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_products(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._options()

        page     = int(request.httprequest.args.get('page', 1))
        limit    = min(int(request.httprequest.args.get('limit', 20)), 50)
        category = request.httprequest.args.get('category', '')
        search   = request.httprequest.args.get('search', '')
        sort     = request.httprequest.args.get('sort', 'create_date desc')
        offset   = (page - 1) * limit

        domain = [('website_published', '=', True), ('sale_ok', '=', True)]
        if category:
            domain.append(('categ_id.name', 'ilike', category))
        if search:
            domain += ['|', ('name', 'ilike', search), ('description_sale', 'ilike', search)]

        products = request.env['product.template'].sudo().search(
            domain, limit=limit, offset=offset, order=sort,
        )
        total = request.env['product.template'].sudo().search_count(domain)

        return _json({
            'success':  True,
            'total':    total,
            'page':     page,
            'limit':    limit,
            'pages':    (total + limit - 1) // limit,
            'products': [_fmt_product(p) for p in products],
        })

    @http.route('/api/v1/products/<int:product_id>', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_product(self, product_id, **kwargs):
        p = request.env['product.template'].sudo().browse(product_id)
        if not p.exists() or not p.website_published:
            return _err('Product not found', 404)
        return _json({'success': True, 'product': _fmt_product(p, full=True)})

    @http.route('/api/v1/products/<int:product_id>/variants', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_variants(self, product_id, **kwargs):
        p = request.env['product.template'].sudo().browse(product_id)
        if not p.exists():
            return _err('Product not found', 404)
        variants = []
        for v in p.product_variant_ids:
            attrs = {
                ptav.attribute_id.name: ptav.name
                for ptav in v.product_template_attribute_value_ids
            }
            variants.append({
                'id':         v.id,
                'attributes': attrs,
                'price':      v.lst_price,
                'in_stock':   v.virtual_available > 0,
                'qty':        max(0, int(v.virtual_available)),
            })
        return _json({'success': True, 'variants': variants})

    # ── Categories ────────────────────────────────────────────────────────────

    @http.route('/api/v1/categories', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_categories(self, **kwargs):
        cats = request.env['product.public.category'].sudo().search(
            [('website_published', '=', True)], order='sequence, name',
        )
        if not cats:
            cats = request.env['product.category'].sudo().search([], limit=50)

        return _json({
            'success':    True,
            'categories': [{'id': c.id, 'name': c.name} for c in cats],
        })

    # ── Cart ──────────────────────────────────────────────────────────────────

    @http.route('/api/v1/cart', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_cart(self, **kwargs):
        _, partner = _auth_user()
        if not partner:
            return _err('Authentication required', 401)

        order = request.env['sale.order'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'draft'),
            ('website_id', '!=', False),
        ], limit=1, order='create_date desc')

        if not order:
            return _json({'success': True, 'cart': {'lines': [], 'total': 0}})

        return _json({'success': True, 'cart': _fmt_cart(order)})

    @http.route('/api/v1/cart/add', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def cart_add(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._options()

        _, partner = _auth_user()
        if not partner:
            return _err('Authentication required', 401)

        try:
            body       = json.loads(request.httprequest.data or '{}')
            product_id = int(body.get('product_id', 0))
            qty        = int(body.get('quantity', 1))
        except Exception:
            return _err('Invalid request body')

        if not product_id:
            return _err('product_id required')

        # Get or create draft order
        order = request.env['sale.order'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'draft'),
            ('website_id', '!=', False),
        ], limit=1, order='create_date desc')

        website = request.env['website'].sudo().search([], limit=1)
        if not order:
            order = request.env['sale.order'].sudo().create({
                'partner_id': partner.id,
                'website_id': website.id if website else False,
                'state':      'draft',
            })

        # Resolve template → variant
        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            tmpl = request.env['product.template'].sudo().browse(product_id)
            if tmpl.exists():
                product = tmpl.product_variant_ids[:1]
            if not product.exists():
                return _err('Product not found', 404)

        # Check if already in cart
        line = order.order_line.filtered(lambda l: l.product_id.id == product.id)
        if line:
            line[0].product_uom_qty += qty
        else:
            order.order_line.sudo().create({
                'order_id':          order.id,
                'product_id':        product.id,
                'product_uom_qty':   qty,
                'price_unit':        product.lst_price,
            })

        return _json({'success': True, 'cart': _fmt_cart(order)})

    @http.route('/api/v1/cart/remove', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def cart_remove(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._options()
        _, partner = _auth_user()
        if not partner:
            return _err('Authentication required', 401)
        try:
            body    = json.loads(request.httprequest.data or '{}')
            line_id = int(body.get('line_id', 0))
        except Exception:
            return _err('Invalid request body')

        line = request.env['sale.order.line'].sudo().browse(line_id)
        if line.exists() and line.order_id.partner_id.id == partner.id:
            line.unlink()
        return _json({'success': True})

    # ── Orders ────────────────────────────────────────────────────────────────

    @http.route('/api/v1/orders', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_orders(self, **kwargs):
        _, partner = _auth_user()
        if not partner:
            return _err('Authentication required', 401)

        limit  = min(int(request.httprequest.args.get('limit', 20)), 50)
        offset = int(request.httprequest.args.get('offset', 0))

        orders = request.env['sale.order'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', 'in', ['sale', 'done', 'sent']),
        ], limit=limit, offset=offset, order='date_order desc')

        return _json({
            'success': True,
            'orders':  [_fmt_order(o) for o in orders],
        })

    @http.route('/api/v1/orders/<int:order_id>', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_order(self, order_id, **kwargs):
        _, partner = _auth_user()
        if not partner:
            return _err('Authentication required', 401)
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.partner_id.id != partner.id:
            return _err('Order not found', 404)
        return _json({'success': True, 'order': _fmt_order(order, full=True)})

    @http.route('/api/v1/orders/create', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def create_order(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._options()
        _, partner = _auth_user()
        if not partner:
            return _err('Authentication required', 401)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return _err('Invalid JSON')

        product_id = int(body.get('product_id', 0))
        qty        = int(body.get('quantity', 1))

        if not product_id:
            return _err('product_id required')

        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            tmpl = request.env['product.template'].sudo().browse(product_id)
            if tmpl.exists():
                product = tmpl.product_variant_ids[:1]
            if not product.exists():
                return _err('Product not found', 404)

        website = request.env['website'].sudo().search([], limit=1)
        order   = request.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'website_id': website.id if website else False,
        })
        request.env['sale.order.line'].sudo().create({
            'order_id':        order.id,
            'product_id':      product.id,
            'product_uom_qty': qty,
            'price_unit':      product.lst_price,
        })
        order.sudo().action_confirm()

        # Award loyalty points
        LoyaltyAccount = request.env.get('loyalty.account')
        if LoyaltyAccount:
            LoyaltyAccount.sudo().on_order_confirmed(order)

        # Get payment URL
        upay_url = request.env['ir.config_parameter'].sudo().get_param(
            'upay_payment_link_url', f'/shop/payment?sale_order_id={order.id}'
        )

        return _json({
            'success':    True,
            'order_id':   order.id,
            'order_name': order.name,
            'amount':     order.amount_total,
            'upay_url':   upay_url,
        })

    # ── Customer Profile ──────────────────────────────────────────────────────

    @http.route('/api/v1/profile', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_profile(self, **kwargs):
        _, partner = _auth_user()
        if not partner:
            return _err('Authentication required', 401)

        loyalty = {}
        LoyaltyAccount = request.env.get('loyalty.account')
        if LoyaltyAccount:
            acc = LoyaltyAccount.sudo().search([('partner_id', '=', partner.id)], limit=1)
            if acc:
                loyalty = acc.to_dict()

        return _json({
            'success': True,
            'profile': {
                'id':       partner.id,
                'name':     partner.name,
                'email':    partner.email or '',
                'phone':    partner.phone or '',
                'avatar':   f'/web/image/res.partner/{partner.id}/image_128',
                'country':  partner.country_id.name if partner.country_id else '',
                'city':     partner.city or '',
                'loyalty':  loyalty,
            },
        })

    @http.route('/api/v1/profile/update', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def update_profile(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._options()
        _, partner = _auth_user()
        if not partner:
            return _err('Authentication required', 401)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return _err('Invalid JSON')

        vals = {}
        for field in ['name', 'phone', 'city', 'street']:
            if field in body:
                vals[field] = body[field]
        if vals:
            partner.sudo().write(vals)

        return _json({'success': True, 'message': 'Profile updated'})

    # ── AI Chat ───────────────────────────────────────────────────────────────

    @http.route('/api/v1/ai/chat', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def ai_chat(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._options()

        uid = _get_uid_from_token()
        if uid:
            request.uid = uid

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return _err('Invalid JSON')

        message    = body.get('message', '').strip()
        session_id = body.get('session_id', '')
        product_id = body.get('product_id')

        if not message:
            return _err('Message required')

        # Call Beena AI engine directly
        try:
            from odoo.addons.uellow_ai_engine.controllers.ai_controller import UellowAIController
            ai = UellowAIController()
            result = ai.chat(
                message=message,
                session_id=session_id,
                product_id=product_id,
            )
            return _json({'success': True, **result})
        except Exception as e:
            _logger.exception('Mobile AI chat error')
            return _err(str(e))

    # ── Loyalty ───────────────────────────────────────────────────────────────

    @http.route('/api/v1/loyalty', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_loyalty(self, **kwargs):
        _, partner = _auth_user()
        if not partner:
            return _err('Authentication required', 401)

        LoyaltyAccount = request.env.get('loyalty.account')
        if not LoyaltyAccount:
            return _json({'success': True, 'available': False})

        acc = LoyaltyAccount.sudo().get_or_create(partner.id)
        txns = acc.transaction_ids[:20]

        return _json({
            'success':      True,
            'account':      acc.to_dict(),
            'transactions': [t.to_dict() for t in txns],
        })

    # ── Search ────────────────────────────────────────────────────────────────

    @http.route('/api/v1/search', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def search(self, **kwargs):
        query = request.httprequest.args.get('q', '').strip()
        limit = min(int(request.httprequest.args.get('limit', 10)), 30)

        if not query:
            return _json({'success': True, 'products': []})

        words = query.split()
        domain = [('website_published', '=', True)]
        word_domain = []
        for w in words:
            word_domain += ['|', ('name', 'ilike', w), ('description_sale', 'ilike', w)]
        if word_domain:
            domain += word_domain[1:]  # remove leading |

        products = request.env['product.template'].sudo().search(domain, limit=limit)

        return _json({
            'success':  True,
            'query':    query,
            'products': [_fmt_product(p) for p in products],
        })

    # ── Banners / Sliders (for home screen) ───────────────────────────────────

    @http.route('/api/v1/home', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False, cors='*')
    def get_home(self, **kwargs):
        # New arrivals
        new_arrivals = request.env['product.template'].sudo().search(
            [('website_published', '=', True)],
            limit=10, order='create_date desc',
        )
        # Best sellers
        best_sellers = request.env['product.template'].sudo().search(
            [('website_published', '=', True)],
            limit=10, order='sales_count desc',
        )
        # Featured categories
        categories = request.env['product.public.category'].sudo().search(
            [('website_published', '=', True)], limit=8
        ) or request.env['product.category'].sudo().search([], limit=8)

        return _json({
            'success':     True,
            'new_arrivals': [_fmt_product(p) for p in new_arrivals],
            'best_sellers': [_fmt_product(p) for p in best_sellers],
            'categories':   [{'id': c.id, 'name': c.name} for c in categories],
        })


# ── Formatters ────────────────────────────────────────────────────────────────

def _fmt_product(p, full=False):
    images = [f'/web/image/product.template/{p.id}/image_1920']
    base = {
        'id':          p.id,
        'name':        p.name,
        'price':       p.list_price,
        'compare_price': p.compare_list_price or 0,
        'currency':    'KD',
        'in_stock':    p.virtual_available > 0,
        'category':    p.categ_id.name if p.categ_id else '',
        'image':       images[0],
        'rating':      0,
        'sales_count': p.sales_count or 0,
        'has_variants': len(p.product_variant_ids) > 1,
    }
    if full:
        base.update({
            'description':  p.description_sale or '',
            'images':       images,
            'attributes':   [
                {
                    'name':   al.attribute_id.name,
                    'values': [v.name for v in al.value_ids],
                }
                for al in p.attribute_line_ids
            ],
        })
    return base


def _fmt_cart(order):
    return {
        'id':     order.id,
        'name':   order.name,
        'total':  order.amount_total,
        'lines': [
            {
                'id':       l.id,
                'product':  {
                    'id':    l.product_id.id,
                    'name':  l.product_id.name,
                    'image': f'/web/image/product.product/{l.product_id.id}/image_128',
                },
                'qty':      l.product_uom_qty,
                'price':    l.price_unit,
                'subtotal': l.price_subtotal,
            }
            for l in order.order_line
            if not l.product_id.name == 'Loyalty Discount'
        ],
    }


def _fmt_order(order, full=False):
    state_map = {
        'draft':  'مسودة',
        'sent':   'مرسل',
        'sale':   'مؤكد',
        'done':   'مكتمل',
        'cancel': 'ملغي',
    }
    delivery_map = {
        'pending':          'في الانتظار',
        'arrived_sorting':  'وصل مركز الفرز',
        'assigned':         'تم تعيين سائق',
        'out_for_delivery': 'في الطريق إليك',
        'delivered':        'تم التسليم',
        'failed':           'فشل التسليم',
    }
    base = {
        'id':              order.id,
        'name':            order.name,
        'amount':          order.amount_total,
        'state':           state_map.get(order.state, order.state),
        'delivery_status': delivery_map.get(
            getattr(order, 'delivery_status', None), 'غير محدد'
        ),
        'date':            str(order.date_order)[:16] if order.date_order else '',
        'lines_count':     len(order.order_line),
    }
    if full:
        base['lines'] = [
            {
                'product_name': l.product_id.name,
                'qty':          l.product_uom_qty,
                'price':        l.price_unit,
                'subtotal':     l.price_subtotal,
                'image':        f'/web/image/product.product/{l.product_id.id}/image_128',
            }
            for l in order.order_line
        ]
    return base


    # ── Push Notifications ────────────────────────────────────────────────────

    @http.route('/api/v1/notifications/register', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def register_device(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return self._options()
        _, partner = _auth_user()
        if not partner:
            return _err('Authentication required', 401)
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return _err('Invalid JSON')

        fcm_token = body.get('fcm_token', '')
        platform  = body.get('platform', 'android')  # android or ios

        if not fcm_token:
            return _err('fcm_token required')

        # Store token in ir.config_parameter
        key = f'push_token_{partner.id}'
        request.env['ir.config_parameter'].sudo().set_param(key, json.dumps({
            'token':    fcm_token,
            'platform': platform,
            'partner':  partner.id,
        }))

        return _json({'success': True, 'message': 'Device registered for notifications'})

    @http.route('/api/v1/notifications/send', type='http', auth='user',
                methods=['POST', 'OPTIONS'], csrf=False, cors='*')
    def send_notification(self, **kwargs):
        """Internal endpoint — send push notification to a customer."""
        if request.httprequest.method == 'OPTIONS':
            return self._options()
        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            return _err('Invalid JSON')

        partner_id = int(body.get('partner_id', 0))
        title      = body.get('title', 'Uellow')
        message    = body.get('message', '')
        data       = body.get('data', {})

        if not partner_id or not message:
            return _err('partner_id and message required')

        # Get FCM token
        key   = f'push_token_{partner_id}'
        token = request.env['ir.config_parameter'].sudo().get_param(key)
        if not token:
            return _err('No device token registered for this partner')

        try:
            token_data = json.loads(token)
            fcm_token  = token_data.get('token', '')
        except Exception:
            return _err('Invalid token data')

        # Send via FCM (requires FCM server key)
        fcm_key = request.env['ir.config_parameter'].sudo().get_param(
            'uellow_mobile_api.fcm_server_key', ''
        )

        if not fcm_key:
            # Log notification without sending (no FCM key configured)
            _logger.info('Push notification [no FCM key]: %s — %s', title, message)
            return _json({'success': True, 'sent': False, 'message': 'FCM key not configured — logged only'})

        import urllib.request as urlreq
        payload = json.dumps({
            'to': fcm_token,
            'notification': {'title': title, 'body': message, 'sound': 'default'},
            'data': data,
        }).encode('utf-8')

        req = urlreq.Request(
            'https://fcm.googleapis.com/fcm/send',
            data=payload,
            headers={
                'Content-Type':  'application/json',
                'Authorization': f'key={fcm_key}',
            }
        )
        try:
            with urlreq.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                return _json({'success': True, 'sent': True, 'fcm_result': result})
        except Exception as e:
            _logger.error('FCM send error: %s', e)
            return _err(f'FCM error: {str(e)}')


def _send_push_notification(env, partner_id, title, message, data=None):
    """Helper function — call from anywhere in Odoo to send push notification."""
    key   = f'push_token_{partner_id}'
    token = env['ir.config_parameter'].sudo().get_param(key)
    if not token:
        return False

    try:
        token_data = json.loads(token)
        fcm_token  = token_data.get('token', '')
        fcm_key    = env['ir.config_parameter'].sudo().get_param('uellow_mobile_api.fcm_server_key', '')

        if not fcm_key:
            return False

        import urllib.request as urlreq
        payload = json.dumps({
            'to': fcm_token,
            'notification': {'title': title, 'body': message, 'sound': 'default'},
            'data': data or {},
        }).encode('utf-8')

        req = urlreq.Request(
            'https://fcm.googleapis.com/fcm/send',
            data=payload,
            headers={'Content-Type': 'application/json', 'Authorization': f'key={fcm_key}'},
        )
        with urlreq.urlopen(req, timeout=10) as resp:
            return True
    except Exception as e:
        _logger.error('Push notification error: %s', e)
        return False
