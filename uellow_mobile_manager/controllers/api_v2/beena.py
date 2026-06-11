"""Beena AI chat passthrough — /api/mobile/v2/beena/*

Proxies to /ai/chat (the existing Beena controller) so the app gets
the same product knowledge / loyalty integration that the web chat has,
without duplicating prompt engineering.
"""
import json
from odoo import http
from odoo.http import request

from ._common import safe_endpoint, get_payload, ok, fail, current_partner, get_lang


class MobileBeenaAPI(http.Controller):

    @http.route('/api/mobile/v2/beena/nudges', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def nudges(self, **kw):
        """Proactive Beena nudges for the logged-in customer — abandoned cart,
        an order on the way, redeemable loyalty points. Drives the teaser strip
        + unread badge on the Beena tab. Each nudge has a STABLE id so the app
        can track which the customer has already seen."""
        partner = current_partner()
        if not partner:
            return ok({'nudges': [], 'count': 0})
        try:
            request.update_context(lang=get_lang())
        except Exception:
            pass
        ar = (get_lang() or '').startswith('ar')
        SO = request.env['sale.order'].sudo()
        out = []

        # 1) Order on the way — highest priority
        try:
            on_way = SO.search([
                ('partner_id', '=', partner.id),
                ('delivery_status', '=', 'out_for_delivery'),
            ], order='write_date desc', limit=1)
            if on_way:
                out.append({
                    'id': 'track-%s' % on_way.id, 'kind': 'track', 'icon': 'truck',
                    'order_id': on_way.id,
                    'text': {'en': 'Your order %s is on the way 🚚' % on_way.name,
                             'ar': 'طلبك %s في الطريق إليك 🚚' % on_way.name},
                })
        except Exception:
            pass

        # 2) Abandoned cart
        try:
            cart = SO.search([
                ('partner_id', '=', partner.id), ('state', '=', 'draft'),
                ('website_id', '!=', False),
            ], order='write_date desc', limit=1)
            n = len(cart.order_line.filtered(
                lambda l: not l.display_type and not getattr(l, 'is_delivery', False)
                and not getattr(l, 'is_reward_line', False))) if cart else 0
            if n:
                out.append({
                    'id': 'cart-%s' % cart.id, 'kind': 'cart', 'icon': 'cart',
                    'text': {'en': '%d item%s waiting in your cart 🛒' % (n, '' if n == 1 else 's'),
                             'ar': 'عندك %d منتج بانتظارك في السلة 🛒' % n},
                })
        except Exception:
            pass

        # 3) Redeemable loyalty points
        try:
            card = request.env['loyalty.card'].sudo().search([
                ('partner_id', '=', partner.id)], order='points desc', limit=1)
            pts = int(card.points) if card else 0
            if pts >= 500:
                out.append({
                    'id': 'loyalty-%d' % (pts // 500), 'kind': 'loyalty', 'icon': 'gift',
                    'text': {'en': 'You have %d points ready to use 🎁' % pts,
                             'ar': 'عندك %d نقطة جاهزة للاستخدام 🎁' % pts},
                })
        except Exception:
            pass

        # localise text to a flat string for convenience too
        for nd in out:
            nd['label'] = nd['text']['ar'] if ar else nd['text']['en']
        return ok({'nudges': out, 'count': len(out)})

    @http.route('/api/mobile/v2/beena/config', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def config(self, **kw):
        Config = request.env.get('ai.config.settings')
        if Config is None:
            return ok({'enabled': False})
        ICP = request.env['ir.config_parameter'].sudo()
        return ok({
            'enabled':     ICP.get_param('uellow_ai.enabled', 'True') == 'True',
            'name':        ICP.get_param('uellow_ai.name', 'Beena'),
            'subtitle': {
                'en': ICP.get_param('uellow_ai.subtitle_en', 'Uellow AI Assistant'),
                'ar': ICP.get_param('uellow_ai.subtitle_ar', 'مساعدة Uellow الذكية'),
            },
            'welcome': {
                'en': ICP.get_param('uellow_ai.welcome_en', 'Hi! I\'m Beena 🐝'),
                'ar': ICP.get_param('uellow_ai.welcome_ar', 'أهلاً! أنا Beena 🐝'),
            },
            'voice_enabled':   ICP.get_param('uellow_ai.voice_enabled', 'True') == 'True',
            'avatar_url':      ICP.get_param('uellow_ai.avatar_url', ''),
        })

    @http.route('/api/mobile/v2/beena/chat', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def chat(self, **kw):
        """Pass-through to /ai/chat — we forward the body untouched and
        repackage the response in the v2 envelope. Auth context is
        attached via the partner record so loyalty / order tools work."""
        p = get_payload()
        if not p.get('message'):
            return fail('MISSING_MESSAGE', 'message required')

        partner = current_partner()
        if partner:
            p.setdefault('partner_id', partner.id)
            # The AI controller resolves the customer from request.env.user
            # (loyalty / orders / fit / try-on tools). The mobile API auths by
            # bearer token, so request.env.user is the PUBLIC user → personalized
            # tools would treat the user as a guest. Switch the request env to
            # the partner's user so those tools work. Userless partners stay
            # public (limited personalization).
            _u = partner.user_ids[:1]
            if _u:
                try:
                    request.update_env(user=_u.id)
                except Exception:
                    pass
        # v2.1.79 — apply the app's language (X-Lang) to the request context so
        # product names / categories come back in the customer's language
        # (was defaulting to English). Set AFTER update_env so it isn't reset.
        try:
            request.update_context(lang=get_lang())
        except Exception:
            pass

        try:
            from odoo.addons.uellow_ai_engine.controllers.ai_controller import UellowAIController
            ctrl = UellowAIController()
            ai_response = ctrl.chat(**p)
            # ctrl.chat() returns the raw dict {reply,state,session_id,extra}
            # when called directly (it's a type='json' route). Older code called
            # .get_data() which failed → str(dict) → the ast-unwrap below stripped
            # everything except `reply`, DROPPING `extra` (all the rich cards).
            if isinstance(ai_response, dict):
                body = dict(ai_response)
            else:
                try:
                    body = json.loads(ai_response.get_data(as_text=True))
                except Exception:
                    body = {'reply': str(ai_response)}

            # Strip HTML from the reply — the web chat embeds <p>/<br>
            # tags but the Flutter app renders raw Text. Convert to
            # plain text + preserve line breaks.
            import re, ast
            raw = (body.get('reply') or body.get('text') or '').strip()
            # /ai/chat sometimes double-wraps: the outer JSON body has a
            # `reply` string whose VALUE is a python-repr dict like
            # "{'reply': '…'}". Try to unwrap once.
            if raw.startswith("{'reply'") or raw.startswith('{"reply"'):
                try:
                    inner = ast.literal_eval(raw)
                    if isinstance(inner, dict) and isinstance(inner.get('reply'), str):
                        raw = inner['reply']
                except Exception:
                    pass
            # v2.1.81 — KEEP markdown (** bold, - bullets, ## headings): the
            # app now renders it richly. Only normalise HTML → text/newlines.
            txt = re.sub(r'<\s*br\s*/?\s*>', '\n', raw)
            txt = re.sub(r'</\s*(p|div|li|h\d)\s*>', '\n', txt)
            # Strip remaining tags
            txt = re.sub(r'<[^>]+>', '', txt)
            # Decode common HTML entities
            txt = (txt.replace('&nbsp;', ' ').replace('&amp;', '&')
                       .replace('&lt;', '<').replace('&gt;', '>')
                       .replace('&quot;', '"').replace('&#39;', "'"))
            # Collapse 3+ newlines into 2
            txt = re.sub(r'\n{3,}', '\n\n', txt).strip()
            body['reply'] = txt
            body['text'] = txt
            return ok(body)
        except Exception as e:
            return fail('AI_FAILED', str(e), 500)
