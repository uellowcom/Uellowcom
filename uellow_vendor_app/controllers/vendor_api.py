import json
import logging
import hashlib
from odoo import http, fields
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def json_r(data, status=200):
    return Response(
        json.dumps(data, default=str),
        status=status,
        headers={
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        },
    )


def get_token_vendor(token):
    if not token:
        return False
    raw = token.replace('Bearer ', '').strip()
    token_rec = request.env['uellow.delivery.token'].sudo().search([
        ('token_hash', '=', hashlib.sha256(raw.encode()).hexdigest()),
        ('active', '=', True),
        ('expires_at', '>', fields.Datetime.now()),
    ], limit=1)
    if not token_rec:
        return False
    return request.env['uellow.vendor'].sudo().search([
        ('user_id', '=', token_rec.user_id.id),
    ], limit=1)


class VendorAppController(http.Controller):

    @http.route('/uellow/vendor/login', type='http', auth='none',
                methods=['POST', 'OPTIONS'], csrf=False)
    def vendor_login(self, login=None, password=None, **kw):
        """Accept login/password either from JSON body or POST kwargs."""
        if request.httprequest.method == 'OPTIONS':
            return json_r({})
        try:
            # Method 1: from kwargs (Odoo parses JSON body into kwargs)
            if login is None:
                # Method 2: try raw body
                body = request.httprequest.get_data(as_text=True)
                if body:
                    try:
                        data = json.loads(body)
                        if isinstance(data, dict):
                            login = data.get('login', '')
                            password = data.get('password', '')
                    except Exception:
                        pass

            login = login or ''
            password = password or ''

            _logger.warning('Vendor login attempt: login=%s', login)

            if not login or not password:
                return json_r({'error': 'Missing credentials'}, 400)

            result = request.env['res.users'].sudo()._login(
                request.env.cr.dbname,
                {'type': 'password', 'login': login, 'password': password},
                {'interactive': False})

            # Odoo 18: _login returns uid int or raises exception
            if isinstance(result, dict):
                uid = result.get('uid') or result.get('id')
            else:
                uid = result

            if not uid:
                return json_r({'error': 'Invalid credentials'}, 401)

            user = request.env['res.users'].sudo().browse(int(uid))
            vendor = request.env['uellow.vendor'].sudo().search([
                ('user_id', '=', uid)], limit=1)
            if not vendor:
                vendor = request.env['uellow.vendor'].sudo().search([
                    ('partner_id', '=', user.partner_id.id)], limit=1)
            if not vendor:
                return json_r({'error': 'No vendor account'}, 403)

            token = request.env['uellow.delivery.token'].sudo().generate_token(user)
            return json_r({
                'ok': True, 'token': token, 'uid': uid,
                'vendor': {
                    'id': vendor.id,
                    'store_name_en': vendor.store_name_en,
                    'store_name_ar': vendor.store_name_ar or '',
                    'tier': vendor.tier,
                    'wallet_balance': vendor.wallet_balance,
                    'order_count': vendor.order_count,
                    'state': vendor.state,
                },
            })
        except Exception as e:
            _logger.error('Vendor login error: %s', e, exc_info=True)
            return json_r({'error': str(e)}, 500)

    @http.route('/uellow/vendor/dashboard', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False)
    def dashboard(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return json_r({})
        vendor = get_token_vendor(request.httprequest.headers.get('Authorization', ''))
        if not vendor:
            return json_r({'error': 'Unauthorized'}, 401)
        return json_r({
            'store_name_en': vendor.store_name_en,
            'store_name_ar': vendor.store_name_ar or '',
            'tier': vendor.tier,
            'wallet_balance': vendor.wallet_balance,
            'order_count': vendor.order_count,
            'total_sales': vendor.total_sales,
            'avg_rating': vendor.avg_rating,
            'cancel_rate': vendor.cancel_rate,
            'follower_count': vendor.follower_count,
            'state': vendor.state,
        })

    @http.route('/uellow/vendor/orders', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False)
    def orders(self, page=1, state='all', **kw):
        if request.httprequest.method == 'OPTIONS':
            return json_r({})
        vendor = get_token_vendor(request.httprequest.headers.get('Authorization', ''))
        if not vendor:
            return json_r({'error': 'Unauthorized'}, 401)
        domain = [('vendor_id', '=', vendor.id)]
        if state != 'all':
            domain.append(('state', '=', state))
        orders = request.env['sale.order'].sudo().search(
            domain, limit=20, offset=(int(page)-1)*20, order='date_order desc')
        return json_r({'orders': [{
            'id': o.id, 'name': o.name,
            'date': str(o.date_order),
            'amount': o.amount_total,
            'state': o.state,
            'partner': o.partner_id.name,
        } for o in orders]})

    @http.route('/uellow/vendor/stock', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False)
    def stock(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return json_r({})
        vendor = get_token_vendor(request.httprequest.headers.get('Authorization', ''))
        if not vendor:
            return json_r({'error': 'Unauthorized'}, 401)
        products = request.env['product.product'].sudo().search([
            ('vendor_partner_id', '=', vendor.partner_id.id)], limit=100)
        return json_r({'products': [{
            'id': p.id, 'name': p.display_name,
            'fbu_state': p.fbu_state, 'vendor_qty': p.vendor_qty,
        } for p in products]})

    @http.route('/uellow/vendor/wallet', type='http', auth='none',
                methods=['GET', 'OPTIONS'], csrf=False)
    def wallet(self, **kw):
        if request.httprequest.method == 'OPTIONS':
            return json_r({})
        vendor = get_token_vendor(request.httprequest.headers.get('Authorization', ''))
        if not vendor or not vendor.wallet_id:
            return json_r({'error': 'Unauthorized'}, 401)
        txns = request.env['uellow.wallet.transaction'].sudo().search([
            ('wallet_id', '=', vendor.wallet_id.id)], limit=20, order='date desc')
        return json_r({
            'balance': vendor.wallet_balance,
            'pending': vendor.wallet_id.pending_balance,
            'total_earned': vendor.wallet_id.total_earned,
            'currency': vendor.currency_id.symbol or 'KD',
            'transactions': [{
                'date': str(t.date), 'type': t.tx_type,
                'amount': t.amount, 'description': t.description or '',
            } for t in txns],
        })
