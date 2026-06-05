# -*- coding: utf-8 -*-
"""
Customer notification engine (v2.1.62)
=======================================
Until now the app inbox only carried admin-authored broadcasts
(mobile.notification). This adds PER-EVENT notifications generated
automatically by the modules (orders, wallet, loyalty, reviews,
affiliate…), each one toggleable from the backend:

- ``mobile.notification.setting``  — singleton with an enable switch per
  event type (Mobile App ▸ Marketing ▸ Notification Settings).
- ``mobile.customer.notification`` — one row per customer per event;
  merged into GET /api/mobile/v2/notifications.
- ``push_event()``                 — the single helper every module calls.
  Checks the admin toggle, then the customer's own preference category,
  then stores the row (and will fan out over FCM once Firebase creds
  land — token plumbing already exists on mobile.session/res.partner).
"""
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# event_code → (settings field, customer-pref category)
EVENT_MAP = {
    'order_confirmed':    ('notify_order_confirmed',    'order_update'),
    'order_shipped':      ('notify_order_shipped',      'order_update'),
    'order_delivering':   ('notify_order_delivering',   'order_update'),
    'order_delivered':    ('notify_order_delivered',    'order_update'),
    'order_failed':       ('notify_order_failed',       'order_update'),
    'order_cancelled':    ('notify_order_cancelled',    'order_update'),
    'wallet_credit':      ('notify_wallet',             'general'),
    'loyalty_points':     ('notify_loyalty',            'general'),
    'review_reply':       ('notify_review_reply',       'general'),
    'affiliate_commission': ('notify_affiliate',        'general'),
    'promotion':          ('notify_promotions',         'promotion'),
}


class MobileNotificationSetting(models.Model):
    _name = 'mobile.notification.setting'
    _description = 'Customer Notification Settings (per-event toggles)'
    _rec_name = 'display_label'

    display_label = fields.Char(default='Notification Settings',
                                readonly=True)
    master_enabled = fields.Boolean(
        string='Master switch', default=True,
        help='Turn OFF to stop ALL automatic event notifications at once.')

    # ── per-event toggles ──
    notify_order_confirmed = fields.Boolean(
        string='Order confirmed', default=True)
    notify_order_shipped = fields.Boolean(
        string='Order shipped / at sorting center', default=True)
    notify_order_delivering = fields.Boolean(
        string='Order out for delivery', default=True)
    notify_order_delivered = fields.Boolean(
        string='Order delivered', default=True)
    notify_order_failed = fields.Boolean(
        string='Delivery failed', default=True)
    notify_order_cancelled = fields.Boolean(
        string='Order cancelled', default=True)
    notify_wallet = fields.Boolean(
        string='Wallet credited', default=True)
    notify_loyalty = fields.Boolean(
        string='Loyalty points earned', default=True)
    notify_review_reply = fields.Boolean(
        string='Specialist review replied', default=True)
    notify_affiliate = fields.Boolean(
        string='Affiliate commission confirmed', default=True)
    notify_promotions = fields.Boolean(
        string='Promotions / module campaigns', default=True)

    # ── program-app pushes (v2.1.65 fleet rollout) ──
    notify_reviewer_new_request = fields.Boolean(
        string='Reviewers app: new review request', default=True)
    notify_vendor_new_order = fields.Boolean(
        string='Vendors app: new order with their products', default=True)
    notify_driver_assigned = fields.Boolean(
        string='Drivers app: order assigned to driver', default=True)
    notify_carrier_new_order = fields.Boolean(
        string='Delivery app: order assigned to carrier', default=True)
    notify_affiliate_news = fields.Boolean(
        string='Partners app: news & campaigns', default=True)

    # future push transport — engine stores rows either way
    fcm_server_key = fields.Char(
        string='FCM server key (legacy, unused)',
        help='Deprecated by Google — kept for reference only.')
    fcm_service_account = fields.Text(
        string='Firebase service account JSON',
        help='Paste the Service Account private-key JSON (Project '
             'Settings ▸ Service Accounts). Enables system-tray push '
             'over FCM HTTP v1 to all registered devices.')

    @api.model
    def get_conf(self):
        rec = self.sudo().search([], limit=1)
        if not rec:
            rec = self.sudo().create({})
        return rec


