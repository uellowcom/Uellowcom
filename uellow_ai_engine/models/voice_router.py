"""
Beena voice router — 4-provider TTS/STT stack with smart routing.

This module is the SINGLE point that controllers/voice_controller.py talks to.
The controller passes in raw text/audio and a hint (lang, partner) and the
router decides:

    1. Which provider to call (per-language primary + length-tier override).
    2. Whether to serve from cache (TTS only).
    3. Whether to fall back to the secondary provider on error.
    4. Whether the customer/store has exceeded its monthly minute cap.
    5. How much the call cost (logged to beena.voice.usage).

Adding a 5th provider later means writing two methods (_tts_<name>,
_stt_<name>) and a tiny case in _adapter() — nothing else.
"""
import base64
import hashlib
import json
import logging
import re
import time
import urllib.request
import urllib.error
from datetime import datetime

from odoo import models, api

_logger = logging.getLogger(__name__)

# Per-million-token price card. Rough numbers — used only for the dashboard,
# never for billing. Adjust as providers change prices.
_PRICE = {
    ('tts', 'eleven', 'eleven_flash_v2_5'):       0.30 / 1000,   # $0.30 per 1k chars
    ('tts', 'eleven', 'eleven_turbo_v2_5'):       0.50 / 1000,
    ('tts', 'eleven', 'eleven_multilingual_v2'):  1.00 / 1000,
    ('tts', 'openai', 'gpt-4o-mini-tts'):         0.015 / 1000,  # $0.015 per 1k chars
    ('tts', 'openai', 'tts-1'):                   0.015 / 1000,
    ('tts', 'openai', 'tts-1-hd'):                0.030 / 1000,
    ('tts', 'azure',  'neural'):                  0.016 / 1000,
    ('tts', 'google', 'wavenet'):                 0.016 / 1000,
    ('stt', 'openai', 'whisper-1'):               0.006 / 60,    # $0.006 / min
    ('stt', 'openai', 'gpt-4o-transcribe'):       0.006 / 60,
    ('stt', 'eleven', 'scribe-v1'):               0.40 / 3600,   # $0.40 / hour
    ('stt', 'azure',  'speech-to-text'):          0.40 / 3600,
    ('stt', 'google', 'speech-v2'):               0.024 / 60,
}


