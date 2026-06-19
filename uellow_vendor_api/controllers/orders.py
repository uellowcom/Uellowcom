# -*- coding: utf-8 -*-
"""Vendor orders — /api/vendor/v1/orders*"""
import base64
from datetime import datetime

from odoo import http, fields
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth,
    current_vendor, fmt_price, bilingual, img_url,
)


def _pdf_attachment_url(report_ref, res_id, filename):
    """Render a QWeb report to a PDF, stash it as an access-token attachment,
    and return a public download URL the app can open without a session."""
    pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(report_ref, [res_id])
    att = request.env['ir.attachment'].sudo().create({
        'name': filename,
        'type': 'binary',
        'datas': base64.b64encode(pdf),
        'mimetype': 'application/pdf',
        'res_model': 'sale.order',
        'res_id': res_id,
    })
    att.generate_access_token()
    base = request.httprequest.host_url.rstrip('/')
    return '%s/web/content/%s?access_token=%s&download=true&filename=%s' % (
        base, att.id, att.access_token, filename)


def _state_label(s):
    return {
        'draft':    {'en': 'Draft',     'ar': 'مسودة'},
        'sent':     {'en': 'Quotation', 'ar': 'عرض سعر'},
        'sale':     {'en': 'Confirmed', 'ar': 'مؤكد'},
        'done':     {'en': 'Done',      'ar': 'مكتمل'},
        'cancel':   {'en': 'Cancelled', 'ar': 'ملغي'},
    }.get(s, {'en': s, 'ar': s})


def _ser_order(o, detail=False):
    vendor = o.vendor_id
    vtype = vendor.vendor_type or 'seller'
    # FBU / consignment: stock & fulfilment owned by Uellow → minimal customer
    # privacy and NO vendor order controls.
    minimal = vtype in ('fbu', 'consignment')
    ship = o.partner_shipping_id or o.partner_id
    cust = {
        'id': o.partner_id.id,
        'name': o.partner_id.name,
        'city': ship.city or '',
        'country': ship.country_id.name if ship.country_id else '',
    }
    if not minimal:
        cust['phone'] = o.partner_id.phone or o.partner_id.mobile or ''
        cust['email'] = o.partner_id.email or ''
    out = {
        'id': o.id,
        'name': o.name,
        'state': o.state,
        'state_label': _state_label(o.state),
        'vendor_type': vtype,
        'minimal': minimal,
        'when': (o.date_order or o.create_date).isoformat()
                if (o.date_order or o.create_date) else '',
        'customer': cust,
        'amount': fmt_price(o.amount_total, o.currency_id),
        'subtotal': fmt_price(o.amount_untaxed, o.currency_id),
        'shipping': fmt_price(o.amount_delivery or 0, o.currency_id),
        'item_count': len(o.order_line.filtered(lambda l: not l.display_type)),
        'invoice_status': o.invoice_status,
        'sla_state': o.vendor_sla_state,
        'fulfill_due': o.vendor_fulfill_due.isoformat() if o.vendor_fulfill_due else '',
        'tracking': o._vendor_tracking(),
    }
    if detail:
        ready = bool(o.vendor_ready_for_pickup)
        shipped = o._vendor_is_shipped()
        # What the vendor may DO with this order, by type + capability.
        out['actions'] = {
            'full_control':      not minimal,
            'can_accept':        (not minimal) and vendor.cap('accept_orders')
                                 and o.state in ('draft', 'sent'),
            'can_reject':        (not minimal) and vendor.cap('cancel_orders')
                                 and o.state != 'cancel' and not shipped,
            'can_prepare':       (not minimal) and o.state in ('sale', 'done')
                                 and not ready and not shipped,
            'ready_for_pickup':  ready,
            'can_print_label':   (not minimal) and o.state in ('sale', 'done'),
            'can_print_invoice': (not minimal) and o.state in ('sale', 'done'),
        }
        if minimal:
            # FBU vendors see only name + city + country (already in `customer`).
            out['shipping_address'] = {
                'city': ship.city or '',
                'country': ship.country_id.name if ship.country_id else '',
            }
        else:
            out['shipping_address'] = {
                'name': ship.name, 'phone': ship.phone or ship.mobile or '',
                'street': ship.street or '', 'street2': ship.street2 or '',
                'city': ship.city or '', 'country': ship.country_id.name if ship.country_id else '',
            }
        out['items'] = []
        for l in o.order_line.filtered(lambda l: not l.display_type):
            p = l.product_id
            out['items'].append({
                'id': l.id,
                'product_id': p.product_tmpl_id.id,
                'name': bilingual(p.product_tmpl_id, 'name'),
                'qty': l.product_uom_qty,
                'price': fmt_price(l.price_unit, o.currency_id),
                'subtotal': fmt_price(l.price_subtotal, o.currency_id),
                'image_url': img_url('product.product', p.id, 'image_256',
                                     unique=p.write_date),
            })
        out['note'] = o.note or ''
    return out


