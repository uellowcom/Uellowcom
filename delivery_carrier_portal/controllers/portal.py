# -*- coding: utf-8 -*-
import requests
import logging
from datetime import date
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

PER_PAGE = 50


def _get_carrier_company(user_id):
    return request.env['delivery.carrier.company'].sudo().search(
        [('portal_user_ids', 'in', user_id), ('active', '=', True)], limit=1
    )


def _get_driver(user_id):
    return request.env['delivery.driver'].sudo().search(
        [('portal_user_id', '=', user_id), ('active', '=', True)], limit=1
    )


def _check_user_group(user_id, xmlid):
    try:
        module, name = xmlid.split('.')
        request.env.cr.execute("""
            SELECT 1 FROM res_groups_users_rel gu
            JOIN ir_model_data imd ON imd.model = 'res.groups' AND imd.res_id = gu.gid
            WHERE imd.module = %s AND imd.name = %s AND gu.uid = %s LIMIT 1
        """, (module, name, user_id))
        return bool(request.env.cr.fetchone())
    except Exception as e:
        _logger.warning("_check_user_group error: %s", e)
        return False


def _is_arabic(request_obj):
    """Detect if user prefers Arabic."""
    lang = (
        request_obj.httprequest.cookies.get('frontend_lang') or
        request_obj.httprequest.accept_languages.best or
        request_obj.env.lang or
        'en'
    )
    return str(lang).startswith('ar')


def _is_manager(uid):
    return _check_user_group(uid, 'delivery_carrier_portal.group_carrier_manager')


def _is_driver(uid):
    return _check_user_group(uid, 'delivery_carrier_portal.group_carrier_driver')


def _full_address(partner):
    parts = []
    if partner.street:     parts.append(partner.street)
    if partner.street2:    parts.append(partner.street2)
    if partner.city:       parts.append(partner.city)
    if partner.state_id:   parts.append(partner.state_id.name)
    if partner.country_id: parts.append(partner.country_id.name)
    return ', '.join(parts) if parts else '—'


def _paginate(records, page, per_page=PER_PAGE):
    """Return page slice and pagination info."""
    page = max(1, int(page or 1))
    total = len(records)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    start = (page - 1) * per_page
    end = start + per_page
    return records[start:end], {
        'page': page,
        'total_pages': total_pages,
        'total': total,
        'per_page': per_page,
        'has_prev': page > 1,
        'has_next': page < total_pages,
    }