class MobileCustomerNotification(models.Model):
    _name = 'mobile.customer.notification'
    _description = 'Per-customer App Notification (auto events)'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', required=True, index=True,
                                 ondelete='cascade', string='Customer')
    event_code = fields.Char(index=True)
    category = fields.Selection([
        ('promotion', 'Promotion'), ('order_update', 'Order Update'),
        ('general', 'General'), ('system', 'System')],
        default='general')
    title = fields.Char(required=True)
    title_ar = fields.Char(string='Title (AR)')
    body = fields.Text()
    body_ar = fields.Text(string='Body (AR)')
    payload = fields.Char(
        help='JSON tap-action payload, e.g. {"type":"order","id":123}')
    is_read = fields.Boolean(default=False, index=True)
    website_id = fields.Many2one('website')

    @api.model
    def push_event(self, partner, event_code, title_en, title_ar,
                   body_en='', body_ar='', payload=None):
        """Single entry point for every module. Silently no-ops when the
        admin toggle or the customer's own preference disallows it —
        callers never need a try/except for business reasons (they still
        wrap in try/except so notifications can never break a flow)."""
        if not partner or event_code not in EVENT_MAP:
            return self.browse()
        fld, category = EVENT_MAP[event_code]
        conf = self.env['mobile.notification.setting'].get_conf()
        if not conf.master_enabled or not getattr(conf, fld, True):
            return self.browse()
        prefs = self.env['mobile.notification.preference'].sudo() \
            .for_partner(partner)
        if prefs and not prefs.allows(category):
            return self.browse()
        rec = self.sudo().create({
            'partner_id': partner.id,
            'event_code': event_code,
            'category': category,
            'title': title_en or title_ar or '',
            'title_ar': title_ar or '',
            'body': body_en or '',
            'body_ar': body_ar or '',
            'payload': json.dumps(payload or {}),
        })
        self._try_fcm(conf, partner, rec)
        return rec

    # ── FCM HTTP v1 (v2.1.64) ─────────────────────────────────────
    # OAuth access tokens minted from the service-account JSON are cached
    # process-wide for ~50 min (they live 60).
    _fcm_tok_cache = {}

    @api.model
    def _fcm_access_token(self, conf):
        import time as _t
        cache = type(self)._fcm_tok_cache
        if cache.get('exp', 0) > _t.time() + 60:
            return cache.get('tok')
        sa_raw = (conf.fcm_service_account or '').strip()
        if not sa_raw:
            return None
        try:
            import jwt as _jwt
            import requests as _rq
            sa = json.loads(sa_raw)
            now = int(_t.time())
            assertion = _jwt.encode({
                'iss': sa['client_email'], 'sub': sa['client_email'],
                'aud': sa['token_uri'], 'iat': now, 'exp': now + 3600,
                'scope':
                    'https://www.googleapis.com/auth/firebase.messaging',
            }, sa['private_key'], algorithm='RS256')
            if isinstance(assertion, bytes):
                assertion = assertion.decode()
            r = _rq.post(sa['token_uri'], data={
                'grant_type':
                    'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': assertion}, timeout=6)
            tok = r.json().get('access_token')
            if tok:
                cache['tok'] = tok
                cache['exp'] = now + 3000
                cache['project'] = sa.get('project_id', '')
            return tok
        except Exception:
            _logger.warning('FCM token mint failed', exc_info=True)
            return None

    @api.model
    def send_fcm(self, conf, token, title, body, data=None):
        """Send ONE push over FCM HTTP v1. Returns True on success."""
        access = self._fcm_access_token(conf)
        if not access or not token:
            return False
        try:
            import requests as _rq
            project = type(self)._fcm_tok_cache.get('project') or                 json.loads(conf.fcm_service_account)['project_id']
            r = _rq.post(
                'https://fcm.googleapis.com/v1/projects/%s/messages:send'
                % project,
                headers={'Authorization': 'Bearer %s' % access,
                         'Content-Type': 'application/json'},
                json={'message': {
                    'token': token,
                    'notification': {'title': title or '',
                                     'body': body or ''},
                    'data': {k: str(v) for k, v in (data or {}).items()},
                    'android': {'priority': 'HIGH'},
                }}, timeout=6)
            return r.status_code == 200
        except Exception:
            _logger.debug('FCM send failed', exc_info=True)
            return False

    @api.model
    def push_role(self, toggle_field, partners, title_en, title_ar,
                  body_en='', body_ar='', data=None):
        """Fleet-app broadcast (v2.1.65): push to PROGRAM users (vendors,
        drivers, reviewers, carriers, partners) over FCM directly. Gated
        by the master switch + the given settings toggle. Localized per
        recipient via res.partner.push_lang (AR default — program users
        are Arabic-first), EN when their app runs in English."""
        conf = self.env['mobile.notification.setting'].get_conf()
        if not conf.master_enabled or not getattr(conf, toggle_field, True):
            return 0
        sent = 0
        for partner in partners[:200]:
            try:
                token = getattr(partner, 'fcm_token', '') or ''
                if not token:
                    continue
                en = (getattr(partner, 'push_lang', '') or 'ar') \
                    .lower().startswith('en')
                if self.send_fcm(
                        conf, token,
                        (title_en or title_ar) if en else (title_ar or title_en),
                        (body_en or body_ar) if en else (body_ar or body_en),
                        data or {}):
                    sent += 1
            except Exception:
                continue
        return sent

    def _try_fcm(self, conf, partner, rec):
        """Best-effort push to the customer's device(s). Localized to
        the customer's LIVE app language: register-device mirrors the
        app's current language onto res.partner.push_lang every time the
        app starts / logs in / switches language, so we read it here.
        Arabic is the default when nothing is stored. Never raises."""
        try:
            token = getattr(partner, 'fcm_token', '') or ''
            if not token:
                return
            en = (getattr(partner, 'push_lang', '') or 'ar') \
                .lower().startswith('en')
            title = (rec.title or rec.title_ar) if en \
                else (rec.title_ar or rec.title)
            body = (rec.body or rec.body_ar or '') if en \
                else (rec.body_ar or rec.body or '')
            self.send_fcm(conf, token, title, body,
                          json.loads(rec.payload or '{}'))
        except Exception:
            _logger.debug('FCM push skipped/failed', exc_info=True)


