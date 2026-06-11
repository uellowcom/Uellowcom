# -*- coding: utf-8 -*-
"""
Carrier mobile API — /api/mobile/v2/carrier/*  (bearer token auth).
Powers the standalone «Uellow Delivery» app for delivery companies:
managers (full company view: orders, drivers, cash, remittances, stats)
and drivers (their own queue + deliver/fail flow with proof).

Auth: the SAME /api/mobile/v2/auth/login — portal users (managers /
drivers) are res.users, so their email+password works; we resolve the
role from delivery.carrier.company.portal_user_ids / delivery.driver.
portal_user_id.
"""
from datetime import datetime, timedelta

from odoo import http, fields as ofields
from odoo.http import request

from odoo.addons.uellow_mobile_manager.controllers.api_v2._common import (
    safe_endpoint, ok, fail, get_payload, current_partner, require_auth,
    paginate,
)

STATUS_LABELS = {
    'pending': {'en': 'Pending', 'ar': 'جديد'},
    'picked_up': {'en': 'Picked up (in transit)', 'ar': 'تم الاستلام — في الطريق'},
    'arrived_sorting': {'en': 'At sorting center', 'ar': 'في مركز الفرز'},
    'assigned': {'en': 'Assigned', 'ar': 'مُسند لسائق'},
    'out_for_delivery': {'en': 'Out for delivery', 'ar': 'خرج للتوصيل'},
    'delivered': {'en': 'Delivered', 'ar': 'تم التسليم'},
    'failed': {'en': 'Failed', 'ar': 'فشل التسليم'},
    'failed_returned': {'en': 'Failed & returned', 'ar': 'فشل ومرتجع'},
}


def _ctx():
    """(user, role, company, driver) for the current bearer token."""
    partner = current_partner()
    if not partner:
        return None, None, None, None
    user = request.env['res.users'].sudo().search(
        [('partner_id', '=', partner.id)], limit=1)
    if not user:
        return None, None, None, None
    company = request.env['delivery.carrier.company'].sudo().search(
        [('portal_user_ids', 'in', user.id), ('active', '=', True)],
        limit=1)
    driver = request.env['delivery.driver'].sudo().search(
        [('portal_user_id', '=', user.id), ('active', '=', True)],
        limit=1)
    role = 'manager' if company else ('driver' if driver else None)
    if role == 'driver':
        company = driver.carrier_company_id
    return user, role, company or None, driver or None


def _full_address(partner):
    parts = [p for p in [partner.street, partner.street2, partner.city,
                         partner.state_id.name if partner.state_id else '',
                         partner.country_id.name
                         if partner.country_id else ''] if p]
    return ', '.join(parts)


def _ser_order(o, role='manager', detail=False):
    ship = o.partner_shipping_id or o.partner_id
    lat = o.delivery_lat or 0.0
    lng = o.delivery_lng or 0.0
    d = {
        'id': o.id,
        'name': o.name,
        'ref': o.carrier_order_ref or '',
        'status': o.delivery_status or 'pending',
        'status_label': STATUS_LABELS.get(o.delivery_status or 'pending',
                                          STATUS_LABELS['pending']),
        'customer': {
            'name': ship.name or o.partner_id.name or '',
            'phone': ship.phone or ship.mobile
                     or o.partner_id.phone or '',
        },
        'address': o.delivery_address_text or _full_address(ship),
        'lat': lat, 'lng': lng,
        'map_url': ('https://www.google.com/maps/dir/?api=1'
                    '&destination=%s,%s' % (lat, lng))
                   if lat and lng else '',
        'amount': round(o.amount_total, 3),
        'currency': o.currency_id.name or 'KWD',
        'payment': o.payment_method_type or 'online',
        'cash_status': o.cash_collection_status or 'not_applicable',
        'driver': {'id': o.delivery_driver_id.id,
                   'name': o.delivery_driver_id.name}
                  if o.delivery_driver_id else None,
        'items_count': len(o.order_line.filtered(
            lambda l: not l.display_type
            and not getattr(l, 'is_delivery', False)
            and not getattr(l, 'is_reward_line', False))),
        'order_type': o.carrier_order_type or 'delivery',
        'created': o.date_order.isoformat() if o.date_order else None,
        'delivered_at': o.delivery_date_actual.isoformat()
                        if o.delivery_date_actual else None,
        'note': o.note or '',
    }
    if detail:
        d['items'] = [{
            'name': l.product_id.display_name,
            'qty': l.product_uom_qty,
            'price': round(l.price_total, 3),
        } for l in o.order_line.filtered(
            lambda l: not l.display_type
            and not getattr(l, 'is_delivery', False)
            and not getattr(l, 'is_reward_line', False))]
    if role == 'manager':
        d['fees'] = {
            'delivery': round(o.carrier_delivery_fee or 0, 3),
            'cash_commission': round(o.carrier_cash_commission or 0, 3),
            'cancel': round(o.carrier_cancel_fee or 0, 3),
            'net': round(o.carrier_net_cost or 0, 3),
        }
    return d


