"""Beena AI chat passthrough — /api/mobile/v2/beena/*

Proxies to /ai/chat (the existing Beena controller) so the app gets
the same product knowledge / loyalty integration that the web chat has,
without duplicating prompt engineering.
"""
import json
from odoo import http
from odoo.http import request

from ._common import safe_endpoint, get_payload, ok, fail, current_partner


class MobileBeenaAPI(http.Controller):

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

        try:
            from odoo.addons.uellow_ai_engine.controllers.ai_controller import UellowAIController
            ctrl = UellowAIController()
            ai_response = ctrl.chat(**p)
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
            # Strip markdown emphasis markers (** __ ` *) — these read as
            # raw "**" on the app since we render plain Text widgets.
            txt = re.sub(r'\*\*(.+?)\*\*', r'\1', raw)
            txt = re.sub(r'__(.+?)__',     r'\1', txt)
            txt = re.sub(r'`([^`]+?)`',    r'\1', txt)
            # <br> + closing block tags → newline
            txt = re.sub(r'<\s*br\s*/?\s*>', '\n', txt)
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
