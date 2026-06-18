# -*- coding: utf-8 -*-
"""Vendor orders — /api/vendor/v1/orders*"""
from datetime import datetime

from odoo import http, fields
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth,
    current_vendor, fmt_price, bilingual, img_url,
)


def _state_label(s):
    return {
        'draft':    {'en': 'Draft',     'ar': 'مسودة'},
        'sent':     {'en': 'Quotation', 'ar': 'عرض سعر'},
        'sale':     {'en': 'Confirmed', 'ar': 'مؤكد'},
        'done':     {'en': 'Done',      'ar': 'مكتمل'},
        'cancel':   {'en': 'Cancelled', 'ar': 'ملغي'},
    }.get(s, {'en': s, 'ar': s})


def _ser_order(o, detail=False):
    out = {
        'id': o.id,
        'name': o.name,
        'state': o.state,
        'state_label': _state_label(o.state),
        'when': (o.date_order or o.create_date).isoformat()
                if (o.date_order or o.create_date) else '',
        'customer': {
            'id': o.partner_id.id,
            'name': o.partner_id.name,
            'phone': o.partner_id.phone or o.partner_id.mobile or '',
            'email': o.partner_id.email or '',
        },
        'amount': fmt_price(o.amount_total, o.currency_id),
        'subtotal': fmt_price(o.amount_untaxed, o.currency_id),
        'shipping': fmt_price(o.amount_delivery or 0, o.currency_id),
        'item_count': len(o.order_line.filtered(lambda l: not l.display_type)),
        'invoice_status': o.invoice_status,
        'sla_state': o.vendor_sla_state,
        'fulfill_due': o.vendor_fulfill_due.isoformat() if o.vendor_fulfill_due else '',
    }
    if detail:
        ship = o.partner_shipping_id or o.partner_id
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

    @http.route('/api/vendor/v1/quicksale', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def quick_sale(self, **kw):
        """Counter / quick sale: build a confirmed sale order from the vendor's
        own products. Body: {lines:[{product_id,qty}], customer_name?, customer_phone?}."""
        v = current_vendor()
        if not v.cap('quick_sale'):
            return fail('FORBIDDEN', 'Quick sales are disabled for your account.', 403, capability='quick_sale')
        p = get_payload()
        lines = p.get('lines') or []
        if not lines:
            return fail('NO_LINES', 'lines required')
        Partner = request.env['res.partner'].sudo()
        phone = (p.get('customer_phone') or '').strip()
        name = (p.get('customer_name') or '').strip() or 'Walk-in customer'
        partner = False
        if phone:
            partner = Partner.search(['|', ('phone', '=', phone), ('mobile', '=', phone)], limit=1)
        if not partner:
            partner = Partner.create({'name': name, 'phone': phone or False})
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
        order = request.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'vendor_id': v.id,
            'origin': 'Vendor quick sale',
        })
        order.write({'order_line': order_lines})
        order.action_confirm()
        return ok({'id': order.id, 'name': order.name, 'state': order.state,
                   'amount': fmt_price(order.amount_total, order.currency_id)})

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
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        if o.state in ('draft', 'sent'):
            o.action_confirm()
        return ok({'state': o.state})

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
