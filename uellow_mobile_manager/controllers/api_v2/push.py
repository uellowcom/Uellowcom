"""Push notification helper + delivery tracking endpoint.

Two purposes:
1. send_push() — thin wrapper around FCM HTTP that the rest of the
   backend calls when an order status changes or a proximity threshold
   trips. Falls back to a no-op + log line if FCM is not configured.
2. /api/mobile/v2/orders/<id>/driver-location — driver app pushes its
   GPS heartbeat here; backend persists, computes distance, and emits
   the matching push (silent for map updates, visible for state /
   proximity changes).
"""
import json
import logging
import urllib.request

from odoo import http, fields
from odoo.http import request

from ._common import (safe_endpoint, get_payload, ok, fail, app_setting,
                      current_partner)
from .orders import _stage_label, _delivery_tracking

_logger = logging.getLogger(__name__)


def _fcm_server_key():
    s = app_setting()
    return (s and s.fcm_server_key) or ''


def send_push(partner, title, body, data=None, channel='order_update',
              priority='high'):
    """Send an FCM message to a partner's registered tokens.

    `data` is a dict that ends up in the notification's data payload so
    the app can route it (open the right order screen, update the live
    activity, etc.). When key='silent' is in `data`, no visible
    notification is shown and only data is delivered."""
    if not partner:
        return False
    tokens = set()
    if partner.fcm_token:
        tokens.add(partner.fcm_token)
    # Pick up any session tokens registered for this partner's user
    users = partner.user_ids
    if users:
        sessions = request.env['mobile.session'].sudo().search([
            ('user_id', 'in', users.ids),
            '|', ('fcm_token', '!=', False), ('push_token', '!=', False),
        ])
        for s in sessions:
            tk = s.fcm_token or s.push_token
            if tk:
                tokens.add(tk)
    if not tokens:
        _logger.info('send_push: no tokens for partner %s', partner.id)
        return False
    # Prefer FCM HTTP v1 (service-account OAuth). Google decommissioned the
    # legacy fcm.googleapis.com/fcm/send + server-key API (June 2024), so the
    # old path silently dropped every push. Route through the working v1 sender
    # (mobile.customer.notification.send_fcm) which mints an OAuth token from
    # the configured service account.
    conf = request.env['mobile.notification.setting'].sudo().search([], limit=1)
    if conf and (conf.fcm_service_account or '').strip():
        Engine = request.env['mobile.customer.notification'].sudo()
        sent = 0
        for tk in tokens:
            try:
                if Engine.send_fcm(conf, tk, title, body, data=data):
                    sent += 1
            except Exception as e:
                _logger.warning('send_push (v1) failed for one token: %s', e)
        return sent > 0
    _logger.info('send_push: no FCM service account configured — %d tokens not '
                 'pushed (%s)', len(tokens), title)
    return False