class DeliveryPortalController(http.Controller):

    # ─── Backend Dashboard Page ──────────────────────────────────────────
    @http.route('/delivery/dashboard', type='http', auth='user')
    def backend_dashboard(self, **kwargs):
        """Standalone backend dashboard page."""
        env = request.env
        carriers = env['delivery.carrier.company'].sudo().search([('active', '=', True)])
        return request.render('delivery_carrier_portal.backend_dashboard', {
            'carriers': carriers,
        })

    # ─── Dashboard ───────────────────────────────────────────────────────
    @http.route('/delivery-portal', type='http', auth='user', website=True)
    def portal_redirect(self, **kwargs):
        return request.redirect('/delivery-portal/dashboard')

    @http.route('/delivery-portal/dashboard', type='http', auth='user', website=True)
    def dashboard(self, **kwargs):
        uid = request.env.user.id
        if _is_manager(uid):
            company = _get_carrier_company(uid)
            if not company:
                return request.render('delivery_carrier_portal.portal_no_access')
            orders = request.env['sale.order'].sudo().search([
                ('delivery_carrier_company_id', '=', company.id),
                ('delivery_carrier_company_id', '=', company.id),
            ], order='date_order desc')
            return request.render('delivery_carrier_portal.portal_dashboard', {
                'company': company,
                'pending_count':    len(orders.filtered(lambda o: o.delivery_status == 'assigned')),
                'assigned_count':   len(orders.filtered(lambda o: o.delivery_status == 'assigned')),
                'in_transit_count': len(orders.filtered(lambda o: o.delivery_status == 'out_for_delivery')),
                'delivered_count':  len(orders.filtered(lambda o: o.delivery_status == 'delivered')),
                'failed_count':     len(orders.filtered(lambda o: o.delivery_status in ('failed', 'failed_returned'))),
                'pending_cash':     sum(orders.filtered(
                    lambda o: o.payment_method_type == 'cash'
                    and o.cash_collection_status in ('pending', 'collected')
                    and o.delivery_status == 'delivered'
                ).mapped('amount_total')),
                'recent_orders': orders[:10],
                'role': 'manager',
            })
        elif _is_driver(uid):
            return request.redirect('/delivery-portal/driver/orders')
        return request.render('delivery_carrier_portal.portal_no_access')

    # ─── Orders List ─────────────────────────────────────────────────────
    @http.route('/delivery-portal/orders', type='http', auth='user', website=True)
    def orders_list(self, status='all', search='', page=1, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return request.redirect('/delivery-portal/dashboard')
        company = _get_carrier_company(uid)
        if not company:
            return request.render('delivery_carrier_portal.portal_no_access')

        domain = [
            ('delivery_carrier_company_id', '=', company.id),
            ('delivery_carrier_company_id', '=', company.id),
        ]
        if status != 'all':
            domain.append(('delivery_status', '=', status))
        if search:
            domain.append(('name', 'ilike', search))

        all_orders = request.env['sale.order'].sudo().search(domain, order='date_order desc')
        orders_page, pager = _paginate(all_orders, page)

        return request.render('delivery_carrier_portal.portal_orders', {
            'company': company,
            'orders': orders_page,
            'current_status': status,
            'search': search,
            'pager': pager,
            'role': 'manager',
        })

    # ─── Trips List ──────────────────────────────────────────────────────
    @http.route('/delivery-portal/trips', type='http', auth='user', website=True)
    def trips_list(self, search='', page=1, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return request.redirect('/delivery-portal/dashboard')
        company = _get_carrier_company(uid)
        if not company:
            return request.render('delivery_carrier_portal.portal_no_access')

        domain = [('carrier_company_id', '=', company.id)]
        if search:
            domain.append(('name', 'ilike', search))

        all_trips = request.env['delivery.trip'].sudo().search(domain, order='date_trip desc')
        trips_page, pager = _paginate(all_trips, page)

        return request.render('delivery_carrier_portal.portal_trips', {
            'company': company,
            'trips': trips_page,
            'search': search,
            'pager': pager,
            'role': 'manager',
        })

    # ─── Trip Detail ──────────────────────────────────────────────────────
    @http.route('/delivery-portal/trip/<int:trip_id>', type='http', auth='user', website=True)
    def trip_detail(self, trip_id, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return request.redirect('/delivery-portal/dashboard')
        company = _get_carrier_company(uid)
        trip = request.env['delivery.trip'].sudo().browse(trip_id)
        if not trip.exists() or trip.carrier_company_id.id != company.id:
            return request.not_found()
        return request.render('delivery_carrier_portal.portal_trip_detail', {
            'company': company, 'trip': trip, 'role': 'manager',
        })

    # ─── Order Detail ─────────────────────────────────────────────────────
    @http.route('/delivery-portal/order/<int:order_id>', type='http', auth='user', website=True)
    def order_detail(self, order_id, **kwargs):
        uid = request.env.user.id
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return request.not_found()

        if _is_manager(uid):
            company = _get_carrier_company(uid)
            if not company or order.delivery_carrier_company_id.id != company.id:
                return request.not_found()
            drivers = request.env['delivery.driver'].sudo().search(
                [('carrier_company_id', '=', company.id), ('active', '=', True)]
            )
            return request.render('delivery_carrier_portal.portal_order_detail', {
                'order': order, 'company': company, 'drivers': drivers,
                'full_address': _full_address(order.partner_id),
                'can_send_payment_link': True,
                'role': 'manager',
            })
        elif _is_driver(uid):
            driver = _get_driver(uid)
            if not driver:
                return request.not_found()
            line = request.env['delivery.trip.line'].sudo().search([
                ('sale_order_id', '=', order_id),
                ('driver_id', '=', driver.id),
            ], limit=1)
            if not line:
                return request.not_found()
            return request.render('delivery_carrier_portal.portal_order_detail', {
                'order': order, 'driver': driver, 'trip_line': line,
                'full_address': _full_address(order.partner_id),
                'can_send_payment_link': driver.can_send_payment_link,
                'role': 'driver',
            })
        return request.not_found()

    # ─── Driver Orders ────────────────────────────────────────────────────
    @http.route('/delivery-portal/driver/orders', type='http', auth='user', website=True)
    def driver_orders(self, status='active', search='', page=1, **kwargs):
        uid = request.env.user.id
        if not _is_driver(uid):
            return request.redirect('/delivery-portal/dashboard')
        driver = _get_driver(uid)
        if not driver:
            return request.render('delivery_carrier_portal.portal_no_access')

        # Get all orders assigned to this driver — use sale.order as source of truth
        all_orders = request.env['sale.order'].sudo().search([
            ('delivery_driver_id', '=', driver.id),
            ('delivery_carrier_company_id', '=', driver.carrier_company_id.id),
        ], order='date_order desc')

        # Also get orders from trip lines (in case driver_id not set directly)
        try:
            trip_lines = request.env['delivery.trip.line'].sudo().search(
                [('driver_id', '=', driver.id)], order='id desc'
            )
            trip_order_ids = trip_lines.mapped('sale_order_id').ids
            extra_orders = request.env['sale.order'].sudo().search([
                ('id', 'in', trip_order_ids),
                ('delivery_carrier_company_id', '=', company.id),
                ('id', 'not in', all_orders.ids),
            ])
            all_orders = all_orders | extra_orders
        except Exception as e:
            _logger.warning("Trip lines error: %s", e)

        # Filter by search
        if search:
            all_orders = all_orders.filtered(
                lambda o: search.lower() in (o.name or '').lower()
                or search.lower() in (o.partner_id.name or '').lower()
            )

        today = date.today()
        # Filter by status using sale.order.delivery_status (source of truth)
        active_orders    = all_orders.filtered(lambda o: o.delivery_status in ('assigned', 'out_for_delivery'))
        delivered_orders = all_orders.filtered(lambda o: o.delivery_status == 'delivered')
        failed_orders    = all_orders.filtered(lambda o: o.delivery_status in ('failed', 'failed_returned'))

        # Select orders based on tab
        if status == 'active':
            tab_orders = active_orders
        elif status == 'delivered':
            tab_orders = delivered_orders
        elif status == 'failed':
            tab_orders = failed_orders
        else:
            tab_orders = all_orders

        # Keep backward compat vars
        all_lines = all_orders
        pending_lines   = active_orders
        delivered_lines = delivered_orders
        failed_lines    = failed_orders
        tab_lines       = tab_orders

        lines_page, pager = _paginate(tab_lines, page)

        try:
            today_delivered = delivered_lines.filtered(
                lambda o: o.delivery_date_actual and o.delivery_date_actual.date() == today
            )
            today_cash = sum(
                o.amount_total
                for o in today_delivered
                if o.payment_method_type == 'cash'
            )
        except Exception as e:
            _logger.warning("today_cash error: %s", e)
            today_cash = 0.0

        return request.render('delivery_carrier_portal.portal_driver_orders', {
            'driver': driver,
            'lines_page': lines_page,
            'pending_lines': pending_lines,
            'delivered_lines': delivered_lines,
            'failed_lines': failed_lines,
            'pending_count':   len(pending_lines),
            'delivered_count': len(delivered_lines),
            'failed_count':    len(failed_lines),
            'today_cash': today_cash,
            'current_tab': status,
            'search': search,
            'pager': pager,
            'role': 'driver',
        })

    # ─── Cash Management ──────────────────────────────────────────────────
    # ─── Remittance New ──────────────────────────────────────────────────
    @http.route('/delivery-portal/remittance/new', type='http', auth='user', website=True)
    def remittance_new(self, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return request.redirect('/delivery-portal/dashboard')
        company = _get_carrier_company(uid)
        if not company:
            return request.render('delivery_carrier_portal.portal_no_access')

        # Cash orders: delivered or failed+returned, collected, not yet remitted
        cash_orders = request.env['sale.order'].sudo().search([
            ('delivery_carrier_company_id', '=', company.id),
            ('payment_method_type', '=', 'cash'),
            ('cash_collection_status', '=', 'collected'),
            ('delivery_status', 'in', ('delivered', 'failed_returned')),
        ], order='date_order desc')

        # Online orders: delivered, not yet in a remittance, have a carrier cost
        online_orders = request.env['sale.order'].sudo().search([
            ('delivery_carrier_company_id', '=', company.id),
            ('payment_method_type', '!=', 'cash'),
            ('delivery_status', '=', 'delivered'),
            ('carrier_portal_remittance_id', '=', False),
        ], order='date_order desc')

        all_orders = cash_orders | online_orders

        return request.render('delivery_carrier_portal.portal_remittance_new', {
            'company':         company,
            'orders':          all_orders,
            'cash_orders':     cash_orders,
            'online_orders':   online_orders,
            'total_delivered': len(all_orders.filtered(lambda o: o.delivery_status == 'delivered')),
            'total_returned':  len(all_orders.filtered(lambda o: o.delivery_status == 'failed_returned')),
            'total_cash':      round(sum(cash_orders.mapped('amount_total')), 3),
            'role': 'manager',
        })

    # ─── Remittance Submit ────────────────────────────────────────────────
    @http.route('/delivery-portal/remittance/submit', type='json', auth='user', website=True, csrf=False)
    def remittance_submit(self, order_ids=None, carrier_ref='', **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return {'success': False}
        company = _get_carrier_company(uid)
        if not company or not order_ids:
            return {'success': False}

        all_orders = request.env['sale.order'].sudo().browse(order_ids)

        # Cash orders: must be collected
        cash_orders = all_orders.filtered(
            lambda o: o.delivery_carrier_company_id.id == company.id
            and o.payment_method_type == 'cash'
            and o.cash_collection_status == 'collected'
        )
        # Online orders: must be delivered and not yet remitted
        online_orders = all_orders.filtered(
            lambda o: o.delivery_carrier_company_id.id == company.id
            and o.payment_method_type != 'cash'
            and o.delivery_status == 'delivered'
            and not o.carrier_portal_remittance_id
        )
        valid_orders = cash_orders | online_orders
        if not valid_orders:
            return {'success': False, 'error': 'No valid orders'}

        rem = request.env['delivery.cash.remittance'].sudo().create({
            'carrier_company_id': company.id,
            'settlement_mode': 'per_order',
            'state': 'pending',
            'carrier_ref': carrier_ref or '',
            'line_ids': [(0, 0, {
                'order_id': o.id,
                'amount': o.amount_total if o.payment_method_type == 'cash' else 0,
            }) for o in valid_orders],
        })

        # Link online orders to this remittance so they won't appear again
        if online_orders:
            online_orders.write({'carrier_portal_remittance_id': rem.id})

        return {'success': True, 'remittance_id': rem.id, 'name': rem.name}

    # ─── Remittance Print ────────────────────────────────────────────────
    @http.route('/delivery-portal/remittance/<int:rem_id>/print', type='http', auth='user', website=True)
    def remittance_print(self, rem_id, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return request.redirect('/delivery-portal/dashboard')
        company = _get_carrier_company(uid)
        rem = request.env['delivery.cash.remittance'].sudo().browse(rem_id)
        if not rem.exists() or rem.carrier_company_id.id != company.id:
            return request.not_found()

        # Generate PDF via Odoo QWeb report
        pdf_content, content_type = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'delivery_carrier_portal.action_settlement_report', [rem_id]
        )
        return request.make_response(pdf_content, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', f'inline; filename="Settlement-{rem.name}.pdf"'),
        ])

    # ─── Remittance Detail (Portal) ───────────────────────────────────────
    @http.route('/delivery-portal/remittance/<int:rem_id>', type='http', auth='user', website=True)
    def remittance_detail(self, rem_id, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return request.redirect('/delivery-portal/dashboard')
        company = _get_carrier_company(uid)
        rem = request.env['delivery.cash.remittance'].sudo().browse(rem_id)
        if not rem.exists() or rem.carrier_company_id.id != company.id:
            return request.not_found()
        return request.render('delivery_carrier_portal.portal_remittance_detail', {
            'company': company,
            'rem': rem,
            'role': 'manager',
        })

    @http.route('/delivery-portal/cash', type='http', auth='user', website=True)
    def cash_management(self, search='', page=1, tab='ready', **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return request.redirect('/delivery-portal/dashboard')
        company = _get_carrier_company(uid)
        if not company:
            return request.render('delivery_carrier_portal.portal_no_access')

        # Base domain — filter by tab
        domain = [
            ('delivery_carrier_company_id', '=', company.id),
            ('payment_method_type', '=', 'cash'),
        ]
        if tab == 'ready':
            # Show only collected & delivered — ready to remit
            domain += [
                ('cash_collection_status', '=', 'collected'),
                ('delivery_status', 'in', ('delivered', 'failed_returned')),
            ]
        elif tab == 'all':
            pass  # show all
        # pending/done tabs show remittance tables, not orders
        if search:
            domain.append(('name', 'ilike', search))

        all_cash = request.env['sale.order'].sudo().search(domain, order='date_order desc')
        cash_page, pager = _paginate(all_cash, page)

        remittances = request.env['delivery.cash.remittance'].sudo().search(
            [('carrier_company_id', '=', company.id)], order='create_date desc', limit=50
        )
        pending_amount = sum(all_cash.filtered(
            lambda o: o.cash_collection_status in ('pending', 'collected')
            and o.delivery_status == 'delivered'
        ).mapped('amount_total'))
        in_remittance = sum(remittances.filtered(lambda r: r.state == 'pending').mapped('total_amount'))
        rem_pending = remittances.filtered(lambda r: r.state == 'pending')
        rem_done    = remittances.filtered(lambda r: r.state in ('remitted', 'partial', 'rejected'))

        return request.render('delivery_carrier_portal.portal_cash', {
            'company': company,
            'cash_orders': cash_page,
            'remittances': remittances,
            'rem_pending': rem_pending,
            'rem_done': rem_done,
            'pending_amount': pending_amount,
            'in_remittance': in_remittance,
            'search': search,
            'pager': pager,
            'tab': tab,
            'role': 'manager',
        })

    # ─── AJAX: Receive at Sorting Center ────────────────────────────────
    @http.route('/delivery-portal/receive-order', type='json', csrf=False, auth='user', website=True)
    def receive_order(self, order_id, line_id=None, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return {'success': False, 'error': 'Access denied'}
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'success': False, 'error': 'Order not found'}
        order.write({'delivery_status': 'arrived_sorting'})
        # Update trip line status too if provided
        if line_id:
            line = request.env['delivery.trip.line'].sudo().browse(line_id)
            if line.exists():
                line.write({'delivery_status': 'arrived_sorting'})
        return {'success': True}

    @http.route('/delivery-portal/no-receive-order', type='json', csrf=False, auth='user', website=True)
    def no_receive_order(self, order_id, line_id=None, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return {'success': False, 'error': 'Access denied'}
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'success': False, 'error': 'Order not found'}
        order.write({'delivery_status': 'failed_returned'})
        if line_id:
            line = request.env['delivery.trip.line'].sudo().browse(line_id)
            if line.exists():
                line.write({'delivery_status': 'failed_returned'})
        return {'success': True}

    # ─── AJAX: Confirm Delivery ───────────────────────────────────────────
    @http.route('/delivery-portal/confirm-delivery', type='json', csrf=False, auth='user', website=True)
    def confirm_delivery(self, order_id, proof_image=None, proof_image_name=None,
                         proof_signature=None, notes='', delivery_lat=None, delivery_lng=None, **kwargs):
        uid   = request.env.user.id
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists():
            return {'success': False}
        vals = {'delivery_status': 'delivered', 'delivery_date_actual': fields.Datetime.now()}
        if order.payment_method_type == 'cash':
            vals['cash_collection_status'] = 'collected'
        # Save GPS location if provided
        if delivery_lat and delivery_lng:
            vals['delivery_lat'] = float(delivery_lat)
            vals['delivery_lng'] = float(delivery_lng)
        order.write(vals)

        # Update trip line
        if _is_driver(uid):
            driver = _get_driver(uid)
            line = request.env['delivery.trip.line'].sudo().search([
                ('sale_order_id', '=', order.id), ('driver_id', '=', driver.id),
            ], limit=1)
        else:
            line = request.env['delivery.trip.line'].sudo().search([
                ('sale_order_id', '=', order.id),
            ], limit=1)

        if line:
            lv = {'delivery_status': 'delivered',
                  'delivery_date_actual': fields.Datetime.now(), 'notes': notes}
            if proof_image:
                lv['proof_image'] = proof_image
                lv['proof_image_filename'] = proof_image_name or 'proof.jpg'
            if proof_signature:
                lv['proof_signature'] = proof_signature
            line.write(lv)
        return {'success': True}

    # ─── AJAX: Fail Delivery ──────────────────────────────────────────────
    @http.route('/delivery-portal/fail-delivery', type='json', csrf=False, auth='user', website=True)
    def fail_delivery(self, order_id, reason='', **kwargs):
        uid   = request.env.user.id
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists():
            return {'success': False}
        order.write({'delivery_status': 'failed'})
        if _is_driver(uid):
            driver = _get_driver(uid)
            line = request.env['delivery.trip.line'].sudo().search([
                ('sale_order_id', '=', order.id), ('driver_id', '=', driver.id),
            ], limit=1)
            if line:
                line.write({'delivery_status': 'failed', 'failure_reason': reason})
        return {'success': True}

    # ─── AJAX: Mark Returned ─────────────────────────────────────────────
    @http.route('/delivery-portal/mark-returned', type='json', csrf=False, auth='user', website=True)
    def mark_returned(self, order_id, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return {'success': False}
        company = _get_carrier_company(uid)
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists() or order.delivery_carrier_company_id.id != company.id:
            return {'success': False}
        order.write({'delivery_status': 'failed_returned'})
        line = request.env['delivery.trip.line'].sudo().search(
            [('sale_order_id', '=', order.id)], limit=1
        )
        if line:
            line.write({
                'delivery_status': 'failed_returned',
                'failure_returned': True,
                'failure_returned_date': fields.Datetime.now(),
            })
        return {'success': True}

    # ─── AJAX: Assign Driver ──────────────────────────────────────────────
    @http.route('/delivery-portal/assign-driver', type='json', csrf=False, auth='user', website=True)
    def assign_driver(self, order_id, driver_id, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return {'success': False}
        company = _get_carrier_company(uid)
        order  = request.env['sale.order'].sudo().browse(int(order_id))
        driver = request.env['delivery.driver'].sudo().browse(int(driver_id))
        if not order.exists() or not driver.exists():
            return {'success': False, 'error': 'Record not found'}
        if order.delivery_carrier_company_id.id != company.id:
            return {'success': False, 'error': 'Order not in your company'}
        if driver.carrier_company_id.id != company.id:
            return {'success': False, 'error': 'Driver not in your company'}
        if order.delivery_status == 'delivered':
            return {'success': False, 'error': 'Order already delivered'}

        order.write({'delivery_driver_id': driver.id, 'delivery_status': 'out_for_delivery'})
        line = request.env['delivery.trip.line'].sudo().search(
            [('sale_order_id', '=', order.id)], limit=1
        )
        if line:
            line.write({'driver_id': driver.id, 'delivery_status': 'out_for_delivery'})
        else:
            request.env['delivery.trip.line'].sudo().create({
                'sale_order_id': order.id,
                'driver_id': driver.id,
                'delivery_status': 'out_for_delivery',
            })
        return {'success': True, 'driver_name': driver.name}

    # ─── AJAX: Unassign Driver ────────────────────────────────────────────
    @http.route('/delivery-portal/unassign-driver', type='json', csrf=False, auth='user', website=True)
    def unassign_driver(self, order_id, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return {'success': False}
        company = _get_carrier_company(uid)
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists() or order.delivery_carrier_company_id.id != company.id:
            return {'success': False}
        if order.delivery_status in ('delivered',) or order.cash_collection_status == 'remitted':
            return {'success': False, 'error': 'Cannot unassign'}
        order.write({'delivery_driver_id': False, 'delivery_status': 'assigned'})
        line = request.env['delivery.trip.line'].sudo().search(
            [('sale_order_id', '=', order.id)], limit=1
        )
        if line:
            line.write({'driver_id': False, 'delivery_status': 'pending'})
        return {'success': True}

    # ─── Reverse Geocode ──────────────────────────────────────────────────
    @http.route('/delivery-portal/reverse-geocode', type='json', csrf=False, auth='user', website=True)
    def reverse_geocode(self, lat=None, lng=None, **kwargs):
        if not lat or not lng:
            return {}
        try:
            resp = requests.get(
                f"https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat={lat}&lon={lng}&accept-language=ar,en",
                timeout=5, headers={'User-Agent': 'UellowDelivery/1.0'}
            )
            data = resp.json()
            addr = data.get('address', {})
            return {
                'display': data.get('display_name', ''),
                'city': addr.get('city') or addr.get('town') or addr.get('village') or '',
                'state': addr.get('state') or '',
                'street': addr.get('road') or '',
            }
        except Exception as e:
            _logger.warning("Reverse geocode error: %s", e)
            return {}

    # ─── Returns List ─────────────────────────────────────────────────────
    @http.route('/delivery-portal/returns', type='http', auth='user', website=True)
    def returns_list(self, filter='all', search='', **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return request.redirect('/delivery-portal/dashboard')
        company = _get_carrier_company(uid)
        if not company:
            return request.render('delivery_carrier_portal.portal_no_access')

        domain = [
            ('delivery_carrier_company_id', '=', company.id),
            ('delivery_status', 'in', ['failed', 'failed_returned']),
        ]
        if filter == 'awaiting':
            domain.append(('return_status', '=', 'awaiting_return'))
        elif filter == 'scheduled':
            domain.append(('return_status', 'in', ['return_scheduled', 'return_in_transit']))
        elif filter == 'received':
            domain.append(('return_status', '=', 'returned_received'))

        if search:
            domain.append(('name', 'ilike', search))

        orders = request.env['sale.order'].sudo().search(domain, order='date_order desc')

        return request.render('delivery_carrier_portal.portal_returns', {
            'company': company,
            'orders': orders,
            'current_filter': filter,
            'search': search,
            'awaiting_count': len(orders.filtered(lambda o: o.return_status == 'awaiting_return')),
            'transit_count':  len(orders.filtered(lambda o: o.return_status in ('return_scheduled', 'return_in_transit'))),
            'received_count': len(orders.filtered(lambda o: o.return_status == 'returned_received')),
            'role': 'manager',
        })

    # ─── AJAX: Schedule Return ────────────────────────────────────────────
    @http.route('/delivery-portal/schedule-return', type='json', csrf=False, auth='user', website=True)
    def schedule_return(self, order_id, scheduled_date=None, notes='', **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return {'success': False}
        company = _get_carrier_company(uid)
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists() or order.delivery_carrier_company_id.id != company.id:
            return {'success': False}

        vals = {'return_status': 'return_scheduled', 'return_notes': notes}
        if scheduled_date:
            # Handle datetime-local format: "2026-05-20T21:10" or "2026-05-20 21:10:00"
            try:
                from datetime import datetime
                dt_str = scheduled_date.replace('T', ' ')
                # Add seconds if missing
                if len(dt_str) == 16:  # "2026-05-20 21:10"
                    dt_str += ':00'
                vals['return_scheduled_date'] = dt_str
            except Exception:
                pass
        order.write(vals)
        return {'success': True}

    # ─── AJAX: Mark Return In Transit ─────────────────────────────────────
    @http.route('/delivery-portal/return-in-transit', type='json', csrf=False, auth='user', website=True)
    def return_in_transit(self, order_id, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return {'success': False}
        company = _get_carrier_company(uid)
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists() or order.delivery_carrier_company_id.id != company.id:
            return {'success': False}
        order.write({'return_status': 'return_in_transit'})
        return {'success': True}

    # ─── AJAX: Confirm Return Received (Backend / Portal) ─────────────────
    @http.route('/delivery-portal/confirm-return', type='json', csrf=False, auth='user', website=True)
    def confirm_return(self, order_id, received_by='', notes='',
                       signature=None, checklist_ok=False, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return {'success': False}
        company = _get_carrier_company(uid)
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists() or order.delivery_carrier_company_id.id != company.id:
            return {'success': False}
        vals = {
            'return_status':        'returned_received',
            'return_received_date': fields.Datetime.now(),
            'return_received_by':   received_by,
            'return_notes':         notes,
            'return_checklist_ok':  checklist_ok,
            'delivery_status':      'failed_returned',
        }
        if signature:
            vals['return_signature'] = signature
        order.write(vals)
        return {'success': True}

    # ─── AJAX: Start Delivery (Driver) ────────────────────────────────────
    @http.route('/delivery-portal/start-delivery', type='json', csrf=False, auth='user', website=True)
    def start_delivery(self, order_id, **kwargs):
        uid = request.env.user.id
        if not _is_driver(uid):
            return {'success': False}
        driver = _get_driver(uid)
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists():
            return {'success': False}

        order.write({'delivery_status': 'out_for_delivery'})
        line = request.env['delivery.trip.line'].sudo().search([
            ('sale_order_id', '=', order.id),
            ('driver_id', '=', driver.id),
        ], limit=1)
        if line:
            line.write({'delivery_status': 'out_for_delivery'})

        # Build WhatsApp message
        partner = order.partner_id
        phone = (partner.mobile or partner.phone or '').replace(' ', '').replace('+', '').replace('-', '')
        amount = '%.3f' % order.amount_total
        payment_ar = 'كاش عند الاستلام' if order.payment_method_type == 'cash' else 'أونلاين مدفوع'
        payment_en = 'Cash on Delivery' if order.payment_method_type == 'cash' else 'Paid Online'

        msg_ar = f'🚚 طلبك في الطريق إليك!\n\nمرحباً {partner.name} 👋\nطلبك رقم {order.name} في طريقه إليك الآن.\n\n📦 تفاصيل الطلب:\n• المبلغ: KD {amount}\n• الدفع: {payment_ar}\n• السائق: {driver.name}\n\nيرجى التجهّز لاستلام طلبك 🙏\n\nUellow W.L.L | يلو'
        msg_en = f'🚚 Your order is on the way!\n\nHello {partner.name} 👋\nYour order {order.name} is now out for delivery.\n\n📦 Order Details:\n• Amount: KD {amount}\n• Payment: {payment_en}\n• Driver: {driver.name}\n\nPlease be ready to receive your order 🙏\n\nUellow W.L.L'

        return {
            'success': True,
            'phone': phone,
            'msg_ar': msg_ar,
            'msg_en': msg_en,
        }

    # ─── Generate Payment Link ───────────────────────────────────────────
    @http.route('/delivery-portal/get-payment-link', type='json', auth='user', website=True, csrf=False)
    def get_payment_link(self, order_id=None, **kwargs):
        uid = request.env.user.id
        if _is_driver(uid):
            driver = _get_driver(uid)
            if not driver or not driver.can_send_payment_link:
                return {'success': False, 'error': 'Not authorized'}
        elif not _is_manager(uid):
            return {'success': False}

        if not order_id:
            return {'success': False, 'error': 'No order_id'}

        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists():
            return {'success': False, 'error': 'Order not found'}

        try:
            import requests as req_lib
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', 'https://www.uellow.com')

            # Get UPayments API key from payment provider
            upay_provider = request.env['payment.provider'].sudo().search(
                [('code', '=', 'upayments'), ('state', '=', 'enabled')], limit=1
            )
            upay_key = getattr(upay_provider, 'upay_application_key', '') if upay_provider else ''
            _logger.info("UPayments key found: %s", bool(upay_key))

            if upay_key:
                try:
                    payload = {
                        "order": {
                            "id": order.name,
                            "reference": order.name,
                            "description": f"Payment for order {order.name}",
                            "currency": "KWD",
                            "amount": round(order.amount_total, 3),
                        },
                        "products": [{
                            "name": f"Order {order.name}",
                            "description": f"Payment for {order.name}",
                            "price": round(order.amount_total, 3),
                            "quantity": 1
                        }],
                        "returnUrl": f"{base_url}/payment/upayments/return",
                        "cancelUrl": f"{base_url}/payment/upayments/cancel",
                        "notificationUrl": f"{base_url}/payment/upayments/webhook",
                        "customerExtraData": str(order.id),
                        "language": "ar",
                    }
                    headers = {
                        "Authorization": f"Bearer {upay_key}",
                        "Content-Type": "application/json",
                    }
                    resp = req_lib.post(
                        "https://api.upayments.com/api/v1/charge",
                        json=payload, headers=headers, timeout=15
                    )
                    data = resp.json()
                    _logger.info("UPayments API response: %s", data)
                    link = (data.get("data") or {}).get("link") or (data.get("data") or {}).get("paymentLink")
                    if link:
                        return {
                            'success': True,
                            'link': link,
                            'amount': order.amount_total,
                            'currency': 'KWD',
                            'order_name': order.name,
                            'partner_name': order.partner_id.name,
                            'partner_phone': order.partner_id.mobile or order.partner_id.phone or '',
                        }
                    _logger.warning("UPayments no link in response: %s", data)
                except Exception as upay_err:
                    _logger.warning("UPayments API error: %s", upay_err)

            # Fallback: Odoo payment link
            from odoo.addons.payment import utils as payment_utils
            access_token = payment_utils.generate_access_token(
                order.partner_id.id,
                order.amount_total,
                order.currency_id.id,
            )
            payment_link = (
                f"{base_url}/payment/pay"
                f"?amount={order.amount_total}"
                f"&currency_id={order.currency_id.id}"
                f"&partner_id={order.partner_id.id}"
                f"&sale_order_id={order.id}"
                f"&access_token={access_token}"
            )
            order.write({
                'pay_link_status': 'sent',
                'pay_link_url': payment_link,
                'pay_link_sent_by': request.env.user.id,
                'pay_link_sent_date': fields.Datetime.now(),
                'pay_link_provider': 'Odoo',
            })
            order.message_post(body=f'💳 Payment link sent via Odoo: {payment_link}')
            return {
                'success': True,
                'link': payment_link,
                'amount': order.amount_total,
                'currency': order.currency_id.name,
                'order_name': order.name,
                'partner_name': order.partner_id.name,
                'partner_phone': order.partner_id.mobile or order.partner_id.phone or '',
            }
        except Exception as e:
            _logger.error("Payment link generation error: %s", e)
            return {'success': False, 'error': str(e)}

    
    # ─── Return Signature Image ───────────────────────────────────────────
    @http.route('/delivery-portal/return-signature/<int:order_id>', type='http', auth='user', website=True)
    def return_signature(self, order_id, **kwargs):
        uid = request.env.user.id
        if not _is_manager(uid):
            return request.not_found()
        company = _get_carrier_company(uid)
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or not order.return_signature:
            return request.not_found()
        import base64
        img_data = base64.b64decode(order.return_signature)
        return request.make_response(img_data, [
            ('Content-Type', 'image/png'),
            ('Content-Disposition', f'inline; filename=signature_{order_id}.png'),
        ])

    # ─── Backend Dashboard Data ───────────────────────────────────────────

    @http.route('/delivery-portal/payment-webhook', type='json', auth='public', csrf=False, website=True)
    def payment_webhook(self, **kwargs):
        """Webhook: called when customer pays via payment link."""
        import json
        try:
            data = request.get_json_data() or {}
            _logger.info("Payment webhook received: %s", data)

            # Extract order reference and payment ref
            order_ref = (data.get('order') or {}).get('id') or data.get('customerExtraData') or ''
            pay_ref   = data.get('paymentId') or data.get('referenceId') or data.get('id') or ''
            amount    = float((data.get('order') or {}).get('amount') or data.get('amount') or 0)
            status    = (data.get('status') or '').lower()

            if not order_ref:
                return {'success': False, 'error': 'No order ref'}

            # Find the sale order
            order = request.env['sale.order'].sudo().search(
                ['|', ('name', '=', order_ref), ('id', '=', order_ref)], limit=1
            )
            if not order:
                _logger.warning("Webhook: order not found: %s", order_ref)
                return {'success': False, 'error': 'Order not found'}

            if status in ('success', 'paid', 'captured', 'completed'):
                order.write({
                    'pay_link_status':       'paid',
                    'pay_link_ref':          pay_ref,
                    'pay_link_amount':       amount or order.amount_total,
                    'pay_link_date':         fields.Datetime.now(),
                    'payment_method_type':   'online',
                    'cash_collection_status': 'remitted',
                })
                order.message_post(
                    body=f'✅ Payment received via Pay Link | Ref: {pay_ref} | Amount: KD {amount:.3f}'
                )
                _logger.info("Webhook: order %s marked as paid", order.name)
            else:
                order.write({'pay_link_status': 'failed'})
                order.message_post(body=f'❌ Payment failed via Pay Link | Status: {status}')

            return {'success': True}
        except Exception as e:
            _logger.error("Payment webhook error: %s", e)
            return {'success': False, 'error': str(e)}

    @http.route('/delivery-portal/dashboard-data', type='json', csrf=False, auth='user')
    def dashboard_data(self, period='30', carrier_id=0, **kwargs):
        """Return JSON data for backend dashboard."""
        from datetime import timedelta, date
        import json

        env = request.env
        days = int(period)
        date_from = fields.Datetime.now() - timedelta(days=days)

        domain_base = [('delivery_carrier_company_id', '!=', False)]
        if carrier_id:
            domain_base.append(('delivery_carrier_company_id', '=', int(carrier_id)))

        orders = env['sale.order'].sudo().search(domain_base)
        recent = orders.filtered(lambda o: o.date_order and o.date_order >= date_from)

        # KPIs
        total = len(recent)
        delivered = recent.filtered(lambda o: o.delivery_status == 'delivered')
        failed    = recent.filtered(lambda o: o.delivery_status in ('failed', 'failed_returned'))
        in_transit = orders.filtered(lambda o: o.delivery_status == 'out_for_delivery')
        assigned  = orders.filtered(lambda o: o.delivery_status == 'assigned')

        cash_orders = recent.filtered(lambda o: o.payment_method_type == 'cash')
        cash_pending = sum(cash_orders.filtered(
            lambda o: o.cash_collection_status in ('pending', 'collected')
        ).mapped('amount_total'))
        cash_remitted = sum(cash_orders.filtered(
            lambda o: o.cash_collection_status == 'remitted'
        ).mapped('amount_total'))

        # Returns
        failed_all = orders.filtered(lambda o: o.delivery_status in ('failed', 'failed_returned'))
        returns_awaiting  = len(failed_all.filtered(lambda o: o.return_status == 'awaiting_return'))
        returns_scheduled = len(failed_all.filtered(lambda o: o.return_status in ('return_scheduled', 'return_in_transit')))
        returns_received  = len(failed_all.filtered(lambda o: o.return_status == 'returned_received'))

        # Carrier breakdown
        carriers_data = []
        carrier_companies = env['delivery.carrier.company'].sudo().search([('active', '=', True)])
        for c in carrier_companies:
            c_orders = recent.filtered(lambda o: o.delivery_carrier_company_id.id == c.id)
            c_del = len(c_orders.filtered(lambda o: o.delivery_status == 'delivered'))
            c_total = len(c_orders)
            c_cash_pending = sum(c_orders.filtered(
                lambda o: o.payment_method_type == 'cash'
                and o.cash_collection_status in ('pending', 'collected')
            ).mapped('amount_total'))
            drivers = env['delivery.driver'].sudo().search([('carrier_company_id', '=', c.id)])
            carriers_data.append({
                'id': c.id,
                'name': c.name,
                'total': c_total,
                'delivered': c_del,
                'failed': len(c_orders.filtered(lambda o: o.delivery_status in ('failed', 'failed_returned'))),
                'success_rate': round(c_del / c_total * 100, 1) if c_total else 0,
                'cash_pending': round(c_cash_pending, 3),
                'drivers_count': len(drivers),
            })

        # Driver leaderboard
        drivers_data = []
        all_drivers = env['delivery.driver'].sudo().search([('active', '=', True)])
        for d in all_drivers:
            d_lines = env['delivery.trip.line'].sudo().search([('driver_id', '=', d.id)])
            d_recent = d_lines.filtered(
                lambda l: l.sale_order_id.date_order and l.sale_order_id.date_order >= date_from
            )
            d_del = len(d_recent.filtered(lambda l: l.delivery_status == 'delivered'))
            d_total = len(d_recent)
            d_cash = sum(
                l.sale_order_id.amount_total
                for l in d_recent.filtered(
                    lambda l: l.delivery_status == 'delivered' and l.payment_method_type == 'cash'
                )
                if l.sale_order_id
            )
            if d_total > 0:
                drivers_data.append({
                    'id': d.id,
                    'name': d.name,
                    'carrier': d.carrier_company_id.name if d.carrier_company_id else '',
                    'total': d_total,
                    'delivered': d_del,
                    'success_rate': round(d_del / d_total * 100, 1),
                    'cash_collected': round(d_cash, 3),
                })
        drivers_data.sort(key=lambda x: x['success_rate'], reverse=True)

        # Daily trend (last 14 days)
        daily_trend = []
        for i in range(13, -1, -1):
            day = date.today() - timedelta(days=i)
            day_start = fields.Datetime.to_datetime(str(day))
            day_end   = fields.Datetime.to_datetime(str(day) + ' 23:59:59')
            day_orders = recent.filtered(
                lambda o: o.date_order and day_start <= o.date_order <= day_end
            )
            daily_trend.append({
                'date': str(day),
                'total': len(day_orders),
                'delivered': len(day_orders.filtered(lambda o: o.delivery_status == 'delivered')),
                'failed': len(day_orders.filtered(lambda o: o.delivery_status in ('failed', 'failed_returned'))),
            })

        # Recent orders (last 20)
        recent_orders = []
        for o in orders.sorted(key=lambda x: x.date_order or fields.Datetime.now(), reverse=True)[:20]:
            recent_orders.append({
                'id': o.id,
                'name': o.name,
                'partner': o.partner_id.name,
                'carrier': o.delivery_carrier_company_id.name if o.delivery_carrier_company_id else '',
                'driver': o.delivery_driver_id.name if o.delivery_driver_id else '',
                'amount': round(o.amount_total, 3),
                'payment': o.payment_method_type,
                'status': o.delivery_status,
                'cash_status': o.cash_collection_status,
                'date': str(o.date_order)[:16] if o.date_order else '',
            })

        # Pending remittances count
        pending_rem = env['delivery.cash.remittance'].sudo().search_count([('state', '=', 'pending')])

        # Financial
        total_delivered_amount = sum(delivered.mapped('amount_total'))
        online_amount = sum(delivered.filtered(
            lambda o: o.payment_method_type == 'online'
        ).mapped('amount_total'))
        cash_amount = sum(delivered.filtered(
            lambda o: o.payment_method_type == 'cash'
        ).mapped('amount_total'))
        avg_order = round(total_delivered_amount / len(delivered), 3) if delivered else 0

        # Alerts
        alerts = []
        old_failed = failed_all.filtered(lambda o: o.return_status == 'awaiting_return')
        if old_failed:
            alerts.append({
                'type': 'danger',
                'msg': f'{len(old_failed)} طلب فاشل لم يُستلم بعد — يحتاج إجراء',
                'msg_en': f'{len(old_failed)} failed orders awaiting return',
            })
        if pending_rem > 0:
            alerts.append({
                'type': 'danger',
                'msg': f'{pending_rem} طلب تسوية معلق بقيمة KD {round(cash_pending, 3)}',
                'msg_en': f'{pending_rem} pending remittance requests',
            })
        old_assigned = assigned.filtered(
            lambda o: o.date_order and o.date_order <= fields.Datetime.now() - timedelta(hours=24)
        )
        if old_assigned:
            alerts.append({
                'type': 'warning',
                'msg': f'{len(old_assigned)} طلب مخصص أكثر من 24 ساعة بدون توصيل',
                'msg_en': f'{len(old_assigned)} orders assigned >24h without delivery',
            })

        success_rate = round(len(delivered) / total * 100, 1) if total else 0

        return {
            'kpi': {
                'total': total,
                'delivered': len(delivered),
                'failed': len(failed),
                'in_transit': len(in_transit),
                'assigned': len(assigned),
                'cash_pending': round(cash_pending, 3),
                'cash_remitted': round(cash_remitted, 3),
                'returns_awaiting': returns_awaiting,
                'returns_scheduled': returns_scheduled,
                'returns_received': returns_received,
                'success_rate': success_rate,
                'pending_remittances': pending_rem,
                'total_delivered_amount': round(total_delivered_amount, 3),
                'online_amount': round(online_amount, 3),
                'cash_amount': round(cash_amount, 3),
                'avg_order': avg_order,
            },
            'carriers': carriers_data,
            'drivers': drivers_data[:5],
            'daily_trend': daily_trend,
            'recent_orders': recent_orders,
            'alerts': alerts,
        }
