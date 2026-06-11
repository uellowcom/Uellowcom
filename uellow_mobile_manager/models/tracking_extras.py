# -*- coding: utf-8 -*-
"""Live order tracking extras — warehouse + carrier center + driver GPS.

Extends three models so the customer app can render a multi-stage map:
- mobile.app.setting → Uellow warehouse name + lat/lng (sourcing center).
- delivery.carrier.company → physical sorting-center lat/lng + address.
- delivery.driver → current_lat/lng + last_seen (heartbeat from driver app).
- res.partner → fcm_token + push prefs (so backend can push to a customer).
- mobile.session → fcm_token (mirror for unauth'd device).
"""
import math
from odoo import models, fields, api


class MobileAppSettingTracking(models.Model):
    _inherit = 'mobile.app.setting'

    warehouse_name_en = fields.Char(string='Uellow Warehouse Name (EN)',
        default='Uellow Warehouse')
    warehouse_name_ar = fields.Char(string='Uellow Warehouse Name (AR)',
        default='مخزن يلو')
    warehouse_lat = fields.Float(string='Warehouse Latitude', digits=(10, 7),
        default=29.3375, help='Uellow sourcing center latitude (Kuwait City default).')
    warehouse_lng = fields.Float(string='Warehouse Longitude', digits=(10, 7),
        default=47.9750, help='Uellow sourcing center longitude.')
    warehouse_address = fields.Char(string='Warehouse Address',
        default='Kuwait City, Kuwait')

    # ── Deep links + smart banner ─────────────────────────────────────
    android_package = fields.Char(string='Android Package Name',
        default='com.uellow.uellow')
    android_fingerprint = fields.Char(string='Android Signing SHA-256',
        help='Production signing-key fingerprint, used by /.well-known/assetlinks.json '
             'to verify App Links. Paste the SHA256 line from `keytool -list -v -keystore`.')
    ios_app_id = fields.Char(string='iOS App ID (TEAMID.bundleID)',
        default='XXXXXXXXXX.com.uellow.app')

    # ── Tracking + live activity tunings ──────────────────────────────
    proximity_alert_km = fields.Float(string='Proximity Alert Threshold (km)',
        default=1.0, digits=(4, 2),
        help='When the driver is within this distance from the customer, '
             'a "be ready" push is sent. Set 0 to disable.')
    driver_heartbeat_seconds = fields.Integer(string='Driver Heartbeat Interval (sec)',
        default=20, help='How often the driver app pings its GPS to the backend.')
    live_activity_enabled = fields.Boolean(string='Enable iOS Live Activities',
        default=True)
    ongoing_notification_enabled = fields.Boolean(string='Enable Android Ongoing Banner',
        default=True)

    # ── Checkout policy ───────────────────────────────────────────────
    require_phone_on_address = fields.Boolean(string='Require phone on address',
        default=True)
    require_address_photo = fields.Boolean(string='Require landmark photo on address',
        default=False, help='Optional unless turned on — useful for hard-to-find streets.')
    free_shipping_min_kd = fields.Float(string='Free Shipping Minimum (KD)',
        default=10.000, digits=(10, 3))
    cash_on_delivery_fee_kd = fields.Float(string='COD Fee (KD)',
        default=0.500, digits=(10, 3))

    # ── App store URLs (re-stated for clarity) ────────────────────────
    appgallery_url = fields.Char(string='Huawei AppGallery URL')

    # ── Misc UX flags ─────────────────────────────────────────────────
    enable_smart_address_picker = fields.Boolean(
        string='Enable map-based address picker',
        default=True)
    enable_address_photo_upload = fields.Boolean(
        string='Allow customer to upload landmark photo with address',
        default=True)
    enable_review_dialog = fields.Boolean(
        string='Inline review dialog on order page',
        default=True)
    enable_deep_links = fields.Boolean(
        string='Web → App deep links',
        default=True)
    enable_app_banner = fields.Boolean(
        string='Mobile web smart banner',
        default=True)


class DeliveryDriverLocation(models.Model):
    _inherit = 'delivery.driver'

    current_lat = fields.Float(string='Current Latitude', digits=(10, 7))
    current_lng = fields.Float(string='Current Longitude', digits=(10, 7))
    location_updated_at = fields.Datetime(string='Last Location Update')
    is_broadcasting = fields.Boolean(string='Broadcasting Location',
        help='True while the driver is on an active delivery and sending heartbeats.')


class ResPartnerPush(models.Model):
    _inherit = 'res.partner'

    fcm_token = fields.Char(string='FCM Push Token')
    apns_token = fields.Char(string='APNS Push Token')
    # Live app language for push localization — written by register-device
    # on every app open / login / language switch. Default 'ar': the
    # customer base is Arabic-first and an 'en' default poisoned everyone
    # into English pushes before their app re-registered.
    push_lang = fields.Char(string='Push Language', default='ar')


