# -*- coding: utf-8 -*-
"""Trips — /api/driver/v1/trips*"""
from datetime import datetime

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_driver,
    fmt_price, short_addr, order_status_code, status_label,
)


def _serialize_trip(trip, detail=False):
    lines = trip.line_ids.sorted(lambda l: (l.sequence or 999, l.id))
    out = {
        'id': trip.id,
        'name': trip.name,
        'date': trip.date_trip.isoformat() if trip.date_trip else None,
        'state': trip.state,
        'state_label': {
            'en': dict(trip._fields['state'].selection).get(trip.state, trip.state),
            'ar': {
                'draft': 'مسودة',
                'in_progress': 'جارية',
                'completed': 'مكتملة',
                'cancelled': 'ملغاة',
            }.get(trip.state, trip.state),
        },
        'line_count': len(lines),
        'done_count': sum(1 for l in lines if l.delivery_status == 'delivered'),
        'failed_count': sum(1 for l in lines if l.delivery_status == 'failed'),
    }
    if detail:
        stops = []
        for l in lines:
            o = l.sale_order_id
            if not o:
                continue
            code = order_status_code(l)
            stops.append({
                'line_id': l.id,
                'order_id': o.id,
                'order_name': o.name,
                'sequence': l.sequence or 0,
                'customer': o.partner_id.name,
                'addr_short': short_addr(o.partner_shipping_id or o.partner_id),
                'amount': fmt_price(o.amount_total, o.currency_id),
                'status': code,
                'status_label': status_label(code),
                'lat': getattr(o.partner_shipping_id or o.partner_id, 'partner_latitude', 0),
                'lng': getattr(o.partner_shipping_id or o.partner_id, 'partner_longitude', 0),
            })
        out['stops'] = stops
        out['notes'] = trip.notes or ''
    return out


class DriverTripsAPI(http.Controller):

    @http.route('/api/driver/v1/trips', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_trips(self, **kw):
        driver = current_driver()
        if not driver.carrier_company_id:
            return ok([])
        Trip = request.env['delivery.trip'].sudo()
        # Trips that include at least one line for this driver
        line_trips = request.env['delivery.trip.line'].sudo().search([
            ('driver_id', '=', driver.id),
        ]).mapped('trip_id')
        trips = Trip.search([('id', 'in', line_trips.ids)],
                            order='date_trip desc, id desc', limit=50)
        return ok([_serialize_trip(t) for t in trips])

    @http.route('/api/driver/v1/trips/<int:trip_id>', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def trip_detail(self, trip_id, **kw):
        Trip = request.env['delivery.trip'].sudo()
        trip = Trip.browse(trip_id)
        if not trip.exists():
            return fail('NOT_FOUND', 'Trip not found', 404)
        return ok({'trip': _serialize_trip(trip, detail=True)})

    @http.route('/api/driver/v1/trips/<int:trip_id>/reorder', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def reorder(self, trip_id, **kw):
        """Re-sequence the trip's stops. body: {line_ids: [3, 1, 4, 2, ...]}"""
        p = get_payload()
        order_ids = p.get('line_ids') or []
        if not isinstance(order_ids, list):
            return fail('BAD_INPUT', 'line_ids must be a list')
        Line = request.env['delivery.trip.line'].sudo()
        for idx, lid in enumerate(order_ids, start=10):
            line = Line.browse(int(lid))
            if line.exists() and line.trip_id.id == trip_id:
                line.write({'sequence': idx})
        return ok({'reordered': True})
