"""
OpenAPI 3 spec — /api/mobile/v2/openapi.json
=============================================

Auto-generated from a static schema dictionary (we don't introspect
controllers because Odoo's @http.route is too dynamic to parse reliably).
The dict below is the source of truth for:
  • Swagger UI rendering (/api/mobile/v2/docs)
  • Codegen tools (openapi-generator, etc.)
  • Contract tests in CI

When you add an endpoint in any *.py here, add a paragraph to the
matching tag in `_PATHS` below. Five-minute job, saves hours later.
"""
import json

from odoo import http
from odoo.http import request

from ._common import CORS_HEADERS, safe_endpoint


_INFO = {
    'title': 'Uellow Mobile API',
    'version': '2.0.0',
    'description': (
        'REST API for the Uellow Flutter app. Bearer-token auth, '
        'bilingual responses, uniform `{success,data,meta,error,code}` '
        'envelope on every endpoint. See controllers/api_v2/_common.py '
        'for the response envelope reference.'
    ),
    'contact': {'name': 'Uellow', 'url': 'https://uellow.com'},
}

_TAGS = [
    {'name': 'auth',          'description': 'Login, register, social, OTP, logout'},
    {'name': 'profile',       'description': 'Update profile, change password'},
    {'name': 'home',          'description': 'Home screen aggregate'},
    {'name': 'products',      'description': 'Catalog read endpoints'},
    {'name': 'categories',    'description': 'Public category tree'},
    {'name': 'cart',          'description': 'Cart CRUD (guest + auth)'},
    {'name': 'orders',        'description': 'Orders + checkout'},
    {'name': 'addresses',     'description': 'Customer addresses'},
    {'name': 'wishlist',      'description': 'Wishlist (auth)'},
    {'name': 'search',        'description': 'Search + popular queries'},
    {'name': 'reviews',       'description': 'Product reviews'},
    {'name': 'loyalty',       'description': 'Loyalty + wallet'},
    {'name': 'notifications', 'description': 'Push notifications'},
    {'name': 'beena',         'description': 'AI chat passthrough'},
    {'name': 'app',           'description': 'App settings + lookups'},
]

