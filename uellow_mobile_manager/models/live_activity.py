# -*- coding: utf-8 -*-
"""iOS Live Activity (ActivityKit) push pipeline — v2.2.48.

Live Activities CANNOT be delivered through FCM. They require a DIRECT
APNs HTTP/2 connection authenticated with a .p8 token (ES256 JWT), the
header ``apns-push-type: liveactivity`` and topic
``<bundle>.push-type.liveactivity``, targeting a per-activity push token
that the iOS app registers via ActivityKit.

Flow:
1. التطبيق يبدأ النشاط (ActivityKit) ويأخذ pushToken ويرسله إلى
   ``/api/mobile/v2/live-activity/register`` (انظر controllers/push.py).
2. عند تغيّر حالة الطلب/التوصيل نرسل تحديث APNs مباشر (update) وعند
   التسليم نرسل (end) لإنهاء النشاط.

كل شيء best-effort ومُسوَّر: بدون مفاتيح APNs أو بدون توكن النشاط لا
يحدث شيء، فلا يؤثر على أي تدفّق قائم.
"""
import json
import logging
import time

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class NotificationSettingAPNs(models.Model):
    _inherit = 'mobile.notification.setting'

    # ── إعداد APNs المباشر (مطلوب لـ Live Activity) ────────────────────
    apns_p8_key = fields.Text(
        string='APNs .p8 Key (PEM contents)',
        help='Paste the full contents of the AuthKey_XXXX.p8 file '
             '(the same Apple key used for push). Required for iOS Live '
             'Activities, which cannot go through FCM.')
    apns_key_id = fields.Char(string='APNs Key ID',
        help='The 10-char Key ID of the .p8 key.')
    apns_team_id = fields.Char(string='Apple Team ID',
        help='Your 10-char Apple Developer Team ID.')
    apns_bundle_id = fields.Char(string='iOS Bundle ID',
        default='com.uellow.app')
    apns_use_sandbox = fields.Boolean(string='APNs Sandbox',
        default=False,
        help='Use api.sandbox.push.apple.com (development builds). '
             'Off = production (api.push.apple.com).')


class MobileNotificationLiveActivity(models.Model):
    _inherit = 'mobile.customer.notification'

    # process-local JWT cache: APNs tokens are valid up to 60 min; refresh
    # well before that. Key = team_id|key_id so a credential change busts it.
    _apns_jwt_cache = {}

    @api.model
    def _apns_jwt(self, conf):
        """Build (or reuse) the ES256 JWT bearer token for APNs."""
        key = (conf.apns_p8_key or '').strip()
        if not key or not conf.apns_key_id or not conf.apns_team_id:
            return None
        ck = '%s|%s' % (conf.apns_team_id, conf.apns_key_id)
        hit = type(self)._apns_jwt_cache.get(ck)
        now = time.time()
        if hit and now - hit[1] < 2400:        # ~40 min (< 60 min APNs limit)
            return hit[0]
        try:
            import jwt as _jwt
            tok = _jwt.encode(
                {'iss': conf.apns_team_id, 'iat': int(now)},
                key, algorithm='ES256',
                headers={'kid': conf.apns_key_id, 'alg': 'ES256'})
            if isinstance(tok, bytes):
                tok = tok.decode()
            type(self)._apns_jwt_cache[ck] = (tok, now)
            return tok
        except Exception:
            _logger.warning('APNs JWT build failed', exc_info=True)
            return None

    @api.model
    def send_live_activity(self, token, content_state, event='update',
                           stale_in=3600):
        """Send ONE Live Activity APNs push. Returns True on 200.
        Never raises."""
        try:
            conf = self.env['mobile.notification.setting'].get_conf()
            if not conf.master_enabled or not token:
                return False
            jwt_tok = self._apns_jwt(conf)
            if not jwt_tok:
                return False
            import httpx
            host = ('https://api.sandbox.push.apple.com'
                    if conf.apns_use_sandbox
                    else 'https://api.push.apple.com')
            bundle = conf.apns_bundle_id or 'com.uellow.app'
            now = int(time.time())
            aps = {
                'timestamp': now,
                'event': event,
                'content-state': content_state or {},
            }
            if event == 'update':
                aps['stale-date'] = now + int(stale_in or 3600)
            elif event == 'end':
                aps['dismissal-date'] = now
            with httpx.Client(http2=True, timeout=8) as c:
                r = c.post(
                    '%s/3/device/%s' % (host, token),
                    headers={
                        'authorization': 'bearer %s' % jwt_tok,
                        'apns-push-type': 'liveactivity',
                        'apns-topic': '%s.push-type.liveactivity' % bundle,
                        'apns-priority': '10',
                        'apns-expiration': '0',
                    },
                    content=json.dumps({'aps': aps}))
            if r.status_code != 200:
                _logger.info('Live Activity APNs %s → %s %s',
                             event, r.status_code, r.text[:160])
            return r.status_code == 200
        except Exception:
            _logger.debug('send_live_activity failed', exc_info=True)
            return False