class MobileSessionPush(models.Model):
    _inherit = 'mobile.session'

    fcm_token = fields.Char(string='FCM Token (Device)')


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance in km between two lat/lng pairs."""
    if not (lat1 and lng1 and lat2 and lng2):
        return None
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class SaleOrderTracking(models.Model):
    _inherit = 'sale.order'

    proximity_notified = fields.Boolean(string='Proximity Push Sent', default=False,
        help='Set true once the < 1km push has been delivered, to avoid spam.')
    last_pushed_stage = fields.Char(string='Last Pushed Stage',
        help='Set after a stage-change push is sent so we do not spam on re-saves.')

    def write(self, vals):
        # v2.2.33 — driver-API writes set skip_push and fire their own
        # event-based customer notifications (push_event), so suppress the
        # legacy stage-push here to avoid double notifications.
        if self.env.context.get('skip_push'):
            return super().write(vals)
        # Detect transitions in delivery_status / state and fire pushes.
        before = {o.id: (o.state, getattr(o, 'delivery_status', ''),
                          o.delivery_driver_id.id if o.delivery_driver_id else 0)
                   for o in self}
        res = super().write(vals)
        try:
            for o in self:
                old = before.get(o.id, (None, None, None))
                changed = (o.state != old[0]
                            or getattr(o, 'delivery_status', '') != old[1]
                            or (o.delivery_driver_id.id if o.delivery_driver_id else 0) != old[2])
                if changed:
                    o._push_stage_update()
        except Exception:
            pass
        return res

    def _push_stage_update(self):
        """Emit FCM push for the customer with the latest stage."""
        self.ensure_one()
        try:
            from odoo.addons.uellow_mobile_manager.controllers.api_v2.push import send_push
        except Exception:
            return
        try:
            stage = self.tracking_stage()
        except Exception:
            return
        if not self.partner_id or self.last_pushed_stage == stage:
            return
        lang = (self.partner_id.lang or 'en')[:2]
        titles = {
            'at_warehouse': ('Order confirmed', 'تأكد طلبك'),
            'at_carrier':   ('Heading out', 'في طريقه إليك'),
            'with_courier': ('With the courier', 'طلبك مع المندوب'),
            'in_transit':   ('Driver on the way', 'السائق في الطريق'),
            'arriving':     ('Arriving soon', 'يصل قريباً'),
            'delivered':    ('Order delivered', 'تم التسليم'),
            'cancelled':    ('Order cancelled', 'تم إلغاء الطلب'),
            'returned':     ('Return received', 'تم استلام الإرجاع'),
        }
        bodies = {
            'at_warehouse': (f'Order {self.name} is being prepared at our warehouse.',
                              f'الطلب {self.name} قيد التحضير في المخزن.'),
            'at_carrier':   (f'Order {self.name} has reached the delivery hub.',
                              f'الطلب {self.name} وصل لمركز التوصيل.'),
            'with_courier': (f'Order {self.name} is now with the courier.',
                              f'الطلب {self.name} أصبح مع المندوب.'),
            'in_transit':   (f'Driver picked up {self.name} and is on the way.',
                              f'استلم السائق {self.name} وهو في الطريق إليك.'),
            'arriving':     (f'Driver is minutes away from your address.',
                              f'السائق على بُعد دقائق من عنوانك.'),
            'delivered':    (f'Order {self.name} delivered. Enjoy!',
                              f'تم تسليم {self.name}. نتمنى لك تجربة سعيدة!'),
            'cancelled':    (f'Order {self.name} was cancelled.',
                              f'تم إلغاء الطلب {self.name}.'),
            'returned':     (f'We received your return for {self.name}.',
                              f'تم استلام مرتجع الطلب {self.name}.'),
        }
        t = titles.get(stage)
        b = bodies.get(stage)
        if not t:
            return
        send_push(
            self.partner_id,
            t[1] if lang == 'ar' else t[0],
            b[1] if lang == 'ar' else b[0],
            data={
                'type': 'order_stage',
                'order_id': str(self.id),
                'stage': stage,
            },
            channel='order_update', priority='high',
        )
        try:
            self.sudo().with_context(skip_push=True).write({'last_pushed_stage': stage})
        except Exception:
            pass

    def tracking_stage(self):
        """Coarse stage for the live tracking map.

        placed       — order just placed, no carrier yet
        at_warehouse — confirmed/preparing at Uellow warehouse
        at_carrier   — assigned to carrier (sorting center), no driver out yet
        in_transit   — driver picked up, en route to customer (live broadcast)
        arriving     — driver within 1 km of customer
        delivered    — done
        cancelled / returned
        """
        self.ensure_one()
        if self.state == 'cancel':
            return 'cancelled'
        if getattr(self, 'return_status', '') == 'returned_received':
            return 'returned'
        ds = getattr(self, 'delivery_status', '')
        if ds == 'delivered':
            return 'delivered'
        if ds == 'out_for_delivery':
            drv = self.delivery_driver_id
            if drv and drv.current_lat and drv.current_lng \
                    and self.delivery_lat and self.delivery_lng:
                dist = haversine_km(drv.current_lat, drv.current_lng,
                                    self.delivery_lat, self.delivery_lng)
                if dist is not None and dist <= 1.0:
                    return 'arriving'
            return 'in_transit'
        if ds == 'accepted':
            # Driver accepted — order is WITH the courier, but he hasn't
            # pressed "Start delivery" yet, so no live pin.
            return 'with_courier'
        if ds == 'assigned':
            return 'at_carrier'
        if ds == 'arrived_sorting':
            return 'at_carrier'
        if self.state == 'sale':
            return 'at_warehouse'
        return 'placed'