# Common reusable components
_COMPONENTS = {
    'securitySchemes': {
        'bearerAuth': {'type': 'http', 'scheme': 'bearer'},
    },
    'schemas': {
        'BilingualText': {
            'type': 'object',
            'properties': {
                'en': {'type': 'string'}, 'ar': {'type': 'string'},
            },
            'required': ['en', 'ar'],
        },
        'Money': {
            'type': 'object',
            'properties': {
                'amount': {'type': 'number'},
                'currency': {'type': 'string'},
                'symbol': {'type': 'string'},
                'digits': {'type': 'integer'},
            },
        },
        'EnvelopeOk': {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean', 'enum': [True]},
                'data': {'description': 'Endpoint-specific payload'},
                'meta': {'type': 'object', 'description': 'Pagination etc.'},
            },
            'required': ['success'],
        },
        'EnvelopeFail': {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean', 'enum': [False]},
                'code': {'type': 'string', 'description': 'Machine-friendly error code'},
                'error': {'type': 'string', 'description': 'Human-readable message'},
            },
            'required': ['success', 'code', 'error'],
        },
        'Pagination': {
            'type': 'object',
            'properties': {
                'page': {'type': 'integer'},
                'per_page': {'type': 'integer'},
                'total': {'type': 'integer'},
                'pages': {'type': 'integer'},
                'has_next': {'type': 'boolean'},
            },
        },
        'ProductCard': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'name': {'$ref': '#/components/schemas/BilingualText'},
                'slug': {'type': 'string'},
                'image': {'type': 'string', 'format': 'uri'},
                'price': {'$ref': '#/components/schemas/Money'},
                'compare_price': {'$ref': '#/components/schemas/Money', 'nullable': True},
                'discount_pct': {'type': 'integer'},
                'in_stock': {'type': 'boolean'},
                'qty_available': {'type': 'integer', 'nullable': True},
                'rating': {
                    'type': 'object',
                    'properties': {
                        'avg': {'type': 'number'},
                        'count': {'type': 'integer'},
                    },
                },
                'is_published': {'type': 'boolean'},
                'badges': {'type': 'array', 'items': {'type': 'string'}},
            },
        },
        'CartLine': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'product_id': {'type': 'integer'},
                'variant_id': {'type': 'integer'},
                'name': {'$ref': '#/components/schemas/BilingualText'},
                'image': {'type': 'string', 'format': 'uri'},
                'qty': {'type': 'number'},
                'unit_price': {'$ref': '#/components/schemas/Money'},
                'subtotal':   {'$ref': '#/components/schemas/Money'},
                'total':      {'$ref': '#/components/schemas/Money'},
            },
        },
        'Cart': {
            'type': 'object',
            'properties': {
                'order_id':   {'type': 'integer', 'nullable': True},
                'cart_token': {'type': 'string'},
                'currency':   {'type': 'string'},
                'lines':      {'type': 'array', 'items': {'$ref': '#/components/schemas/CartLine'}},
                'line_count': {'type': 'integer'},
                'totals': {
                    'type': 'object',
                    'properties': {
                        'subtotal': {'$ref': '#/components/schemas/Money'},
                        'tax':      {'$ref': '#/components/schemas/Money'},
                        'shipping': {'$ref': '#/components/schemas/Money'},
                        'discount': {'$ref': '#/components/schemas/Money'},
                        'total':    {'$ref': '#/components/schemas/Money'},
                    },
                },
                'coupons': {'type': 'array', 'items': {'type': 'string'}},
            },
        },
        'User': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'},
                'email': {'type': 'string'},
                'phone': {'type': 'string'},
                'avatar': {'type': 'string', 'format': 'uri'},
                'lang': {'type': 'string'},
                'wallet_balance': {'type': 'number'},
                'loyalty_points': {'type': 'integer'},
                'addresses_count': {'type': 'integer'},
            },
        },
    },
    'responses': {
        'AuthRequired': {
            'description': 'Bearer token missing or invalid',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/EnvelopeFail'}}},
        },
        'NotFound': {
            'description': 'Resource not found',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/EnvelopeFail'}}},
        },
        'Error': {
            'description': 'Error',
            'content': {'application/json': {'schema': {'$ref': '#/components/schemas/EnvelopeFail'}}},
        },
    },
}


def _ok_response(content_schema=None):
    """Build an OK 200 response with the envelope wrapping a schema."""
    if content_schema is None:
        ok_schema = {'$ref': '#/components/schemas/EnvelopeOk'}
    else:
        ok_schema = {
            'allOf': [
                {'$ref': '#/components/schemas/EnvelopeOk'},
                {'type': 'object', 'properties': {'data': content_schema}},
            ],
        }
    return {
        'description': 'OK',
        'content': {'application/json': {'schema': ok_schema}},
    }


def _ep(tag, summary, *, auth=False, body=None, params=None, response_schema=None):
    base = {
        'tags': [tag],
        'summary': summary,
        'responses': {
            '200': _ok_response(response_schema),
            '4XX': {'$ref': '#/components/responses/Error'},
        },
    }
    if auth:
        base['security'] = [{'bearerAuth': []}]
        base['responses']['401'] = {'$ref': '#/components/responses/AuthRequired'}
    if params:
        base['parameters'] = params
    if body:
        base['requestBody'] = {
            'required': True,
            'content': {'application/json': {'schema': body}},
        }
    return base


def _qs(name, *, schema=None, desc=''):
    return {
        'name': name, 'in': 'query', 'description': desc,
        'schema': schema or {'type': 'string'},
    }