class SaleOrderLiveActivity(models.Model):
    _inherit = 'sale.order'

    live_activity_token = fields.Char(
        string='iOS Live Activity Push Token', copy=False)
    live_activity_active = fields.Boolean(
        string='Live Activity Active', default=False, copy=False)

    # خريطة حالة التوصيل → (نسبة التقدّم، عنوان EN، عنوان AR)
    _LA_STATUS_MAP = {
        'pending':          (0.10, 'Order confirmed',  'تم تأكيد الطلب'),
        'picked_up':        (0.35, 'Picked up',        'تم الاستلام'),
        'arrived_sorting':  (0.45, 'At sorting center', 'في مركز الفرز'),
        'assigned':         (0.55, 'Driver assigned',  'تم تعيين السائق'),
        'accepted':         (0.65, 'Driver on the way', 'السائق في الطريق'),
        'out_for_delivery': (0.80, 'Out for delivery', 'خرج للتوصيل'),
        'delivered':        (1.00, 'Delivered',         'تم التسليم'),
        'failed':           (1.00, 'Delivery failed',   'فشل التوصيل'),
        'failed_returned':  (1.00, 'Returned',          'أُعيد الطلب'),
    }

    def _la_content_state(self):
        """content-state للودجت — يجب أن تطابق مفاتيحه/أنواعه struct
        ``UellowOrderAttributes.ContentState`` في التطبيق:
        {title:String, body:String, progress:Double(0..1)}."""
        self.ensure_one()
        status = (getattr(self, 'delivery_status', '') or '').lower()
        prog, en, ar = self._LA_STATUS_MAP.get(
            status,
            (0.10 if self.state in ('sale', 'done') else 0.05,
             'Processing', 'قيد المعالجة'))
        en_lang = (self.partner_id.push_lang or 'ar').lower().startswith('en')
        drv = self.delivery_driver_id \
            if 'delivery_driver_id' in self._fields else None
        body = self.name or ''
        if drv and drv.name:
            body = '%s · %s' % (body, drv.name)
        return {
            'title': (en if en_lang else ar),
            'body': body,
            'progress': float(prog),
        }

    def push_live_activity(self, event='update'):
        """Best-effort: push the current order state to its Live Activity."""
        eng = self.env.get('mobile.customer.notification')
        if eng is None:
            return
        for o in self:
            if not o.live_activity_token or not o.live_activity_active:
                continue
            try:
                ok = eng.sudo().send_live_activity(
                    o.live_activity_token, o._la_content_state(), event=event)
                if event == 'end' or ok is False and event == 'end':
                    o.sudo().write({'live_activity_active': False})
            except Exception:
                _logger.debug('push_live_activity failed', exc_info=True)

    def write(self, vals):
        # Detect a delivery/state transition and mirror it to the Live
        # Activity. Guarded + best-effort so it never blocks an order save.
        watch = ('delivery_status' in vals) or ('state' in vals)
        before = {}
        if watch:
            before = {o.id: (getattr(o, 'delivery_status', ''), o.state)
                      for o in self}
        res = super().write(vals)
        if watch and not self.env.context.get('skip_live_activity'):
            try:
                _DONE = ('delivered', 'done', 'completed')
                for o in self:
                    if not (o.live_activity_token and o.live_activity_active):
                        continue
                    now_ds = getattr(o, 'delivery_status', '')
                    prev = before.get(o.id)
                    if prev and prev == (now_ds, o.state):
                        continue
                    ended = (str(now_ds).lower() in _DONE) \
                        or (o.state in ('done', 'cancel'))
                    o.push_live_activity('end' if ended else 'update')
            except Exception:
                _logger.debug('live activity write hook failed', exc_info=True)
        return res
