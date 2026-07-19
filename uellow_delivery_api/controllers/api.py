import json
import logging
from odoo import http, fields
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


def json_response(data, status=200):
    return Response(
        json.dumps(data, default=str),
        status=status,
        headers={'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
    )


def get_driver(token):
    if not token:
        return False
    raw = token.replace('Bearer ', '').strip()
    return request.env['uellow.delivery.token'].sudo().validate_token(raw)


class DeliveryAPIController(http.Controller):

    # ── Auth ────────────────────────────────────────────────────────
    @http.route('/api/delivery/login', type='http', auth='none',
                methods=['POST'], csrf=False)
    def login(self, **post):
        try:
            data = json.loads(request.httprequest.data)
            login = data.get('login', '')
            password = data.get('password', '')
            uid = request.env['res.users'].sudo()._login(
                request.env.cr.dbname, login, password, {})
            if not uid:
                return json_response({'error': 'Invalid credentials'}, 401)
            user = request.env['res.users'].sudo().browse(uid)
            token = request.env['uellow.delivery.token'].sudo().generate_token(user)
            return json_response({
                'ok': True,
                'token': token,
                'user': {'id': user.id, 'name': user.name},
            })
        except Exception as e:
            _logger.error('Delivery API login error: %s', e)
            return json_response({'error': str(e)}, 500)

    # ── Orders ───────────────────────────────────────────────────────
    @http.route('/api/delivery/orders', type='http', auth='none',
                methods=['GET'], csrf=False)
    def get_orders(self, **kw):
        token = request.httprequest.headers.get('Authorization', '')
        driver = get_driver(token)
        if not driver:
            return json_response({'error': 'Unauthorized'}, 401)

        pickings = request.env['stock.picking'].sudo().search([
            ('picking_type_code', '=', 'outgoing'),
            ('state', 'in', ('assigned', 'ready')),
            ('scheduled_date', '<=', fields.Datetime.now()),
        ], limit=50, order='scheduled_date asc')

        orders = []
        for p in pickings:
            sale = p.sale_id
            orders.append({
                'id': p.id,
                'name': p.name,
                'partner': sale.partner_id.name if sale else '',
                'address': sale.partner_shipping_id.street if sale else '',
                'phone': sale.partner_id.mobile or sale.partner_id.phone or '',
                'amount': sale.amount_total if sale else 0,
                'is_cod': bool(sale and 'cod' in (sale.payment_term_id.name or '').lower()),
                'state': p.state,
            })
        return json_response({'orders': orders})

    # ── Confirm Delivery ─────────────────────────────────────────────
    @http.route('/api/delivery/order/<int:picking_id>/confirm', type='http',
                auth='none', methods=['POST'], csrf=False)
    def confirm_delivery(self, picking_id, **kw):
        token = request.httprequest.headers.get('Authorization', '')
        driver = get_driver(token)
        if not driver:
            return json_response({'error': 'Unauthorized'}, 401)
        try:
            data = json.loads(request.httprequest.data or '{}')
            picking = request.env['stock.picking'].sudo().browse(picking_id)
            if not picking.exists():
                return json_response({'error': 'Not found'}, 404)
            # Validate immediately
            if picking.state == 'assigned':
                picking.with_context(skip_immediate=True).button_validate()
            picking.message_post(
                body=f"Confirmed by driver: {driver.name}. Note: {data.get('note', '')}",
            )
            return json_response({'ok': True, 'state': picking.state})
        except Exception as e:
            return json_response({'error': str(e)}, 500)

    # ── Trip Details ─────────────────────────────────────────────────
    @http.route('/api/delivery/trip/<int:trip_id>', type='http',
                auth='none', methods=['GET'], csrf=False)
    def get_trip(self, trip_id, **kw):
        token = request.httprequest.headers.get('Authorization', '')
        driver = get_driver(token)
        if not driver:
            return json_response({'error': 'Unauthorized'}, 401)
        trip = request.env['uellow.delivery.trip'].sudo().browse(trip_id)
        if not trip.exists():
            return json_response({'error': 'Not found'}, 404)
        return json_response({
            'id': trip.id,
            'name': trip.name,
            'date': str(trip.date),
            'state': trip.state,
            'total_orders': trip.total_orders,
            'cod_total': trip.cod_total,
            'cod_collected': trip.cod_collected,
        })

    # ── Cash Summary ─────────────────────────────────────────────────
    @http.route('/api/delivery/cash/summary', type='http',
                auth='none', methods=['GET'], csrf=False)
    def cash_summary(self, **kw):
        token = request.httprequest.headers.get('Authorization', '')
        driver = get_driver(token)
        if not driver:
            return json_response({'error': 'Unauthorized'}, 401)
        trips = request.env['uellow.delivery.trip'].sudo().search([
            ('driver_id', '=', driver.id),
            ('state', 'in', ('in_progress', 'completed')),
        ], limit=10)
        return json_response({
            'driver': driver.name,
            'trips': [{
                'name': t.name,
                'date': str(t.date),
                'cod_total': t.cod_total,
                'cod_collected': t.cod_collected,
            } for t in trips],
        })