def _path(name, schema=None):
    return {
        'name': name, 'in': 'path', 'required': True,
        'schema': schema or {'type': 'integer'},
    }


# ─── Paths ────────────────────────────────────────────────────────────

_PATHS = {
    # ── Auth
    '/api/mobile/v2/auth/login': {
        'post': _ep('auth', 'Login with email + password',
                    body={'type': 'object', 'required': ['email', 'password'],
                          'properties': {
                              'email': {'type': 'string'},
                              'password': {'type': 'string'},
                              'device_id': {'type': 'string'},
                              'device_name': {'type': 'string'},
                              'push_token': {'type': 'string'},
                              'app_version': {'type': 'string'},
                          }},
                    response_schema={
                        'type': 'object',
                        'properties': {
                            'token': {'type': 'string'},
                            'user': {'$ref': '#/components/schemas/User'},
                        },
                    }),
    },
    '/api/mobile/v2/auth/register': {
        'post': _ep('auth', 'Register a new account',
                    body={'type': 'object', 'required': ['name', 'email', 'password'],
                          'properties': {
                              'name': {'type': 'string'},
                              'email': {'type': 'string'},
                              'password': {'type': 'string'},
                              'phone': {'type': 'string'},
                          }}),
    },
    '/api/mobile/v2/auth/otp/request':  {'post': _ep('auth', 'Request OTP (no-op; Firebase handles SMS)')},
    '/api/mobile/v2/auth/otp/verify':   {'post': _ep('auth', 'Verify Firebase OTP and login/register')},
    '/api/mobile/v2/auth/social/google':   {'post': _ep('auth', 'Sign in with Google ID token')},
    '/api/mobile/v2/auth/social/apple':    {'post': _ep('auth', 'Sign in with Apple identity token')},
    '/api/mobile/v2/auth/social/facebook': {'post': _ep('auth', 'Sign in with Facebook access token')},
    '/api/mobile/v2/auth/forgot':  {'post': _ep('auth', 'Send password reset email')},
    '/api/mobile/v2/auth/logout':  {'post': _ep('auth', 'Revoke the current session', auth=True)},
    '/api/mobile/v2/auth/me':      {'get':  _ep('auth', 'Current authenticated user', auth=True)},

    # ── Profile
    '/api/mobile/v2/profile/update':          {'post': _ep('profile', 'Update profile fields', auth=True)},
    '/api/mobile/v2/profile/change-password': {'post': _ep('profile', 'Change password', auth=True)},
    '/api/mobile/v2/profile/delete':          {'post': _ep('profile', 'Delete account (soft)', auth=True)},

    # ── Home
    '/api/mobile/v2/home': {'get': _ep('home', 'Home screen aggregate')},

    # ── Products
    '/api/mobile/v2/products': {
        'get': _ep('products', 'List products',
                   params=[
                       _qs('page', schema={'type': 'integer'}),
                       _qs('per_page', schema={'type': 'integer'}),
                       _qs('category_id', schema={'type': 'integer'}),
                       _qs('search'),
                       _qs('sort', schema={'type': 'string', 'enum':
                            ['newest','oldest','price_asc','price_desc','name','popular','top_rated']}),
                       _qs('brand_id', schema={'type': 'integer'}),
                       _qs('tag_id',   schema={'type': 'integer'}),
                       _qs('min_price',schema={'type': 'number'}),
                       _qs('max_price',schema={'type': 'number'}),
                       _qs('on_sale'),
                   ],
                   response_schema={'type': 'array',
                                    'items': {'$ref': '#/components/schemas/ProductCard'}}),
    },
    '/api/mobile/v2/products/{product_id}': {
        'get': _ep('products', 'Product detail',
                   params=[_path('product_id')]),
    },
    '/api/mobile/v2/products/{product_id}/variants': {
        'get': _ep('products', 'Product variants', params=[_path('product_id')]),
    },
    '/api/mobile/v2/products/{product_id}/reviews': {
        'get': _ep('products', 'Product reviews + summary', params=[_path('product_id')]),
    },
    '/api/mobile/v2/products/{product_id}/related': {
        'get': _ep('products', 'Related products', params=[_path('product_id')]),
    },
    '/api/mobile/v2/products/top-selling':     {'get': _ep('products', 'Top-selling products')},
    '/api/mobile/v2/products/recommended':     {'get': _ep('products', 'Personalised recommendations')},
    '/api/mobile/v2/products/recently-viewed': {'get': _ep('products', 'Recently viewed (auth)', auth=True)},
    '/api/mobile/v2/products/section/{section_id}': {
        'get': _ep('products', 'Products of a mobile.product.slider', params=[_path('section_id')]),
    },
    '/api/mobile/v2/products/{product_id}/ask': {
        'post': _ep('products', 'Ask a question about a product', params=[_path('product_id')]),
    },

    # ── Categories
    '/api/mobile/v2/categories':         {'get': _ep('categories', 'List categories (root or children)')},
    '/api/mobile/v2/categories/tree':    {'get': _ep('categories', 'Full category hierarchy')},
    '/api/mobile/v2/categories/{category_id}': {
        'get': _ep('categories', 'Category detail', params=[_path('category_id')]),
    },
    '/api/mobile/v2/categories/{category_id}/products': {
        'get': _ep('categories', 'Products in a category',
                   params=[_path('category_id'), _qs('sort'), _qs('page'), _qs('per_page')]),
    },

    # ── Cart
    '/api/mobile/v2/cart': {
        'get': _ep('cart', 'Get current cart',
                   response_schema={'type':'object','properties':{'cart':{'$ref':'#/components/schemas/Cart'}}}),
    },
    '/api/mobile/v2/cart/add': {
        'post': _ep('cart', 'Add a product to the cart',
                    body={'type':'object','required':['product_id'],
                          'properties':{'product_id':{'type':'integer'},'qty':{'type':'number'}}}),
    },
    '/api/mobile/v2/cart/update':        {'post': _ep('cart', 'Update line quantity')},
    '/api/mobile/v2/cart/remove':        {'post': _ep('cart', 'Remove a line')},
    '/api/mobile/v2/cart/clear':         {'post': _ep('cart', 'Empty the cart')},
    '/api/mobile/v2/cart/apply-coupon':  {'post': _ep('cart', 'Apply a coupon code')},
    '/api/mobile/v2/cart/remove-coupon': {'post': _ep('cart', 'Remove the active coupon')},

    # ── Orders
    '/api/mobile/v2/orders':                  {'get':  _ep('orders', 'List orders', auth=True)},
    '/api/mobile/v2/orders/{order_id}':       {'get':  _ep('orders', 'Order detail', auth=True, params=[_path('order_id')])},
    '/api/mobile/v2/orders/shipping-methods': {'get':  _ep('orders', 'Shipping methods for cart')},
    '/api/mobile/v2/orders/payment-methods':  {'get':  _ep('orders', 'Available payment providers')},
    '/api/mobile/v2/orders/checkout/summary': {'get':  _ep('orders', 'Checkout summary (cart + addresses)', auth=True)},
    '/api/mobile/v2/orders/checkout/confirm': {'post': _ep('orders', 'Confirm and place order', auth=True)},

    # ── Addresses
    '/api/mobile/v2/addresses':             {'get':  _ep('addresses', 'List addresses', auth=True)},
    '/api/mobile/v2/addresses/create':      {'post': _ep('addresses', 'Create an address', auth=True)},
    '/api/mobile/v2/addresses/{addr_id}/update': {'post': _ep('addresses', 'Update an address', auth=True, params=[_path('addr_id')])},
    '/api/mobile/v2/addresses/{addr_id}/delete': {'post': _ep('addresses', 'Delete (archive) an address', auth=True, params=[_path('addr_id')])},

    # ── Wishlist
    '/api/mobile/v2/wishlist':         {'get':  _ep('wishlist', 'List wishlist', auth=True)},
    '/api/mobile/v2/wishlist/add':     {'post': _ep('wishlist', 'Add to wishlist', auth=True)},
    '/api/mobile/v2/wishlist/remove':  {'post': _ep('wishlist', 'Remove from wishlist', auth=True)},

    # ── Search
    '/api/mobile/v2/search':         {'get': _ep('search', 'Full-text search', params=[_qs('q')])},
    '/api/mobile/v2/search/popular': {'get': _ep('search', 'Popular queries')},

    # ── Reviews
    '/api/mobile/v2/reviews/create': {'post': _ep('reviews', 'Create or update review', auth=True)},
    '/api/mobile/v2/reviews/mine':   {'get':  _ep('reviews', 'My reviews', auth=True)},

    # ── Loyalty + Wallet
    '/api/mobile/v2/loyalty':              {'get': _ep('loyalty', 'Points + tier + redeem rate', auth=True)},
    '/api/mobile/v2/wallet/balance':       {'get': _ep('loyalty', 'Wallet balance', auth=True)},
    '/api/mobile/v2/wallet/transactions':  {'get': _ep('loyalty', 'Wallet transactions', auth=True)},

    # ── Notifications
    '/api/mobile/v2/notifications':                   {'get':  _ep('notifications', 'List notifications', auth=True)},
    '/api/mobile/v2/notifications/{notif_id}/read':   {'post': _ep('notifications', 'Mark notification as read', auth=True, params=[_path('notif_id')])},
    '/api/mobile/v2/notifications/register-device':   {'post': _ep('notifications', 'Register / update FCM token')},

    # ── Beena
    '/api/mobile/v2/beena/config': {'get':  _ep('beena', 'Beena AI config')},
    '/api/mobile/v2/beena/chat':   {'post': _ep('beena', 'Send a message to Beena')},

    # ── App settings
    '/api/mobile/v2/app/settings':      {'get': _ep('app', 'App-wide settings + feature flags')},
    '/api/mobile/v2/app/languages':     {'get': _ep('app', 'Active languages')},
    '/api/mobile/v2/app/countries':     {'get': _ep('app', 'Countries list')},
    '/api/mobile/v2/app/states':        {'get': _ep('app', 'States for a country',
                                                  params=[_qs('country_id', schema={'type': 'integer'})])},
    '/api/mobile/v2/app/version-check': {'get': _ep('app', 'Min/latest version + force-update flag')},
}


