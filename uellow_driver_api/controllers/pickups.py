# -*- coding: utf-8 -*-
"""
Pickup leg — the COURIER collects a trip's orders from the Uellow warehouse
and brings them to the carrier sorting centre.

The pickup courier is a delivery.driver set as `delivery.trip.pickup_driver_id`
(by Uellow from the order/trip form, or by the carrier from their app). They
see the trip here, receive each package (barcode or one-by-one), and that
moves the orders `pending → picked_up`. The carrier warehouse then receives
them (`picked_up → arrived_sorting`) and distributes to per-region drivers.
"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, ok, fail, get_payload, require_auth, current_driver,
    short_addr, fmt_price,
)

_OPEN_TRIP = ('draft', 'assigned', 'in_progress')


class DriverPickups(http.Controller):

    @http.route('/api/driver/v1/pickups', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def pickups(self, **kw):
        """Trips this courier must collect from the Uellow warehouse."""
        driver = current_driver()
        trips = request.env['delivery.trip'].sudo().search([
            ('pickup_driver_id', '=', driver.id),
            ('state', 'in', _OPEN_TRIP),
        ], order='date_trip desc, id desc', limit=50)
        out = []
        for t in trips:
            orders = t.line_ids.mapped('sale_order_id')
            if not orders:
                continue
            to_collect = orders.filtered(lambda o: o.delivery_status == 'pending')
            collected = orders.filtered(
                lambda o: o.delivery_status not in ('pending', False))
            if not to_collect and t.pickup_state != 'collecting':
                continue  # nothing left here
            out.append({
                'id': t.id,
                'name': t.name,
                'date': t.date_trip.isoformat() if t.date_trip else None,
                'warehouse': 'Uellow',
                'total': len(orders),
                'to_collect': len(to_collect),
                'collected': len(collected),
                'pickup_state': t.pickup_state,
            })
        return ok({'pickups': out})

    @http.route('/api/driver/v1/pickups/<int:tid>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def pickup_detail(self, tid, **kw):
        driver = current_driver()
        trip = request.env['delivery.trip'].sudo().browse(tid)
        if not trip.exists() or trip.pickup_driver_id.id != driver.id:
            return fail('NOT_FOUND', 'Pickup not assigned to you', 404)
        orders = []
        for line in trip.line_ids.sorted('sequence'):
            o = line.sale_order_id
            if not o:
                continue
            orders.append({
                'id': o.id,
                'name': o.name,
                'code': (o.carrier_order_ref or o.name or '').strip(),
                'collected': o.delivery_status not in ('pending', False),
                'customer': {
                    'name': o.partner_id.name or '',
                    'phone': o.partner_id.phone or o.partner_id.mobile or '',
                },
                'addr_short': short_addr(o.partner_shipping_id or o.partner_id),
                'amount': fmt_price(o.amount_total, o.currency_id),
                'items_count': len(o.order_line.filtered(
                    lambda l: not l.display_type)),
            })
        return ok({
            'trip': {'id': trip.id, 'name': trip.name,
                     'pickup_state': trip.pickup_state},
            'orders': orders,
        })

    @http.route('/api/driver/v1/pickups/<int:tid>/collect', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def pickup_collect(self, tid, **kw):
        driver = current_driver()
        trip = request.env['delivery.trip'].sudo().browse(tid)
        if not trip.exists() or trip.pickup_driver_id.id != driver.id:
            return fail('NOT_FOUND', 'Pickup not assigned to you', 404)
        p = get_payload()
        order_ids = {int(x) for x in (p.get('order_ids') or []) if x}
        collect_missing = bool(p.get('collect_missing'))

        pending = trip.line_ids.mapped('sale_order_id').filtered(
            lambda o: o.delivery_status == 'pending')
        if collect_missing:
            to_collect = pending
        else:
            to_collect = pending.filtered(lambda o: o.id in order_ids)
        skipped = pending - to_collect

        for o in to_collect:
            o.with_context(skip_push=True).write(
                {'delivery_status': 'picked_up'})
            o.message_post(
                body='📦 Collected from the Uellow warehouse by %s '
                     '(pickup courier).' % driver.name)
        if to_collect:
            trip.message_post(
                body='🚚 %s collected %d/%d order(s) from Uellow.'
                % (driver.name, len(to_collect), len(pending)))
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({
            'collected': len(to_collect),
            'remaining': len(pending - to_collect),
            'missing': [{'id': o.id, 'name': o.name} for o in skipped]
                       if not collect_missing else [],
        })
