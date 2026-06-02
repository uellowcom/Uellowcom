"""Shipping + carrier tracking — /api/mobile/v2/shipping/*

Reads from delivery_carrier_portal so the same data the carrier
companies see in their portal is what the customer sees in the app.
"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, current_partner, require_auth,
    bilingual, fmt_price,
)


class MobileShippingAPI(http.Controller):

    @http.route('/api/mobile/v2/shipping/zones', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def zones(self, **kw):
        """List available delivery zones with their flat fee. Used by the
        cart/checkout to show the customer what they'd pay before they
        enter an address."""
        Rule = request.env.get('carrier.pricing.rule')
        if Rule is None:
            return ok([])
        rules = Rule.sudo().search([('active', '=', True)] if 'active' in Rule._fields else [])
        return ok([{
            'id': r.id,
            'zone': r.zone_name or '',
            'fee':  fmt_price(r.delivery_fee or 0),
            'eta_min_hours': int(getattr(r, 'eta_min_hours', 0) or 0),
            'eta_max_hours': int(getattr(r, 'eta_max_hours', 0) or 0),
        } for r in rules])

    @http.route('/api/mobile/v2/shipping/companies', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def companies(self, **kw):
        """Carrier companies the customer can pick from at checkout."""
        Carrier = request.env.get('delivery.carrier.company')
        if Carrier is None:
            return ok([])
        carriers = Carrier.sudo().search([
            ('active', '=', True)
        ] if 'active' in Carrier._fields else [])
        return ok([{
            'id':   c.id,
            'name': bilingual(c, 'name'),
            'logo': f'/web/image/delivery.carrier.company/{c.id}/logo'
                    if 'logo' in c._fields and c.logo else None,
            'phone': getattr(c, 'support_phone', '') or '',
            'rating': float(getattr(c, 'average_rating', 0) or 0),
        } for c in carriers])

    @http.route('/api/mobile/v2/shipping/track/<int:order_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def track(self, order_id, **kw):
        """Track an order. Returns the timeline of delivery events from
        delivery.trip + delivery.trip.line when present."""
        partner = current_partner()
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.partner_id != partner:
            return fail('NOT_FOUND', 'Order not found', 404)

        # Find the related delivery trip line
        TripLine = request.env.get('delivery.trip.line')
        timeline = []
        current_status = order.state
        driver = None
        eta = None
        if TripLine is not None:
            lines = TripLine.sudo().search([
                ('sale_order_id', '=', order.id),
            ], order='create_date desc')
            for line in lines:
                timeline.append({
                    'status': getattr(line, 'state', '') or '',
                    'label':  bilingual(line, 'state'),
                    'at':     line.write_date.isoformat() if line.write_date else None,
                    'note':   getattr(line, 'note', '') or '',
                })
                if line.trip_id and line.trip_id.driver_id:
                    driver = {
                        'name':  line.trip_id.driver_id.name,
                        'phone': getattr(line.trip_id.driver_id, 'phone', '') or '',
                        'vehicle': getattr(line.trip_id.driver_id, 'vehicle_plate', '') or '',
                    }
                    if hasattr(line.trip_id, 'eta'):
                        eta = line.trip_id.eta and line.trip_id.eta.isoformat() or None

        return ok({
            'order_name': order.name,
            'status': current_status,
            'driver': driver,
            'eta': eta,
            'timeline': timeline,
        })

    @http.route('/api/mobile/v2/shipping/preferences', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def get_preferences(self, **kw):
        """Customer shipping preferences (preferred carrier, time window,
        leave-at-door instructions). Stored on res.partner."""
        partner = current_partner()
        return ok({
            'preferred_carrier_id': partner.preferred_carrier_id.id
                if 'preferred_carrier_id' in partner._fields and partner.preferred_carrier_id else None,
            'preferred_window': getattr(partner, 'preferred_delivery_window', '') or '',
            'delivery_notes': getattr(partner, 'delivery_notes', '') or '',
            'contactless': bool(getattr(partner, 'contactless_delivery', False)),
        })

    @http.route('/api/mobile/v2/shipping/preferences/save', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def save_preferences(self, **kw):
        p = get_payload()
        partner = current_partner()
        vals = {}
        if 'preferred_carrier_id' in p and 'preferred_carrier_id' in partner._fields:
            try: vals['preferred_carrier_id'] = int(p['preferred_carrier_id'])
            except Exception: pass
        if 'delivery_notes' in p and 'delivery_notes' in partner._fields:
            vals['delivery_notes'] = p['delivery_notes']
        if 'contactless' in p and 'contactless_delivery' in partner._fields:
            vals['contactless_delivery'] = bool(p['contactless'])
        if 'preferred_window' in p and 'preferred_delivery_window' in partner._fields:
            vals['preferred_delivery_window'] = p['preferred_window']
        if vals:
            partner.sudo().write(vals)
        return ok({'saved': True})