class BeenaVoiceRouter(models.AbstractModel):
    """Routing + cache + usage logging. Stateless model (no records)."""
    _name        = 'beena.voice.router'
    _description = 'Beena voice provider router'

    # ──────────────────────────────────────────────────────────────────
    #  Public entrypoints (called by controllers/voice_controller.py)
    # ──────────────────────────────────────────────────────────────────

    @api.model
    def tts(self, text, lang='en', partner=None, force_provider=None):
        """Generate speech from text.

        Returns: {'success': bool, 'audio': base64-mp3 OR url, 'mimetype',
                  'cached': bool, 'provider': str, 'error': str|None,
                  'cost_usd': float}
        """
        text = (text or '').strip()
        if not text:
            return {'success': False, 'error': 'empty_text'}
        if len(text) > 4000:
            text = text[:4000]

        if not self._param_bool('voice_enabled', False):
            return {'success': False, 'error': 'voice_disabled'}

        # Enforce caps before the call — keeps a runaway loop from racking up
        # cost while we wait for someone to notice the dashboard.
        capped = self._check_caps(partner, 'tts')
        if capped:
            return {'success': False, 'error': capped}

        # Build the ordered candidate list: [force] OR [primary, fallback, none]
        if force_provider and force_provider not in ('auto', 'none'):
            candidates = [force_provider]
        else:
            candidates = self._tts_chain(lang)
        if not candidates:
            return {'success': False, 'error': 'no_provider_enabled'}

        last_err = None
        for prov in candidates:
            model_name = self._tts_model_for(prov, len(text))
            voice_id   = self._tts_voice_for(prov, lang)
            key        = self._cache_key('tts', prov, model_name, voice_id, text)

            # ── Cache hit?
            if self._param_bool('voice_cache_enabled', True):
                hit = self._cache_get(key)
                if hit:
                    self._log_usage(
                        kind='tts', provider=prov, partner=partner,
                        chars=len(text), seconds=0, success=True, cached=True,
                        cost_usd=0.0, voice_id=voice_id, model_used=model_name,
                        text_hash=key,
                    )
                    return {
                        'success':  True, 'audio': hit['data'],
                        'mimetype': hit['mimetype'], 'cached': True,
                        'provider': prov, 'cost_usd': 0.0,
                    }

            # ── Live call
            try:
                method = getattr(self, '_tts_' + prov, None)
                if not method:
                    last_err = 'adapter_missing_' + prov
                    continue
                audio_b64, mimetype = method(text, lang, voice_id, model_name)
                if not audio_b64:
                    last_err = 'empty_audio_' + prov
                    continue
                # Cache + log
                if self._param_bool('voice_cache_enabled', True):
                    self._cache_set(key, audio_b64, mimetype)
                cost = self._estimate_cost('tts', prov, model_name, chars=len(text))
                self._log_usage(
                    kind='tts', provider=prov, partner=partner,
                    chars=len(text),
                    seconds=self._estimate_seconds(text, lang),
                    success=True, cached=False, cost_usd=cost,
                    voice_id=voice_id, model_used=model_name, text_hash=key,
                )
                return {
                    'success':  True, 'audio': audio_b64, 'mimetype': mimetype,
                    'cached':   False, 'provider': prov, 'cost_usd': cost,
                }
            except Exception as e:
                last_err = str(e)[:300]
                _logger.warning('TTS %s failed: %s', prov, last_err)
                self._log_usage(
                    kind='tts', provider=prov, partner=partner,
                    chars=len(text), seconds=0, success=False, cached=False,
                    cost_usd=0.0, voice_id=voice_id, model_used=model_name,
                    text_hash=key, error=last_err,
                )
                continue

        return {'success': False, 'error': last_err or 'all_providers_failed'}

    @api.model
    def stt(self, audio_b64, mimetype='audio/webm', lang_hint=None, partner=None,
            force_provider=None):
        """Transcribe audio.

        Returns: {'success': bool, 'text': str, 'lang': str, 'provider': str,
                  'cost_usd': float, 'error': str|None}
        """
        if not audio_b64:
            return {'success': False, 'error': 'empty_audio'}
        if not self._param_bool('voice_enabled', False):
            return {'success': False, 'error': 'voice_disabled'}

        capped = self._check_caps(partner, 'stt')
        if capped:
            return {'success': False, 'error': capped}

        if force_provider and force_provider not in ('auto', 'none'):
            candidates = [force_provider]
        else:
            candidates = self._stt_chain()
        if not candidates:
            return {'success': False, 'error': 'no_provider_enabled'}

        # Rough audio duration from byte length (fine for caps).
        try:
            raw = base64.b64decode(audio_b64)
            est_seconds = max(1.0, len(raw) / 16000.0)
        except Exception:
            est_seconds = 5.0

        last_err = None
        for prov in candidates:
            try:
                method = getattr(self, '_stt_' + prov, None)
                if not method:
                    last_err = 'adapter_missing_' + prov
                    continue
                text, detected_lang = method(audio_b64, mimetype, lang_hint)
                model_name = self._stt_model_for(prov)
                cost = self._estimate_cost('stt', prov, model_name, seconds=est_seconds)
                self._log_usage(
                    kind='stt', provider=prov, partner=partner,
                    chars=len(text or ''), seconds=est_seconds,
                    success=True, cached=False, cost_usd=cost,
                    model_used=model_name,
                )
                return {
                    'success':  True, 'text': text or '',
                    'lang':     detected_lang or lang_hint or '',
                    'provider': prov, 'cost_usd': cost,
                }
            except Exception as e:
                last_err = str(e)[:300]
                _logger.warning('STT %s failed: %s', prov, last_err)
                self._log_usage(
                    kind='stt', provider=prov, partner=partner,
                    chars=0, seconds=est_seconds, success=False, cached=False,
                    cost_usd=0.0, model_used=self._stt_model_for(prov),
                    error=last_err,
                )
                continue

        return {'success': False, 'error': last_err or 'all_providers_failed'}

    @api.model
    def realtime_config(self, partner=None):
        """Return the Phase-B WebSocket connection blob the JS needs.
        For OpenAI Realtime the client signs the WS itself (we return an
        ephemeral session URL); for ElevenLabs Convo we return their agent_id
        + signed URL. Never returns the raw API key to the browser."""
        if not self._param_bool('voice_phase_b_enabled', False):
            return {'success': False, 'error': 'phase_b_disabled'}
        capped = self._check_caps(partner, 'realtime')
        if capped:
            return {'success': False, 'error': capped}
        prov = self._param('voice_realtime_provider', 'openai')
        if prov == 'openai':
            return self._realtime_openai(partner)
        if prov == 'eleven':
            return self._realtime_eleven(partner)
        return {'success': False, 'error': 'realtime_disabled'}

    # ──────────────────────────────────────────────────────────────────
    #  Routing logic
    # ──────────────────────────────────────────────────────────────────

    def _tts_chain(self, lang):
        """Return [primary, fallback] filtered to enabled providers only."""
        ar = (lang or 'en').lower().startswith('ar')
        primary  = self._param(f'voice_tts_primary_{"ar" if ar else "en"}', 'auto')
        fallback = self._param(f'voice_tts_fallback_{"ar" if ar else "en"}', 'none')
        chain = []
        for p in (primary, fallback):
            if p == 'none':
                continue
            if p == 'auto':
                chain.extend(self._auto_chain('tts'))
            elif self._provider_enabled(p):
                chain.append(p)
        # Dedup preserving order
        seen, out = set(), []
        for p in chain:
            if p not in seen:
                seen.add(p); out.append(p)
        return out

    def _stt_chain(self):
        primary  = self._param('voice_stt_primary',  'auto')
        fallback = self._param('voice_stt_fallback', 'none')
        chain = []
        for p in (primary, fallback):
            if p == 'none':
                continue
            if p == 'auto':
                chain.extend(self._auto_chain('stt'))
            elif self._provider_enabled(p):
                chain.append(p)
        seen, out = set(), []
        for p in chain:
            if p not in seen:
                seen.add(p); out.append(p)
        return out

    def _auto_chain(self, kind):
        """Default ordering when the routing is set to 'auto'."""
        if kind == 'stt':
            order = ('openai', 'eleven', 'azure', 'google')
        else:
            order = ('eleven', 'openai', 'azure', 'google')
        return [p for p in order if self._provider_enabled(p)]

    def _provider_enabled(self, prov):
        return self._param_bool(f'voice_{prov}_enabled', False) \
            and bool(self._param(f'voice_{prov}_api_key', '') or
                     self._param(f'voice_{prov}_key', '') or
                     self._param(f'voice_{prov}_credentials', ''))

    def _tts_voice_for(self, prov, lang):
        ar = (lang or 'en').lower().startswith('ar')
        suffix = 'ar' if ar else 'en'
        return self._param(f'voice_{prov}_voice_{suffix}', '')

    def _tts_model_for(self, prov, char_len):
        """Length-based override: short → fast, long → HD when supported."""
        short = self._param_int('voice_short_text_threshold', 120)
        long_ = self._param_int('voice_long_text_threshold',  500)

        if prov == 'eleven':
            base = self._param('voice_eleven_model', 'eleven_flash_v2_5')
            if char_len >= long_ and base == 'eleven_flash_v2_5':
                return 'eleven_multilingual_v2'
            return base
        if prov == 'openai':
            base = self._param('voice_openai_tts_model', 'gpt-4o-mini-tts')
            if char_len >= long_ and base == 'tts-1':
                return 'tts-1-hd'
            return base
        if prov == 'azure':
            return 'neural'
        if prov == 'google':
            return 'wavenet'
        return base if 'base' in locals() else ''

    def _stt_model_for(self, prov):
        if prov == 'openai':
            return self._param('voice_openai_stt_model', 'whisper-1')
        if prov == 'eleven':
            return 'scribe-v1'
        if prov == 'azure':
            return 'speech-to-text'
        if prov == 'google':
            return 'speech-v2'
        return ''

    # ──────────────────────────────────────────────────────────────────
    #  Provider adapters — TTS
    # ──────────────────────────────────────────────────────────────────

    def _tts_eleven(self, text, lang, voice_id, model_name):
        api_key = self._param('voice_eleven_api_key', '')
        if not api_key or not voice_id:
            raise Exception('eleven_unconfigured')
        url = f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
        body = json.dumps({
            'text':     text,
            'model_id': model_name,
            'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75},
        }).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST', headers={
            'xi-api-key':   api_key,
            'Content-Type': 'application/json',
            'Accept':       'audio/mpeg',
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            audio = resp.read()
        return base64.b64encode(audio).decode('ascii'), 'audio/mpeg'

    def _tts_openai(self, text, lang, voice_id, model_name):
        api_key = self._param('voice_openai_api_key', '')
        if not api_key:
            raise Exception('openai_unconfigured')
        # voice_id from settings holds the OpenAI voice name (alloy/nova/…)
        # which we mirror through ai_voice_openai_tts_voice. For non-OpenAI
        # voice ids (configured per provider) we fall back to "nova".
        oai_voice = self._param('voice_openai_tts_voice', 'nova')
        payload = {
            'model':           model_name,
            'voice':           oai_voice,
            'input':           text,
            'response_format': 'mp3',
        }
        # gpt-4o-mini-tts honours a style-instructions field that lets you
        # steer tone/pace/persona ("speak warmly, like a boutique advisor").
        # The older tts-1 / tts-1-hd models silently ignore it.
        if model_name == 'gpt-4o-mini-tts':
            instr = (self._param('voice_openai_tts_instructions', '') or '').strip()
            if instr:
                payload['instructions'] = instr[:1000]
        url  = 'https://api.openai.com/v1/audio/speech'
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='POST', headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type':  'application/json',
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            audio = resp.read()
        return base64.b64encode(audio).decode('ascii'), 'audio/mpeg'

    def _tts_azure(self, text, lang, voice_id, model_name):
        key    = self._param('voice_azure_key', '')
        region = self._param('voice_azure_region', 'eastus')
        if not key or not voice_id or not region:
            raise Exception('azure_unconfigured')
        url = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1'
        # voice_id encodes language: ar-KW-NouraNeural → lang ar-KW
        lang_code = '-'.join(voice_id.split('-')[:2]) if voice_id else 'en-US'
        safe = self._xml_escape(text)
        ssml = (
            f"<speak version='1.0' xml:lang='{lang_code}'>"
            f"<voice xml:lang='{lang_code}' name='{voice_id}'>{safe}</voice>"
            f"</speak>"
        ).encode('utf-8')
        req = urllib.request.Request(url, data=ssml, method='POST', headers={
            'Ocp-Apim-Subscription-Key': key,
            'Content-Type':              'application/ssml+xml',
            'X-Microsoft-OutputFormat':  'audio-24khz-48kbitrate-mono-mp3',
            'User-Agent':                'BeenaVoice/1.0',
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            audio = resp.read()
        return base64.b64encode(audio).decode('ascii'), 'audio/mpeg'

    def _tts_google(self, text, lang, voice_id, model_name):
        creds_json = self._param('voice_google_credentials', '')
        if not creds_json or not voice_id:
            raise Exception('google_unconfigured')
        # Google requires OAuth2 access token; we mint one from the SA JSON.
        token = self._google_access_token(creds_json,
                                          'https://www.googleapis.com/auth/cloud-platform')
        # Derive lang from voice id "ar-XA-Wavenet-D" → "ar-XA"
        lang_code = '-'.join(voice_id.split('-')[:2]) if voice_id else 'en-US'
        body = json.dumps({
            'input':  {'text': text},
            'voice':  {'languageCode': lang_code, 'name': voice_id},
            'audioConfig': {'audioEncoding': 'MP3'},
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://texttospeech.googleapis.com/v1/text:synthesize',
            data=body, method='POST', headers={
                'Authorization': f'Bearer {token}',
                'Content-Type':  'application/json',
            })
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        return payload.get('audioContent', ''), 'audio/mpeg'

    # ──────────────────────────────────────────────────────────────────
    #  Provider adapters — STT
    # ──────────────────────────────────────────────────────────────────

    def _stt_openai(self, audio_b64, mimetype, lang_hint):
        api_key = self._param('voice_openai_api_key', '')
        if not api_key:
            raise Exception('openai_unconfigured')
        boundary = '----BeenaBoundary' + str(int(time.time()))
        model_name = self._param('voice_openai_stt_model', 'whisper-1')
        raw = base64.b64decode(audio_b64)
        ext = self._mimetype_to_ext(mimetype)
        body  = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="model"\r\n\r\n'
            f'{model_name}\r\n'
        ).encode('utf-8')
        if lang_hint:
            body += (
                f'--{boundary}\r\n'
                f'Content-Disposition: form-data; name="language"\r\n\r\n'
                f'{lang_hint[:2]}\r\n'
            ).encode('utf-8')
        body += (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="file"; filename="audio.{ext}"\r\n'
            f'Content-Type: {mimetype}\r\n\r\n'
        ).encode('utf-8') + raw + (
            f'\r\n--{boundary}--\r\n'
        ).encode('utf-8')
        req = urllib.request.Request(
            'https://api.openai.com/v1/audio/transcriptions',
            data=body, method='POST', headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type':  f'multipart/form-data; boundary={boundary}',
            })
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        return payload.get('text', ''), payload.get('language', lang_hint or '')

    def _stt_eleven(self, audio_b64, mimetype, lang_hint):
        api_key = self._param('voice_eleven_api_key', '')
        if not api_key:
            raise Exception('eleven_unconfigured')
        boundary = '----BeenaBoundary' + str(int(time.time()))
        raw = base64.b64decode(audio_b64)
        ext = self._mimetype_to_ext(mimetype)
        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="model_id"\r\n\r\n'
            f'scribe_v1\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="file"; filename="audio.{ext}"\r\n'
            f'Content-Type: {mimetype}\r\n\r\n'
        ).encode('utf-8') + raw + (
            f'\r\n--{boundary}--\r\n'
        ).encode('utf-8')
        req = urllib.request.Request(
            'https://api.elevenlabs.io/v1/speech-to-text',
            data=body, method='POST', headers={
                'xi-api-key':   api_key,
                'Content-Type': f'multipart/form-data; boundary={boundary}',
            })
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        return payload.get('text', ''), payload.get('language_code', lang_hint or '')

    def _stt_azure(self, audio_b64, mimetype, lang_hint):
        key    = self._param('voice_azure_key', '')
        region = self._param('voice_azure_region', 'eastus')
        if not key:
            raise Exception('azure_unconfigured')
        # Azure's REST short-audio endpoint takes WAV or OGG — for webm/opus
        # the request still works in most cases via container negotiation.
        lang = (lang_hint or 'ar-KW') if (lang_hint or 'ar').startswith('ar') else 'en-US'
        url = (f'https://{region}.stt.speech.microsoft.com/speech/recognition/'
               f'conversation/cognitiveservices/v1?language={lang}')
        raw = base64.b64decode(audio_b64)
        req = urllib.request.Request(url, data=raw, method='POST', headers={
            'Ocp-Apim-Subscription-Key': key,
            'Content-Type': "audio/webm; codecs=opus" if 'webm' in mimetype else mimetype,
            'Accept':       'application/json',
        })
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        return payload.get('DisplayText', ''), lang

    def _stt_google(self, audio_b64, mimetype, lang_hint):
        creds_json = self._param('voice_google_credentials', '')
        if not creds_json:
            raise Exception('google_unconfigured')
        token = self._google_access_token(creds_json,
                                          'https://www.googleapis.com/auth/cloud-platform')
        lang = (lang_hint or 'ar-XA') if (lang_hint or 'ar').startswith('ar') else 'en-US'
        body = json.dumps({
            'config': {
                'languageCode': lang,
                'enableAutomaticPunctuation': True,
                'encoding': 'WEBM_OPUS' if 'webm' in mimetype else 'MP3',
            },
            'audio': {'content': audio_b64},
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://speech.googleapis.com/v1/speech:recognize',
            data=body, method='POST', headers={
                'Authorization': f'Bearer {token}',
                'Content-Type':  'application/json',
            })
        with urllib.request.urlopen(req, timeout=45) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
        result = payload.get('results') or [{}]
        alt    = (result[0].get('alternatives') or [{}])[0]
        return alt.get('transcript', ''), lang

    # ──────────────────────────────────────────────────────────────────
    #  Realtime (Phase B) handshakes
    # ──────────────────────────────────────────────────────────────────

    def _realtime_openai(self, partner):
        api_key = self._param('voice_openai_api_key', '')
        if not api_key:
            return {'success': False, 'error': 'openai_unconfigured'}
        # Mint an ephemeral session — the JS uses it to open the WebSocket
        # directly to OpenAI without exposing the long-lived API key.
        body = json.dumps({
            'model': 'gpt-4o-realtime-preview',
            'voice': self._param('voice_openai_tts_voice', 'nova'),
        }).encode('utf-8')
        req = urllib.request.Request(
            'https://api.openai.com/v1/realtime/sessions',
            data=body, method='POST', headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type':  'application/json',
            })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return {'success': False, 'error': 'openai_session_failed: ' + str(e)[:200]}
        return {
            'success': True,
            'provider': 'openai',
            'session_id':   payload.get('id'),
            'client_secret': (payload.get('client_secret') or {}).get('value'),
            'expires_at':   (payload.get('client_secret') or {}).get('expires_at'),
            'ws_url':       'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview',
            'max_seconds':  self._param_int('voice_realtime_max_seconds', 300),
        }

    def _realtime_eleven(self, partner):
        api_key = self._param('voice_eleven_api_key', '')
        if not api_key:
            return {'success': False, 'error': 'eleven_unconfigured'}
        # The ElevenLabs Convo AI uses signed WebSocket URLs tied to an agent.
        # The agent_id is stored under voice_eleven_agent_id (optional setting).
        # If absent, we tell the JS to fall back to Phase A.
        agent_id = self.env['ir.config_parameter'].sudo().get_param(
            'uellow_ai.voice_eleven_agent_id', '')
        if not agent_id:
            return {'success': False, 'error': 'eleven_no_agent'}
        url = f'https://api.elevenlabs.io/v1/convai/conversation/get_signed_url?agent_id={agent_id}'
        req = urllib.request.Request(url, method='GET', headers={'xi-api-key': api_key})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return {'success': False, 'error': 'eleven_signed_url_failed: ' + str(e)[:200]}
        return {
            'success':     True,
            'provider':    'eleven',
            'signed_url':  payload.get('signed_url'),
            'agent_id':    agent_id,
            'max_seconds': self._param_int('voice_realtime_max_seconds', 300),
        }

    # ──────────────────────────────────────────────────────────────────
    #  Cache (ir.attachment-backed)
    # ──────────────────────────────────────────────────────────────────

    def _cache_key(self, kind, provider, model_name, voice_id, text):
        h = hashlib.md5()
        h.update(kind.encode('utf-8'))
        h.update(b'|')
        h.update(provider.encode('utf-8'))
        h.update(b'|')
        h.update((model_name or '').encode('utf-8'))
        h.update(b'|')
        h.update((voice_id or '').encode('utf-8'))
        h.update(b'|')
        h.update(text.encode('utf-8'))
        return h.hexdigest()

    def _cache_get(self, key):
        att = self.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'beena.voice.cache'),
            ('name',      '=', key),
        ], limit=1)
        if not att:
            return None
        try:
            data = att.datas.decode('ascii') if isinstance(att.datas, bytes) else att.datas
        except Exception:
            data = att.datas
        # Refresh write_date so popular replies stay alive
        att.sudo().write({'write_date': fields_now()})
        return {'data': data, 'mimetype': att.mimetype or 'audio/mpeg'}

    def _cache_set(self, key, audio_b64, mimetype):
        try:
            self.env['ir.attachment'].sudo().create({
                'name':      key,
                'res_model': 'beena.voice.cache',
                'res_id':    0,
                'type':      'binary',
                'datas':     audio_b64,
                'mimetype':  mimetype,
                'public':    False,
            })
        except Exception as e:
            _logger.warning('voice cache write failed: %s', e)

    # ──────────────────────────────────────────────────────────────────
    #  Caps + usage log
    # ──────────────────────────────────────────────────────────────────

    def _check_caps(self, partner, kind):
        monthly = self._param_int('voice_max_monthly_minutes', 0)
        per_cust = self._param_int('voice_max_per_customer_minutes', 0)
        if not monthly and not per_cust:
            return None
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        Usage = self.env['beena.voice.usage'].sudo()
        if monthly:
            total = sum(Usage.search([('create_date', '>=', month_start),
                                      ('success', '=', True)]).mapped('seconds')) / 60.0
            if total >= monthly:
                return 'monthly_cap_reached'
        if per_cust and partner:
            mine = sum(Usage.search([('partner_id', '=', partner.id),
                                     ('create_date', '>=', month_start),
                                     ('success', '=', True)]).mapped('seconds')) / 60.0
            if mine >= per_cust:
                return 'customer_cap_reached'
        return None

    def _log_usage(self, **kw):
        try:
            self.env['beena.voice.usage'].sudo().create({
                'kind':       kw.get('kind'),
                'provider':   kw.get('provider'),
                'partner_id': (kw.get('partner') or self.env['res.partner']).id or False,
                'chars':      kw.get('chars', 0),
                'seconds':    kw.get('seconds', 0.0),
                'success':    kw.get('success', True),
                'cached':     kw.get('cached', False),
                'cost_usd':   kw.get('cost_usd', 0.0),
                'voice_id':   kw.get('voice_id', ''),
                'model_used': kw.get('model_used', ''),
                'text_hash':  kw.get('text_hash', ''),
                'error':      kw.get('error', ''),
            })
        except Exception as e:
            _logger.warning('voice usage log failed: %s', e)

    def _estimate_cost(self, kind, provider, model_name, chars=0, seconds=0.0):
        rate = _PRICE.get((kind, provider, model_name))
        if rate is None:
            return 0.0
        return round(rate * (chars if kind == 'tts' else seconds), 5)

    def _estimate_seconds(self, text, lang):
        """Cheap estimate of spoken duration — ~15 chars per second for AR,
        ~18 for EN. Used for the monthly cap accounting."""
        cps = 15.0 if (lang or 'en').startswith('ar') else 18.0
        return max(0.5, len(text) / cps)

    # ──────────────────────────────────────────────────────────────────
    #  Parameter helpers (sugar over ir.config_parameter)
    # ──────────────────────────────────────────────────────────────────

    def _param(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param(
            f'uellow_ai.{key}', default) or default

    def _param_bool(self, key, default=False):
        v = self._param(key, 'True' if default else 'False')
        return v in ('True', '1', 'true', True)

    def _param_int(self, key, default=0):
        try:
            return int(self._param(key, str(default)) or default)
        except Exception:
            return int(default)

    # ──────────────────────────────────────────────────────────────────
    #  Misc helpers
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _xml_escape(s):
        return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                 .replace('"', '&quot;').replace("'", '&apos;'))

    @staticmethod
    def _mimetype_to_ext(mt):
        m = (mt or '').lower()
        if 'webm' in m: return 'webm'
        if 'ogg'  in m: return 'ogg'
        if 'wav'  in m: return 'wav'
        if 'mp4'  in m or 'm4a' in m: return 'm4a'
        if 'mp3'  in m or 'mpeg' in m: return 'mp3'
        return 'webm'

    def _google_access_token(self, creds_json, scope):
        """Mint a short-lived access token from a service-account JSON.
        Uses the same JWT-bearer flow Google publishes."""
        try:
            info = json.loads(creds_json)
        except Exception as e:
            raise Exception('google_bad_creds: ' + str(e))
        import jwt as _jwt  # PyJWT — available in Odoo's runtime
        now = int(time.time())
        payload = {
            'iss':   info['client_email'],
            'scope': scope,
            'aud':   info['token_uri'],
            'iat':   now,
            'exp':   now + 3600,
        }
        signed = _jwt.encode(payload, info['private_key'], algorithm='RS256')
        body = (
            'grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer'
            f'&assertion={signed}'
        ).encode('utf-8')
        req = urllib.request.Request(info['token_uri'], data=body, method='POST',
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode('utf-8'))['access_token']


def fields_now():
    """Tiny helper so _cache_get doesn't have to import fields just for now()."""
    return datetime.now()