class MobileDriverLocation(http.Controller):

    @http.route('/api/mobile/v2/orders/<int:order_id>/driver-location',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    def post_driver_location(self, order_id, **kw):
        """Driver-side push of {lat, lng}. Auth is by driver bearer
        token — same scheme as the driver app's other endpoints.

        Side effects:
        - Updates delivery.driver.current_lat/lng + location_updated_at.
        - Computes distance to customer.
        - Pushes silent data to the customer (live map update).
        - When distance crosses 1km for the first time, pushes a
          visible 'arriving soon' notification.
        """
        p = get_payload()
        lat = p.get('lat')
        lng = p.get('lng')
        try:
            lat = float(lat); lng = float(lng)
        except Exception:
            return fail('BAD_INPUT', 'lat/lng required', 400)
        # Resolve driver via the driver.session bearer token.
        token = (request.httprequest.headers.get('Authorization') or '').replace('Bearer ', '').strip()
        if not token:
            return fail('NO_AUTH', 'driver token required', 401)
        import hashlib
        h = hashlib.sha256(token.encode()).hexdigest()
        session = request.env['driver.session'].sudo().search([('token_hash', '=', h)], limit=1) if 'driver.session' in request.env else None
        if not session or not session.driver_id:
            return fail('NO_AUTH', 'invalid driver token', 401)
        driver = session.driver_id
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.delivery_driver_id != driver:
            return fail('NOT_FOUND', 'order not assigned to this driver', 404)
        # Persist heartbeat
        driver.sudo().write({
            'current_lat': lat,
            'current_lng': lng,
            'is_broadcasting': True,
            'location_updated_at': fields.Datetime.now(),
        })
        # Distance + proximity push
        from odoo.addons.uellow_mobile_manager.models.tracking_extras import haversine_km
        dist = None
        if order.delivery_lat and order.delivery_lng:
            dist = haversine_km(lat, lng, order.delivery_lat, order.delivery_lng)
        # Silent data push so the app refreshes the map
        silent_payload = {
            'silent': '1',
            'type': 'driver_location',
            'order_id': str(order.id),
            'lat': str(lat),
            'lng': str(lng),
            'distance_km': str(round(dist, 3)) if dist is not None else '',
        }
        try:
            send_push(order.partner_id, '', '', data=silent_payload,
                      channel='driver_location', priority='high')
        except Exception:
            pass
        # Visible proximity push — once per order
        try:
            if dist is not None and dist <= 1.0 and not order.proximity_notified:
                order.sudo().write({'proximity_notified': True})
                lang = (order.partner_id.lang or 'en')[:2]
                if lang == 'ar':
                    title = 'طلبك يقترب!'
                    body = f'سائق {driver.name} على بُعد دقائق منك — يُرجى التجهيز.'
                else:
                    title = 'Your order is arriving!'
                    body = f'Driver {driver.name} is minutes away — please be ready.'
                send_push(order.partner_id, title, body,
                          data={'type': 'proximity', 'order_id': str(order.id)},
                          channel='order_update', priority='high')
                request.env.cr.commit()
        except Exception as e:
            _logger.warning('proximity push failed: %s', e)
        return ok({'received': True, 'distance_km': dist})

    @http.route('/api/mobile/v2/orders/<int:order_id>/driver-broadcast/stop',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    def stop_broadcast(self, order_id, **kw):
        token = (request.httprequest.headers.get('Authorization') or '').replace('Bearer ', '').strip()
        if not token:
            return fail('NO_AUTH', 'driver token required', 401)
        import hashlib
        h = hashlib.sha256(token.encode()).hexdigest()
        session = request.env['driver.session'].sudo().search([('token_hash', '=', h)], limit=1) if 'driver.session' in request.env else None
        if not session or not session.driver_id:
            return fail('NO_AUTH', 'invalid driver token', 401)
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.delivery_driver_id != session.driver_id:
            return fail('NOT_FOUND', 'order not assigned', 404)
        session.driver_id.sudo().write({'is_broadcasting': False})
        return ok({'stopped': True})

    # ── iOS Live Activity token registration (v2.2.48) ─────────────────
    @http.route('/api/mobile/v2/live-activity/register',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    def register_live_activity(self, **kw):
        """التطبيق يبدأ النشاط (ActivityKit) ويرسل توكن الدفع الخاص به هنا
        لربطه بالطلب، كي نستطيع إرسال تحديثات Live Activity عبر APNs."""
        partner = current_partner()
        if not partner:
            return fail('NO_AUTH', 'login required', 401)
        p = get_payload()
        try:
            order_id = int(p.get('order_id') or 0)
        except Exception:
            order_id = 0
        token = (p.get('activity_token') or p.get('token') or '').strip()
        if not order_id or not token:
            return fail('BAD_REQUEST', 'order_id + activity_token required')
        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists() or order.partner_id.id != partner.id:
            return fail('NOT_FOUND', 'order not found', 404)
        order.write({'live_activity_token': token,
                     'live_activity_active': True})
        request.env.cr.commit()
        return ok({'registered': True, 'order_id': order_id})

    @http.route('/api/mobile/v2/live-activity/end',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    def end_live_activity(self, **kw):
        """التطبيق ينهي النشاط محلياً ويبلغنا لإيقاف الإرسال."""
        partner = current_partner()
        if not partner:
            return fail('NO_AUTH', 'login required', 401)
        p = get_payload()
        try:
            order_id = int(p.get('order_id') or 0)
        except Exception:
            order_id = 0
        order = request.env['sale.order'].sudo().browse(order_id)
        if order.exists() and order.partner_id.id == partner.id:
            order.with_context(skip_live_activity=True).write(
                {'live_activity_active': False})
            request.env.cr.commit()
        return ok({'ended': True})