class SaleOrderNotify(models.Model):
    """Order lifecycle → customer notifications. The delivery_status
    field is defined by delivery_carrier_portal; we only LISTEN for it in
    write() vals, so no manifest dependency is needed."""
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        for so in self:
            try:
                self.env['mobile.customer.notification'].push_event(
                    so.partner_id, 'order_confirmed',
                    'Order %s confirmed ✓' % so.name,
                    'تم تأكيد طلبك %s ✓' % so.name,
                    'We are preparing your order now.',
                    'نقوم بتجهيز طلبك الآن.',
                    {'type': 'order', 'id': so.id})
            except Exception:
                _logger.debug('order_confirmed notify failed',
                              exc_info=True)
        self._notify_vendors_new_order()
        return res

    def _notify_vendors_new_order(self):
        """v2.1.65 — each vendor whose products are in the order gets a
        push in the Vendors app."""
        Engine = self.env['mobile.customer.notification']
        for so in self:
            try:
                vendors = so.order_line.mapped(
                    'product_id.product_tmpl_id.vendor_id').filtered(
                    lambda v: v.user_id and v.user_id.partner_id)
                for v in vendors:
                    Engine.push_role(
                        'notify_vendor_new_order',
                        [v.user_id.partner_id],
                        'New order %s 🛒' % so.name,
                        'طلب جديد %s 🛒' % so.name,
                        'An order containing your products was placed.',
                        'وصل طلب جديد يحتوي منتجاتك — افتح تطبيق البائعين.',
                        {'type': 'order', 'id': str(so.id)})
            except Exception:
                _logger.debug('vendor notify failed', exc_info=True)

    _DELIVERY_EVENTS = {
        'arrived_sorting':  ('order_shipped',
                             'Order %s shipped 📦', 'تم شحن طلبك %s 📦',
                             'Your order reached our sorting center.',
                             'وصل طلبك إلى مركز الفرز.'),
        'out_for_delivery': ('order_delivering',
                             'Order %s out for delivery 🚚',
                             'طلبك %s خرج للتوصيل 🚚',
                             'The driver is on the way to you.',
                             'السائق في الطريق إليك.'),
        'delivered':        ('order_delivered',
                             'Order %s delivered ✅',
                             'تم توصيل طلبك %s ✅',
                             'Enjoy! Tell us what you think.',
                             'بالهناء! شاركنا رأيك في المنتجات.'),
        'failed':           ('order_failed',
                             'Delivery attempt failed ⚠️',
                             'تعذّر توصيل طلبك %s ⚠️',
                             'We could not deliver order %s — we will retry.',
                             'سنعيد محاولة التوصيل قريباً.'),
    }

    def write(self, vals):
        watch = vals.get('delivery_status')
        prev = {}
        if watch and watch in self._DELIVERY_EVENTS:
            prev = {so.id: getattr(so, 'delivery_status', '')
                    for so in self}
        res = super().write(vals)
        # v2.1.65 — program-app pushes on assignment
        Engine = self.env['mobile.customer.notification']
        if vals.get('delivery_driver_id'):
            try:
                drv = self.env['delivery.driver'].sudo().browse(
                    vals['delivery_driver_id'])
                pr = drv.portal_user_id.partner_id if drv.portal_user_id                     else None
                if pr:
                    for so in self:
                        Engine.push_role(
                            'notify_driver_assigned', [pr],
                            'New delivery assigned: %s 🛵' % so.name,
                            'تم إسناد طلب جديد إليك: %s 🛵' % so.name,
                            'Open the app to view the order.',
                            'افتح التطبيق لعرض تفاصيل الطلب والعنوان.',
                            {'type': 'order', 'id': str(so.id)})
            except Exception:
                _logger.debug('driver notify failed', exc_info=True)
        if vals.get('delivery_carrier_company_id'):
            try:
                comp = self.env['delivery.carrier.company'].sudo().browse(
                    vals['delivery_carrier_company_id'])
                prs = comp.portal_user_ids.mapped('partner_id')
                if prs:
                    for so in self:
                        Engine.push_role(
                            'notify_carrier_new_order', list(prs),
                            'New order for your company: %s 📦' % so.name,
                            'طلب جديد لشركتكم: %s 📦' % so.name,
                            'Receive it from the sorting center.',
                            'استلموه من مركز الفرز وأسندوه لسائق.',
                            {'type': 'order', 'id': str(so.id)})
            except Exception:
                _logger.debug('carrier notify failed', exc_info=True)
        if watch and watch in self._DELIVERY_EVENTS:
            ev, t_en, t_ar, b_en, b_ar = self._DELIVERY_EVENTS[watch]
            for so in self:
                if prev.get(so.id) == watch:
                    continue   # no transition
                try:
                    self.env['mobile.customer.notification'].push_event(
                        so.partner_id, ev,
                        t_en % so.name if '%s' in t_en else t_en,
                        t_ar % so.name if '%s' in t_ar else t_ar,
                        b_en % so.name if '%s' in b_en else b_en,
                        b_ar % so.name if '%s' in b_ar else b_ar,
                        {'type': 'order', 'id': so.id})
                except Exception:
                    _logger.debug('delivery notify failed', exc_info=True)
        return res

    def _action_cancel(self):
        res = super()._action_cancel()
        for so in self:
            try:
                self.env['mobile.customer.notification'].push_event(
                    so.partner_id, 'order_cancelled',
                    'Order %s cancelled' % so.name,
                    'تم إلغاء طلبك %s' % so.name,
                    'Any paid amount will be refunded.',
                    'سيتم رد أي مبلغ مدفوع.',
                    {'type': 'order', 'id': so.id})
            except Exception:
                _logger.debug('cancel notify failed', exc_info=True)
        return res


class LoyaltyCardNotify(models.Model):
    """Loyalty points earned → notification (only on increases)."""
    _inherit = 'loyalty.card'

    def write(self, vals):
        prev = {}
        if 'points' in vals:
            prev = {c.id: c.points for c in self}
        res = super().write(vals)
        if 'points' in vals:
            for c in self:
                gained = (c.points or 0) - (prev.get(c.id) or 0)
                if gained < 1 or not c.partner_id:
                    continue
                try:
                    self.env['mobile.customer.notification'].push_event(
                        c.partner_id, 'loyalty_points',
                        '+%d loyalty points ⭐' % int(gained),
                        '+%d نقطة ولاء ⭐' % int(gained),
                        'Your balance is now %d points.' % int(c.points),
                        'رصيدك الآن %d نقطة.' % int(c.points),
                        {'type': 'screen', 'value': 'loyalty'})
                except Exception:
                    _logger.debug('loyalty notify failed', exc_info=True)
        return res
