"""
Beena voice — public-facing HTTP endpoints.

  POST /ai/tts                  text + lang        → {audio b64, mimetype}
  POST /ai/transcribe           audio b64 + mime   → {text, lang}
  POST /ai/voice/usage          → {month_minutes, cap, cost_usd, providers}
  POST /ai/voice/realtime_token → {provider, ws_url, client_secret, ...}
  POST /ai/voice/clear_cache    admin only

All endpoints honour the master `voice_enabled` switch. Customer-facing routes
return JSON shaped like the rest of the Beena API — `{success, ...}` —
never the raw provider payload.
"""
import base64
import logging
from datetime import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BeenaVoiceController(http.Controller):

    # ──────────────────────────────────────────────────────────────────
    #  TTS
    # ──────────────────────────────────────────────────────────────────
    @http.route('/ai/tts', type='json', auth='public', methods=['POST'], csrf=False)
    def tts(self, **kw):
        text  = (kw.get('text') or '').strip()
        lang  = (kw.get('lang') or 'en').strip().lower()
        force = (kw.get('provider') or '').strip().lower() or None
        if not text:
            return {'success': False, 'error': 'empty_text'}
        partner = self._partner()
        router  = request.env['beena.voice.router'].sudo()
        return router.tts(text, lang=lang, partner=partner, force_provider=force)

    # ──────────────────────────────────────────────────────────────────
    #  STT
    # ──────────────────────────────────────────────────────────────────
    @http.route('/ai/transcribe', type='json', auth='public', methods=['POST'], csrf=False)
    def transcribe(self, **kw):
        audio = (kw.get('audio') or '').strip()
        mime  = (kw.get('mimetype') or 'audio/webm').strip()
        lang  = (kw.get('lang') or '').strip().lower() or None
        force = (kw.get('provider') or '').strip().lower() or None
        if not audio:
            return {'success': False, 'error': 'empty_audio'}
        partner = self._partner()
        router  = request.env['beena.voice.router'].sudo()
        return router.stt(audio, mimetype=mime, lang_hint=lang,
                          partner=partner, force_provider=force)

    # ──────────────────────────────────────────────────────────────────
    #  Phase B — realtime conversation handshake
    # ──────────────────────────────────────────────────────────────────
    @http.route('/ai/voice/realtime_token', type='json', auth='public',
                methods=['POST'], csrf=False)
    def realtime_token(self, **kw):
        partner = self._partner()
        router  = request.env['beena.voice.router'].sudo()
        return router.realtime_config(partner=partner)

    # ──────────────────────────────────────────────────────────────────
    #  Usage snapshot (drives the dashboard pill + browser-side caps)
    # ──────────────────────────────────────────────────────────────────
    @http.route('/ai/voice/usage', type='json', auth='public', methods=['POST'], csrf=False)
    def usage(self, **kw):
        Usage = request.env['beena.voice.usage'].sudo()
        Param = request.env['ir.config_parameter'].sudo()
        now   = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        recs = Usage.search([('create_date', '>=', month_start),
                             ('success', '=', True)])
        total_seconds = sum(recs.mapped('seconds'))
        total_cost    = sum(recs.mapped('cost_usd'))

        partner_id = (request.env.user.partner_id.id
                      if request.env.user.id != request.env.ref('base.public_user').id
                      else False)
        cust_seconds = 0.0
        if partner_id:
            cust_seconds = sum(Usage.search([
                ('partner_id', '=', partner_id),
                ('create_date', '>=', month_start),
                ('success', '=', True),
            ]).mapped('seconds'))

        return {
            'enabled':        Param.get_param('uellow_ai.voice_enabled', 'False') in ('True', '1', 'true'),
            'phase_a':        Param.get_param('uellow_ai.voice_phase_a_enabled', 'True') in ('True', '1', 'true'),
            'phase_b':        Param.get_param('uellow_ai.voice_phase_b_enabled', 'False') in ('True', '1', 'true'),
            'autoplay':       Param.get_param('uellow_ai.voice_autoplay_replies', 'False') in ('True', '1', 'true'),
            'month_minutes':  round(total_seconds / 60.0, 1),
            'month_cap':      int(Param.get_param('uellow_ai.voice_max_monthly_minutes', '1000') or 1000),
            'month_cost_usd': round(total_cost, 4),
            'my_minutes':     round(cust_seconds / 60.0, 1),
            'my_cap':         int(Param.get_param('uellow_ai.voice_max_per_customer_minutes', '30') or 30),
            'providers': {
                'eleven': Param.get_param('uellow_ai.voice_eleven_enabled', 'False') in ('True', '1', 'true'),
                'openai': Param.get_param('uellow_ai.voice_openai_enabled', 'False') in ('True', '1', 'true'),
                'azure':  Param.get_param('uellow_ai.voice_azure_enabled',  'False') in ('True', '1', 'true'),
                'google': Param.get_param('uellow_ai.voice_google_enabled', 'False') in ('True', '1', 'true'),
            },
        }

    # ──────────────────────────────────────────────────────────────────
    #  Admin: flush the TTS cache (call from settings UI if needed)
    # ──────────────────────────────────────────────────────────────────
    @http.route('/ai/voice/clear_cache', type='json', auth='user', methods=['POST'], csrf=False)
    def clear_cache(self, **kw):
        if not request.env.user.has_group('base.group_system'):
            return {'success': False, 'error': 'forbidden'}
        atts = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'beena.voice.cache'),
        ])
        n = len(atts)
        atts.unlink()
        return {'success': True, 'cleared': n}

    # ──────────────────────────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────────────────────────
    def _partner(self):
        pub = request.env.ref('base.public_user')
        if request.env.user.id == pub.id:
            return None
        return request.env.user.partner_id
