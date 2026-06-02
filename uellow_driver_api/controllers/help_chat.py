# -*- coding: utf-8 -*-
"""Driver help / ops chat — /api/driver/v1/help*"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_driver,
)


_FAQ = [
    {'key': 'unreachable',
     'q': {'en': 'What if customer is unreachable?',
           'ar': 'ماذا لو العميل غير متاح؟'},
     'a': {'en': 'Try calling 3 times with 2 min gap. If still no answer, '
                 'tap Fail → "Customer not reachable" and toggle "Return to Uellow" on. '
                 'The order will go back to the warehouse and you keep delivery fee.',
           'ar': 'اتصل 3 مرات بفارق دقيقتين بين كل محاولة. إذا لم يرد، '
                  'اضغط فشل ← "العميل غير متاح" وفعّل خيار "إرجاع لـ Uellow". '
                  'الطلب يرجع للمستودع وأنت تحتفظ برسوم التوصيل.'}},
    {'key': 'cash_settlement',
     'q': {'en': 'How does cash settlement work?',
           'ar': 'كيف تتم تسوية النقد؟'},
     'a': {'en': 'Open Cash tab → tick the COD orders you collected → '
                 'enter a reference (your own log number) → Submit. '
                 'The amount appears under "Submitted" until your carrier company approves it.',
           'ar': 'افتح تبويب النقد ← حدد طلبات COD التي حصّلتها ← '
                  'أدخل مرجعك ← أرسل. المبلغ يظهر تحت "مرسلة" حتى توافق الشركة.'}},
    {'key': 'map',
     'q': {'en': 'Map / navigation issue',
           'ar': 'مشكلة الخريطة'},
     'a': {'en': 'Use the "Open in Maps" button on any order — it launches '
                 'your phone\'s native maps app (Google Maps / Apple Maps).',
           'ar': 'استخدم زر "افتح الخريطة" في أي طلب — يفتح تطبيق الخرائط الأصلي على هاتفك.'}},
    {'key': 'emergency',
     'q': {'en': 'Emergency: accident / theft',
           'ar': 'طوارئ: حادث / سرقة'},
     'a': {'en': 'Tap the red Emergency button. Your GPS + driver ID is '
                 'sent to operations immediately, and an ops agent will call '
                 'you within 60 seconds.',
           'ar': 'اضغط زر الطوارئ الأحمر. موقعك ورقم سائقك يُرسلان للعمليات فوراً، '
                  'ويتصل بك مسؤول العمليات خلال 60 ثانية.'}},
]


class DriverHelpAPI(http.Controller):

    @http.route('/api/driver/v1/help/faq', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def faq(self, **kw):
        return ok(_FAQ)

    @http.route('/api/driver/v1/help/chat', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def chat(self, **kw):
        """Send a message to the operations team via mail.channel."""
        p = get_payload()
        body = (p.get('body') or '').strip()
        if not body:
            return fail('EMPTY', 'Empty message')
        driver = current_driver()
        partner = driver.portal_user_id.partner_id if driver.portal_user_id else None
        # Create / find an ops channel for this driver
        Channel = request.env['discuss.channel'].sudo() \
            if 'discuss.channel' in request.env else request.env['mail.channel'].sudo()
        channel = Channel.search(
            [('name', '=', f'Ops · {driver.name}')], limit=1)
        if not channel:
            channel = Channel.create({
                'name': f'Ops · {driver.name}',
                'channel_type': 'channel',
                'channel_partner_ids': [(4, partner.id)] if partner else [],
            })
        msg = channel.message_post(body=body, author_id=partner.id if partner else 1)
        return ok({'channel_id': channel.id, 'message_id': msg.id})

    @http.route('/api/driver/v1/help/emergency', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def emergency(self, **kw):
        """Driver pressed the emergency button. Log it loud + alert ops."""
        p = get_payload()
        lat = p.get('lat')
        lng = p.get('lng')
        kind = (p.get('kind') or 'unknown').strip()
        driver = current_driver()
        request.env['mail.message'].sudo().create({
            'subject': f'🚨 DRIVER EMERGENCY: {driver.name} ({kind})',
            'body':    f'Driver {driver.name} pressed Emergency. '
                       f'Kind: {kind}. GPS: {lat},{lng}. '
                       f'Phone: {driver.phone}',
            'model':   'delivery.driver',
            'res_id':  driver.id,
            'message_type': 'notification',
        })
        return ok({'alerted': True})