def _spec():
    return {
        'openapi': '3.0.3',
        'info': _INFO,
        'tags': _TAGS,
        'servers': [{
            'url': request.env['ir.config_parameter'].sudo()
                    .get_param('web.base.url', 'https://www.uellow.com').rstrip('/'),
        }],
        'components': _COMPONENTS,
        'security': [],
        'paths': _PATHS,
    }


class MobileOpenAPI(http.Controller):

    @http.route('/api/mobile/v2/openapi.json', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def openapi(self, **kw):
        return request.make_response(
            json.dumps(_spec(), ensure_ascii=False, default=str, indent=2),
            headers=CORS_HEADERS,
            status=200,
        )

    @http.route('/api/mobile/v2/docs', type='http', auth='public',
                methods=['GET'], csrf=False)
    def docs(self, **kw):
        """Inline Swagger UI — no extra files needed. Points at our
        openapi.json so the docs are always in sync with the spec."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Uellow Mobile API v2 — Docs</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body style="margin:0">
  <div id="swagger"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({
      url: '/api/mobile/v2/openapi.json',
      dom_id: '#swagger',
      deepLinking: true,
      docExpansion: 'list',
      defaultModelsExpandDepth: 1,
      tryItOutEnabled: true,
    });
  </script>
</body>
</html>"""
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ])