class VendorOrdersAPI(http.Controller):

    @http.route('/api/vendor/v1/orders', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_orders(self, **kw):
        v = current_vendor()
        p = get_payload()
        state = (p.get('state') or '').strip()
        search = (p.get('search') or '').strip()
        try:
            page = max(1, int(p.get('page') or 1))
            per_page = min(50, max(5, int(p.get('per_page') or 20)))
        except (TypeError, ValueError):
            page, per_page = 1, 20
        domain = [('vendor_id', '=', v.id)]
        if state == 'new':       domain += [('state', '=', 'sent')]
        elif state == 'pending': domain += [('state', '=', 'draft')]
        elif state == 'active':  domain += [('state', '=', 'sale'),
                                            ('invoice_status', '!=', 'invoiced')]
        elif state == 'completed': domain += [('invoice_status', '=', 'invoiced')]
        elif state == 'cancelled': domain += [('state', '=', 'cancel')]
        if search:
            domain += ['|', ('name', 'ilike', search),
                            ('partner_id.name', 'ilike', search)]
        Order = request.env['sale.order'].sudo()
        total = Order.search_count(domain)
        rows = Order.search(domain, order='id desc',
                            limit=per_page, offset=(page - 1) * per_page)
        return ok([_ser_order(o) for o in rows], meta={
            'page': page, 'per_page': per_page, 'total': total,
            'pages': (total + per_page - 1) // per_page,
        })

    @http.route('/api/vendor/v1/warehouses', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def warehouses(self, **kw):
        """Source warehouse(s) for the vendor's quick sales — restricted to the
        vendor's OWN warehouse (the one holding their FBU sub-location), never
        the whole company's warehouse list."""
        v = current_vendor()
        Wh = request.env['stock.warehouse'].sudo()
        whs = Wh.browse()
        loc = v.fbu_location_id.location_id if v.fbu_location_id else False
        if loc:
            whs = (Wh.search([('lot_stock_id', 'parent_of', loc.id)], limit=1)
                   or Wh.search([('view_location_id', 'parent_of', loc.id)], limit=1))
        if not whs:
            # Fallback: the vendor's company default warehouse only.
            whs = Wh.search([('company_id', '=', request.env.company.id)], limit=1)
        return ok([{'id': w.id, 'name': w.name, 'code': w.code or '',
                    'location': (loc.complete_name if loc else (w.lot_stock_id.complete_name or ''))}
                   for w in whs])

    @http.route('/api/vendor/v1/quicksale', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def quick_sale(self, **kw):
        """Counter / quick sale. Captures the full customer address, a source
        warehouse and a delivery date, then files the order in DRAFT, on hold
        pending Uellow approval (it is NOT auto-confirmed). Body:
        {lines:[{product_id,qty}], customer:{name,phone,street,street2,city},
         warehouse_id?, delivery_date?, note?}."""
        v = current_vendor()
        if not v.cap('quick_sale'):
            return fail('FORBIDDEN', 'Quick sales are disabled for your account.', 403, capability='quick_sale')
        p = get_payload()
        lines = p.get('lines') or []
        if not lines:
            return fail('NO_LINES', 'lines required')
        cust = p.get('customer') or {}
        name = (cust.get('name') or p.get('customer_name') or '').strip() or 'Walk-in customer'
        phone = (cust.get('phone') or p.get('customer_phone') or '').strip()
        if not phone:
            return fail('NO_PHONE', 'Customer phone is required')
        Partner = request.env['res.partner'].sudo()
        partner = Partner.search(['|', ('phone', '=', phone), ('mobile', '=', phone)], limit=1)
        addr_vals = {
            'name': name, 'phone': phone,
            'street': (cust.get('street') or '').strip() or False,
            'street2': (cust.get('street2') or '').strip() or False,
            'city': (cust.get('city') or '').strip() or False,
        }
        if cust.get('country_id'):
            try:
                addr_vals['country_id'] = int(cust['country_id'])
            except (TypeError, ValueError):
                pass
        elif v.country_id:
            addr_vals['country_id'] = v.country_id.id
        if not partner:
            partner = Partner.create(addr_vals)
        else:
            # keep address fresh on the existing customer
            partner.write({k: val for k, val in addr_vals.items() if val})
        order_lines = []
        for ln in lines:
            try:
                pid = int(ln.get('product_id'))
                qty = float(ln.get('qty') or 1)
            except (TypeError, ValueError):
                continue
            t = request.env['product.template'].sudo().browse(pid)
            if not t.exists() or t.vendor_id.id != v.id:
                return fail('BAD_LINE', 'Product %s is not yours' % pid, 400)
            variant = t.product_variant_id
            order_lines.append((0, 0, {'product_id': variant.id, 'product_uom_qty': qty}))
        if not order_lines:
            return fail('NO_VALID_LINES', 'No valid product lines')
        vals = {
            'partner_id': partner.id,
            'vendor_id': v.id,
            'origin': 'Vendor quick sale',
            'is_quick_sale': True,
            'note': (p.get('note') or '').strip(),
        }
        if p.get('warehouse_id'):
            try:
                vals['warehouse_id'] = int(p['warehouse_id'])
            except (TypeError, ValueError):
                pass
        if p.get('delivery_date'):
            vals['commitment_date'] = p['delivery_date']
        order = request.env['sale.order'].sudo().create(vals)
        order.write({'order_line': order_lines})
        # Held in DRAFT pending Uellow approval — do NOT auto-confirm.
        order.message_post(body='Vendor quick sale submitted — awaiting Uellow approval')
        request.env.cr.commit()
        return ok({'id': order.id, 'name': order.name, 'state': order.state,
                   'pending_approval': True,
                   'amount': fmt_price(order.amount_total, order.currency_id)})

    @http.route('/api/vendor/v1/quicksale/list', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def quick_sale_list(self, **kw):
        """History log of the vendor's quick sales."""
        v = current_vendor()
        rows = request.env['sale.order'].sudo().search(
            [('vendor_id', '=', v.id), ('is_quick_sale', '=', True)],
            order='id desc', limit=100)
        out = []
        for o in rows:
            approved = o.state in ('sale', 'done')
            out.append({
                'id': o.id, 'name': o.name, 'state': o.state,
                'state_label': _state_label(o.state),
                'approved': approved,
                'pending': o.state in ('draft', 'sent'),
                'customer': o.partner_id.name,
                'city': (o.partner_shipping_id or o.partner_id).city or '',
                'amount': fmt_price(o.amount_total, o.currency_id),
                'delivery_date': o.commitment_date.isoformat() if o.commitment_date else '',
                'when': (o.date_order or o.create_date).isoformat()
                        if (o.date_order or o.create_date) else '',
            })
        return ok(out)

    @http.route('/api/vendor/v1/orders/hub', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def order_hub(self, **kw):
        """Fulfillment workspace: orders grouped into actionable buckets with
        SLA aging. to_confirm → to_ship → shipped → completed."""
        v = current_vendor()
        Order = request.env['sale.order'].sudo()
        base = [('vendor_id', '=', v.id)]
        to_confirm = Order.search(base + [('state', 'in', ('draft', 'sent'))],
                                  order='date_order asc', limit=100)
        active = Order.search(base + [('state', '=', 'sale'),
                                      ('invoice_status', '!=', 'invoiced')],
                              order='date_order asc', limit=200)
        to_ship = active.filtered(lambda o: not o._vendor_is_shipped())
        shipped = active.filtered(lambda o: o._vendor_is_shipped())
        completed = Order.search(base + [('invoice_status', '=', 'invoiced')],
                                 order='date_order desc', limit=30)
        overdue = len((to_confirm + to_ship).filtered(
            lambda o: o.vendor_sla_state == 'overdue'))
        due_soon = len((to_confirm + to_ship).filtered(
            lambda o: o.vendor_sla_state == 'due_soon'))
        return ok({
            'buckets': {
                'to_confirm': [_ser_order(o) for o in to_confirm],
                'to_ship':    [_ser_order(o) for o in to_ship],
                'shipped':    [_ser_order(o) for o in shipped],
                'completed':  [_ser_order(o) for o in completed],
            },
            'counts': {
                'to_confirm': len(to_confirm), 'to_ship': len(to_ship),
                'shipped': len(shipped), 'completed': len(completed),
            },
            'sla': {'overdue': overdue, 'due_soon': due_soon},
        })

    @http.route('/api/vendor/v1/orders/bulk', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def bulk_orders(self, **kw):
        """Bulk confirm or ship. Body: {ids:[...], action:'confirm'|'ship'}."""
        v = current_vendor()
        if not v.cap('manage_orders'):
            return fail('FORBIDDEN', 'Managing orders is disabled for your account.', 403, capability='manage_orders')
        p = get_payload()
        action = (p.get('action') or '').strip()
        ids = p.get('ids') or []
        if action not in ('confirm', 'ship') or not ids:
            return fail('BAD_REQUEST', 'action (confirm|ship) and ids required')
        try:
            ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            return fail('BAD_IDS', 'ids must be integers')
        orders = request.env['sale.order'].sudo().browse(ids).filtered(
            lambda o: o.exists() and o.vendor_id.id == v.id)
        done, failed = 0, 0
        for o in orders:
            try:
                if action == 'confirm' and o.state in ('draft', 'sent'):
                    o.action_confirm()
                    done += 1
                elif action == 'ship':
                    for pick in o.picking_ids.filtered(lambda pk: pk.state not in ('done', 'cancel')):
                        pick.action_assign()
                        for ml in pick.move_ids:
                            ml.quantity = ml.product_uom_qty
                        pick.button_validate()
                    o.message_post(body='Vendor marked order as shipped (bulk)')
                    done += 1
            except Exception as e:
                failed += 1
                o.message_post(body='Bulk %s failed: %s' % (action, e))
        return ok({'action': action, 'done': done, 'failed': failed})

    @http.route('/api/vendor/v1/orders/<int:order_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def order_detail(self, order_id, **kw):
        v = current_vendor()
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        return ok({'order': _ser_order(o, detail=True)})

    @http.route('/api/vendor/v1/orders/<int:order_id>/confirm', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def confirm(self, order_id, **kw):
        v = current_vendor()
        if not v.cap('accept_orders'):
            return fail('FORBIDDEN', 'Accepting orders is disabled for your account.', 403, capability='accept_orders')
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        if o.state in ('draft', 'sent'):
            o.action_confirm()
        return ok({'state': o.state})

    @http.route('/api/vendor/v1/orders/<int:order_id>/prepare', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def prepare(self, order_id, **kw):
        """Seller marks the order packed & ready for Uellow to collect. Assigns
        pickings (reserve stock) and flags ready_for_pickup."""
        v = current_vendor()
        if not v.cap('manage_orders'):
            return fail('FORBIDDEN', 'Managing orders is disabled for your account.', 403, capability='manage_orders')
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        if o.vendor_id.vendor_type in ('fbu', 'consignment'):
            return fail('NOT_ALLOWED', 'Uellow fulfils this order.', 403)
        for pick in o.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
            try:
                pick.action_assign()
            except Exception:
                pass
        o.write({'vendor_ready_for_pickup': True})
        o.message_post(body='Vendor marked order ready for Uellow pickup')
        request.env.cr.commit()
        return ok({'ready_for_pickup': True, 'tracking': o._vendor_tracking()})

    @http.route('/api/vendor/v1/orders/<int:order_id>/label', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def label(self, order_id, **kw):
        """Packing / delivery label PDF (download URL)."""
        v = current_vendor()
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        picks = o.picking_ids.filtered(lambda p: p.state != 'cancel')
        try:
            if picks:
                url = _pdf_attachment_url('stock.report_deliveryslip', picks[0].id,
                                          'label-%s.pdf' % o.name)
            else:
                url = _pdf_attachment_url('sale.report_saleorder', o.id,
                                          'order-%s.pdf' % o.name)
        except Exception as e:
            return fail('REPORT_ERROR', str(e), 500)
        return ok({'url': url})

    @http.route('/api/vendor/v1/orders/<int:order_id>/invoice', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def invoice(self, order_id, **kw):
        """Invoice PDF if invoiced, else the order confirmation PDF."""
        v = current_vendor()
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        try:
            inv = o.invoice_ids.filtered(lambda i: i.state == 'posted')[:1]
            if inv:
                url = _pdf_attachment_url('account.report_invoice', inv.id,
                                          'invoice-%s.pdf' % o.name)
            else:
                url = _pdf_attachment_url('sale.report_saleorder', o.id,
                                          'order-%s.pdf' % o.name)
        except Exception as e:
            return fail('REPORT_ERROR', str(e), 500)
        return ok({'url': url})

    @http.route('/api/vendor/v1/orders/<int:order_id>/cancel', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def cancel(self, order_id, **kw):
        v = current_vendor()
        if not v.cap('cancel_orders'):
            return fail('FORBIDDEN', 'Cancelling orders is disabled for your account.', 403, capability='cancel_orders')
        p = get_payload()
        reason = (p.get('reason') or 'Vendor cancelled').strip()
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        if o.state != 'cancel':
            try:
                o._action_cancel() if hasattr(o, '_action_cancel') else o.action_cancel()
            except Exception:
                o.write({'state': 'cancel'})
            o.message_post(body=f'Vendor cancelled: {reason}')
        return ok({'state': 'cancel'})

    @http.route('/api/vendor/v1/orders/<int:order_id>/ship', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def ship(self, order_id, **kw):
        """Trigger picking validation — confirms vendor packed + shipped."""
        v = current_vendor()
        if not v.cap('manage_orders'):
            return fail('FORBIDDEN', 'Managing orders is disabled for your account.', 403, capability='manage_orders')
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        for pick in o.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
            try:
                pick.action_assign()
                for ml in pick.move_ids:
                    ml.quantity = ml.product_uom_qty
                pick.button_validate()
            except Exception as e:
                o.message_post(body=f'Ship failed: {e}')
        o.message_post(body='Vendor marked order as shipped')
        return ok({'shipped': True})