def _scope_domain(role, company, driver):
    if role == 'manager':
        return [('delivery_carrier_company_id', '=', company.id)]
    return [('delivery_carrier_company_id', '=', company.id),
            ('delivery_driver_id', '=', driver.id)]


class UellowCarrierAPI(http.Controller):

    # ── identity + dashboard numbers ─────────────────────────────────
    @http.route('/api/mobile/v2/carrier/me', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def me(self, **kw):
        user, role, company, driver = _ctx()
        if not role:
            return ok({'role': 'none'})
        Sale = request.env['sale.order'].sudo()
        dom = _scope_domain(role, company, driver)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0)
        week = today - timedelta(days=today.weekday())
        month = today.replace(day=1)
        since30 = datetime.utcnow() - timedelta(days=30)

        def cnt(extra):
            return Sale.search_count(dom + extra)

        delivered30 = cnt([('delivery_status', '=', 'delivered'),
                           ('delivery_date_actual', '>=', since30)])
        failed30 = cnt([('delivery_status', 'in',
                         ('failed', 'failed_returned')),
                        ('write_date', '>=', since30)])
        total30 = delivered30 + failed30
        cod_pending_orders = Sale.search(dom + [
            ('payment_method_type', '=', 'cash'),
            ('cash_collection_status', '=', 'collected'),
        ])
        cod_today = Sale.search(dom + [
            ('payment_method_type', '=', 'cash'),
            ('cash_collection_status', 'in', ('collected', 'remitted')),
            ('delivery_date_actual', '>=', today),
        ])
        status_counts = {}
        for st in STATUS_LABELS:
            status_counts[st] = cnt([('delivery_status', '=', st)])
        out = {
            'role': role,
            'user_name': user.name,
            'company': {
                'id': company.id,
                'name': company.name,
                'phone': company.phone or '',
                'settlement_mode': company.cash_settlement_mode,
                'logo_url': '/web/image/delivery.carrier.company/%d/logo'
                            % company.id,
                'drivers_count': company.driver_count,
            },
            'driver': {
                'id': driver.id, 'name': driver.name,
                'phone': driver.phone,
                'vehicle': driver.vehicle_info or '',
            } if driver else None,
            'stats': {
                'today_delivered': cnt([
                    ('delivery_status', '=', 'delivered'),
                    ('delivery_date_actual', '>=', today)]),
                'week_delivered': cnt([
                    ('delivery_status', '=', 'delivered'),
                    ('delivery_date_actual', '>=', week)]),
                'month_delivered': cnt([
                    ('delivery_status', '=', 'delivered'),
                    ('delivery_date_actual', '>=', month)]),
                'active_orders': cnt([
                    ('delivery_status', 'in',
                     ('pending', 'arrived_sorting', 'assigned',
                      'out_for_delivery'))]),
                'success_rate': round(delivered30 * 100.0 / total30, 1)
                                if total30 else 100.0,
                'cod_pending_kd': round(sum(
                    cod_pending_orders.mapped('amount_total')), 3),
                'cod_pending_count': len(cod_pending_orders),
                'cod_today_kd': round(sum(
                    cod_today.mapped('amount_total')), 3),
            },
            'status_counts': status_counts,
        }
        return ok(out)

    # ── orders ───────────────────────────────────────────────────────
    @http.route('/api/mobile/v2/carrier/orders', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def orders(self, **kw):
        user, role, company, driver = _ctx()
        if not role:
            return fail('NOT_CARRIER', 'Carrier account required', 403)
        p = get_payload()
        dom = _scope_domain(role, company, driver)
        status = (p.get('status') or '').strip()
        if status == 'active':
            dom.append(('delivery_status', 'in',
                        ('pending', 'arrived_sorting', 'assigned',
                         'out_for_delivery')))
        elif status == 'failed':
            dom.append(('delivery_status', 'in',
                        ('failed', 'failed_returned')))
        elif status:
            dom.append(('delivery_status', '=', status))
        q = (p.get('q') or '').strip()
        if q:
            dom += ['|', '|', '|',
                    ('name', 'ilike', q),
                    ('carrier_order_ref', 'ilike', q),
                    ('partner_id.name', 'ilike', q),
                    ('partner_id.phone', 'ilike', q)]
        recs = request.env['sale.order'].sudo().search(
            dom, order='date_order desc')
        items, meta = paginate(
            recs, page=p.get('page', 1), per_page=p.get('per_page', 20),
            serializer=lambda o: _ser_order(o, role))
        return ok({'orders': items}, meta)

    @http.route('/api/mobile/v2/carrier/orders/<int:oid>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def order_detail(self, oid, **kw):
        user, role, company, driver = _ctx()
        o = self._owned_order(oid, role, company, driver)
        if o is None:
            return fail('NOT_FOUND', 'Order not found', 404)
        return ok(_ser_order(o, role, detail=True))

    def _owned_order(self, oid, role, company, driver):
        if not role:
            return None
        o = request.env['sale.order'].sudo().browse(oid)
        if not o.exists() or \
                o.delivery_carrier_company_id.id != company.id:
            return None
        if role == 'driver' and o.delivery_driver_id.id != driver.id:
            return None
        return o

    # ── status actions ───────────────────────────────────────────────
    @http.route('/api/mobile/v2/carrier/orders/<int:oid>/<string:act>',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_auth
    def order_action(self, oid, act, **kw):
        user, role, company, driver = _ctx()
        o = self._owned_order(oid, role, company, driver)
        if o is None:
            return fail('NOT_FOUND', 'Order not found', 404)
        p = get_payload()
        Line = request.env['delivery.trip.line'].sudo()

        def line_for():
            dom = [('sale_order_id', '=', o.id)]
            if role == 'driver':
                dom.append(('driver_id', '=', driver.id))
            return Line.search(dom, limit=1)

        if act == 'receive':
            if role != 'manager':
                return fail('FORBIDDEN', 'Manager only', 403)
            o.write({'delivery_status': 'arrived_sorting'})

        elif act == 'not-received':
            if role != 'manager':
                return fail('FORBIDDEN', 'Manager only', 403)
            o.write({'delivery_status': 'failed_returned'})
            l = line_for()
            if l:
                l.write({'delivery_status': 'failed_returned'})

        elif act == 'assign':
            if role != 'manager':
                return fail('FORBIDDEN', 'Manager only', 403)
            d = request.env['delivery.driver'].sudo().browse(
                int(p.get('driver_id') or 0))
            if not d.exists() or d.carrier_company_id.id != company.id:
                return fail('NOT_FOUND', 'Driver not found', 404)
            if o.delivery_status == 'delivered':
                return fail('BAD_STATE', 'Already delivered', 400)
            # Assigning a driver sets 'assigned' (NOT out_for_delivery) so the
            # driver gets the ACCEPT step in their app; the driver's "Start
            # delivery" is what moves it to out_for_delivery + live tracking.
            o.write({'delivery_driver_id': d.id,
                     'delivery_status': 'assigned'})
            l = line_for()
            if l:
                l.write({'driver_id': d.id,
                         'delivery_status': 'assigned'})
            else:
                Line.create({'sale_order_id': o.id, 'driver_id': d.id,
                             'delivery_status': 'assigned'})

        elif act == 'unassign':
            if role != 'manager':
                return fail('FORBIDDEN', 'Manager only', 403)
            if o.delivery_status == 'delivered' or \
                    o.cash_collection_status == 'remitted':
                return fail('BAD_STATE', 'Cannot unassign', 400)
            o.write({'delivery_driver_id': False,
                     'delivery_status': 'assigned'})
            l = line_for()
            if l:
                l.write({'driver_id': False,
                         'delivery_status': 'pending'})

        elif act == 'start':
            if o.delivery_status == 'delivered':
                return fail('BAD_STATE', 'Already delivered', 400)
            o.write({'delivery_status': 'out_for_delivery'})
            l = line_for()
            if l:
                l.write({'delivery_status': 'out_for_delivery'})

        elif act == 'deliver':
            vals = {'delivery_status': 'delivered',
                    'delivery_date_actual': ofields.Datetime.now()}
            if o.payment_method_type == 'cash':
                vals['cash_collection_status'] = 'collected'
            try:
                if p.get('lat') and p.get('lng'):
                    vals['delivery_lat'] = float(p['lat'])
                    vals['delivery_lng'] = float(p['lng'])
            except Exception:
                pass
            o.write(vals)
            l = line_for()
            lv = {'delivery_status': 'delivered',
                  'delivery_date_actual': ofields.Datetime.now(),
                  'notes': (p.get('notes') or '').strip()}
            if p.get('proof_image'):
                lv['proof_image'] = p['proof_image']
                lv['proof_image_filename'] = 'proof.jpg'
            if l:
                l.write(lv)
            elif driver:
                lv.update({'sale_order_id': o.id, 'driver_id': driver.id})
                Line.create(lv)

        elif act == 'fail':
            o.write({'delivery_status': 'failed'})
            l = line_for()
            if l:
                l.write({'delivery_status': 'failed',
                         'failure_reason': (p.get('reason') or '')
                         .strip()})

        elif act == 'return':
            if role != 'manager':
                return fail('FORBIDDEN', 'Manager only', 403)
            o.write({'delivery_status': 'failed_returned'})
            l = line_for()
            if l:
                l.write({'delivery_status': 'failed_returned',
                         'failure_returned': True,
                         'failure_returned_date':
                             ofields.Datetime.now()})
        else:
            return fail('BAD_REQUEST', 'Unknown action %s' % act, 400)

        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok(_ser_order(o, role))

    # ── TRIPS: receive incoming orders at the sorting centre ──────────
    #   The carrier sees the trips Uellow dispatched to it, opens one, and
    #   receives each package — manually per row OR by scanning its barcode
    #   (the app matches the scanned code locally). "Receive all" can take in
    #   everything still pending or just the scanned ones; Uellow is notified.
    @http.route('/api/mobile/v2/carrier/trips', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def trips(self, **kw):
        user, role, company, driver = _ctx()
        if role != 'manager':
            return fail('FORBIDDEN', 'Manager only', 403)
        Trip = request.env['delivery.trip'].sudo()
        trips = Trip.search([
            ('carrier_company_id', '=', company.id),
            ('state', 'in', ('draft', 'assigned', 'in_progress')),
        ], order='date_trip desc, id desc', limit=100)
        out = [self._ser_trip(t) for t in trips]
        out = [t for t in out if t['total'] > 0]
        # trips with packages still to receive come first
        out.sort(key=lambda t: (t['pending'] == 0, ))
        return ok({'trips': out})

    @http.route('/api/mobile/v2/carrier/trips/<int:tid>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def trip_detail(self, tid, **kw):
        user, role, company, driver = _ctx()
        if role != 'manager':
            return fail('FORBIDDEN', 'Manager only', 403)
        trip = request.env['delivery.trip'].sudo().browse(tid)
        if not trip.exists() or trip.carrier_company_id.id != company.id:
            return fail('NOT_FOUND', 'Trip not found', 404)
        orders = []
        for line in trip.line_ids.sorted('sequence'):
            o = line.sale_order_id
            if not o:
                continue
            row = _ser_order(o, role)
            row['line_id'] = line.id
            # received AT SORTING = past the in-transit stages
            row['received'] = o.delivery_status not in (
                'pending', 'picked_up', False)
            # the scannable code on the package label
            row['code'] = (o.carrier_order_ref or o.name or '').strip()
            orders.append(row)
        return ok({'trip': self._ser_trip(trip), 'orders': orders})

    @http.route('/api/mobile/v2/carrier/trips/<int:tid>/receive',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_auth
    def trip_receive(self, tid, **kw):
        user, role, company, driver = _ctx()
        if role != 'manager':
            return fail('FORBIDDEN', 'Manager only', 403)
        trip = request.env['delivery.trip'].sudo().browse(tid)
        if not trip.exists() or trip.carrier_company_id.id != company.id:
            return fail('NOT_FOUND', 'Trip not found', 404)
        p = get_payload()
        order_ids = {int(x) for x in (p.get('order_ids') or []) if x}
        receive_missing = bool(p.get('receive_missing'))

        # Receivable at the sorting centre = still at Uellow ('pending', e.g.
        # the carrier picks up directly) OR brought in by the pickup courier
        # ('picked_up'). Either way they become 'arrived_sorting'.
        pending = trip.line_ids.mapped('sale_order_id').filtered(
            lambda o: o.delivery_status in ('pending', 'picked_up'))
        if receive_missing:
            to_receive = pending
        else:
            to_receive = pending.filtered(lambda o: o.id in order_ids)
        skipped = pending - to_receive

        # Receiving = order → 'arrived_sorting' (source of truth; the trip
        # line's stored-related status follows by recompute).
        for o in to_receive:
            o.with_context(skip_push=True).write(
                {'delivery_status': 'arrived_sorting'})
            o.message_post(body='📦 Received at sorting center by %s'
                           % (company.name or 'carrier'))
        # Notify Uellow about what was received (and what is still missing).
        if to_receive or skipped:
            body = ('🚚 %s received %d/%d package(s) of trip %s.'
                    % (company.name or 'Carrier', len(to_receive),
                       len(pending), trip.name))
            if skipped and not receive_missing:
                body += ' ⚠️ Not received: %s' % ', '.join(skipped.mapped('name'))
            self._notify_uellow(body, to_receive | skipped)
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({
            'received': len(to_receive),
            'remaining': len(pending - to_receive),
            'missing': [{'id': o.id, 'name': o.name} for o in skipped]
                       if not receive_missing else [],
            'trip': self._ser_trip(trip),
        })

    @http.route('/api/mobile/v2/carrier/trips/<int:tid>/assign-pickup',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_auth
    def trip_assign_pickup(self, tid, **kw):
        """Carrier assigns one of its drivers to COLLECT this trip from the
        Uellow warehouse (the pickup leg)."""
        user, role, company, driver = _ctx()
        if role != 'manager':
            return fail('FORBIDDEN', 'Manager only', 403)
        trip = request.env['delivery.trip'].sudo().browse(tid)
        if not trip.exists() or trip.carrier_company_id.id != company.id:
            return fail('NOT_FOUND', 'Trip not found', 404)
        p = get_payload()
        d = request.env['delivery.driver'].sudo().browse(int(p.get('driver_id') or 0))
        if not d.exists() or d.carrier_company_id.id != company.id:
            return fail('NOT_FOUND', 'Driver not found', 404)
        trip.action_assign_pickup(d, by='carrier')
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok(self._ser_trip(trip))

    def _ser_trip(self, trip):
        orders = trip.line_ids.mapped('sale_order_id')
        # receivable at the sorting centre = pending (direct) or picked_up
        # (brought in by the pickup courier)
        receivable = orders.filtered(
            lambda o: o.delivery_status in ('pending', 'picked_up'))
        return {
            'id': trip.id,
            'name': trip.name,
            'date': trip.date_trip.isoformat() if trip.date_trip else None,
            'state': trip.state,
            'total': len(orders),
            'pending': len(receivable),
            'received': len(orders) - len(receivable),
            'pickup_state': trip.pickup_state,
            'pickup_driver': {'id': trip.pickup_driver_id.id,
                              'name': trip.pickup_driver_id.name}
                             if trip.pickup_driver_id else None,
        }

    def _notify_uellow(self, body, orders):
        """Best-effort note to Uellow ops (chatter on the orders' partner +
        the orders themselves already carry the receipt messages)."""
        try:
            for o in orders[:1]:
                # one summary line on the first order keeps an audit trail
                o.message_post(body=body)
        except Exception:
            pass

    # ── drivers (manager) ────────────────────────────────────────────
    @http.route('/api/mobile/v2/carrier/drivers', type='http',
                auth='public', methods=['GET', 'POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_auth
    def drivers(self, **kw):
        user, role, company, driver = _ctx()
        if role != 'manager':
            return fail('FORBIDDEN', 'Manager only', 403)
        Sale = request.env['sale.order'].sudo()
        if request.httprequest.method == 'GET':
            today = datetime.utcnow().replace(hour=0, minute=0, second=0)
            out = []
            for d in company.driver_ids:
                base = [('delivery_driver_id', '=', d.id)]
                out.append({
                    'id': d.id, 'name': d.name, 'phone': d.phone,
                    'vehicle': d.vehicle_info or '',
                    'status': d.status,
                    'photo_url': '/web/image/delivery.driver/%d/photo'
                                 % d.id,
                    'active_orders': Sale.search_count(base + [
                        ('delivery_status', '=', 'out_for_delivery')]),
                    'today_delivered': Sale.search_count(base + [
                        ('delivery_status', '=', 'delivered'),
                        ('delivery_date_actual', '>=', today)]),
                    'total_delivered': Sale.search_count(base + [
                        ('delivery_status', '=', 'delivered')]),
                    'has_login': bool(d.portal_user_id),
                })
            return ok({'drivers': out})
        # POST — create a driver (+ optional app login)
        p = get_payload()
        name = (p.get('name') or '').strip()
        phone = (p.get('phone') or '').strip()
        if not name or not phone:
            return fail('BAD_REQUEST', 'name and phone required')
        vals = {'name': name, 'phone': phone,
                'vehicle_info': (p.get('vehicle') or '').strip(),
                'carrier_company_id': company.id}
        email = (p.get('email') or '').strip().lower()
        password = p.get('password') or ''
        if email and password:
            Users = request.env['res.users'].sudo()
            if Users.search_count([('login', '=', email)]):
                return fail('EXISTS',
                            'A user with this email already exists /'
                            ' يوجد مستخدم بهذا البريد', 400)
            groups = [request.env.ref('base.group_portal').id]
            try:
                groups.append(request.env.ref(
                    'delivery_carrier_portal.group_carrier_driver').id)
            except Exception:
                pass
            new_user = Users.create({
                'name': name, 'login': email, 'email': email,
                'password': password,
                'groups_id': [(6, 0, groups)],
            })
            vals['portal_user_id'] = new_user.id
        d = request.env['delivery.driver'].sudo().create(vals)
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'id': d.id, 'name': d.name,
                   'has_login': bool(d.portal_user_id)})

    # ── cash + remittances (manager) ─────────────────────────────────
    @http.route('/api/mobile/v2/carrier/cash', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def cash(self, **kw):
        user, role, company, driver = _ctx()
        if role != 'manager':
            return fail('FORBIDDEN', 'Manager only', 403)
        Sale = request.env['sale.order'].sudo()
        base = [('delivery_carrier_company_id', '=', company.id)]
        cash_ready = Sale.search(base + [
            ('payment_method_type', '=', 'cash'),
            ('cash_collection_status', '=', 'collected')])
        online_ready = Sale.search(base + [
            ('payment_method_type', '!=', 'cash'),
            ('delivery_status', '=', 'delivered'),
            ('carrier_portal_remittance_id', '=', False)])
        rems = request.env['delivery.cash.remittance'].sudo().search(
            [('carrier_company_id', '=', company.id)],
            order='create_date desc', limit=30)
        return ok({
            'cash_ready': [_ser_order(o, role) for o in cash_ready],
            'online_ready': [_ser_order(o, role) for o in online_ready],
            'cash_total': round(sum(cash_ready.mapped('amount_total')), 3),
            'remittances': [{
                'id': r.id, 'name': r.name, 'state': r.state,
                'total': round(sum(r.line_ids.mapped('amount')), 3),
                'orders': len(r.line_ids),
                'date': r.create_date.isoformat()
                        if r.create_date else None,
            } for r in rems],
        })

    @http.route('/api/mobile/v2/carrier/cash/remit', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def remit(self, **kw):
        user, role, company, driver = _ctx()
        if role != 'manager':
            return fail('FORBIDDEN', 'Manager only', 403)
        p = get_payload()
        ids = [int(x) for x in (p.get('order_ids') or [])
               if str(x).lstrip('-').isdigit()]
        if not ids:
            return fail('BAD_REQUEST', 'order_ids required')
        Sale = request.env['sale.order'].sudo()
        all_orders = Sale.browse(ids)
        cash_orders = all_orders.filtered(
            lambda o: o.delivery_carrier_company_id.id == company.id
            and o.payment_method_type == 'cash'
            and o.cash_collection_status == 'collected')
        online_orders = all_orders.filtered(
            lambda o: o.delivery_carrier_company_id.id == company.id
            and o.payment_method_type != 'cash'
            and o.delivery_status == 'delivered'
            and not o.carrier_portal_remittance_id)
        valid = cash_orders | online_orders
        if not valid:
            return fail('NO_VALID', 'No valid orders to remit /'
                        ' لا توجد طلبات صالحة للتسوية', 400)
        rem = request.env['delivery.cash.remittance'].sudo().create({
            'carrier_company_id': company.id,
            'settlement_mode': 'per_order',
            'state': 'pending',
            'carrier_ref': (p.get('carrier_ref') or '').strip(),
            'line_ids': [(0, 0, {
                'order_id': o.id,
                'amount': o.amount_total
                          if o.payment_method_type == 'cash' else 0,
            }) for o in valid],
        })
        if online_orders:
            online_orders.write({'carrier_portal_remittance_id': rem.id})
        try:
            request.env.cr.commit()
        except Exception:
            pass
        return ok({'id': rem.id, 'name': rem.name,
                   'orders': len(valid)})

    # ── stats (charts) ───────────────────────────────────────────────
    @http.route('/api/mobile/v2/carrier/stats', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def stats(self, **kw):
        user, role, company, driver = _ctx()
        if not role:
            return fail('NOT_CARRIER', 'Carrier account required', 403)
        Sale = request.env['sale.order'].sudo()
        dom = _scope_domain(role, company, driver)
        days = []
        today = datetime.utcnow().replace(hour=0, minute=0, second=0)
        for i in range(13, -1, -1):
            d0 = today - timedelta(days=i)
            d1 = d0 + timedelta(days=1)
            delivered = Sale.search(dom + [
                ('delivery_status', '=', 'delivered'),
                ('delivery_date_actual', '>=', d0),
                ('delivery_date_actual', '<', d1)])
            days.append({
                'date': d0.strftime('%Y-%m-%d'),
                'delivered': len(delivered),
                'cod': round(sum(o.amount_total for o in delivered
                                 if o.payment_method_type == 'cash'), 3),
            })
        breakdown = {st: Sale.search_count(
            dom + [('delivery_status', '=', st)])
            for st in STATUS_LABELS}
        top = []
        if role == 'manager':
            month = today.replace(day=1)
            for d in company.driver_ids:
                n = Sale.search_count([
                    ('delivery_driver_id', '=', d.id),
                    ('delivery_status', '=', 'delivered'),
                    ('delivery_date_actual', '>=', month)])
                if n:
                    top.append({'name': d.name, 'delivered': n})
            top.sort(key=lambda x: -x['delivered'])
        return ok({'days': days, 'breakdown': breakdown,
                   'top_drivers': top[:10]})
