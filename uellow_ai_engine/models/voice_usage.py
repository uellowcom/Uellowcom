"""
Beena voice — per-customer/per-month usage log.

One row per request (TTS, STT, or Realtime call). Used by /ai/voice/usage to
enforce monthly + per-customer minute caps, and by the dashboard to show cost.
"""
from odoo import models, fields, api
from datetime import datetime


class BeenaVoiceUsage(models.Model):
    _name        = 'beena.voice.usage'
    _description = 'Beena voice request log (TTS / STT / Realtime)'
    _order       = 'create_date desc'
    _rec_name    = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=True)

    kind         = fields.Selection([
        ('tts',       'TTS (text-to-speech)'),
        ('stt',       'STT (speech-to-text)'),
        ('realtime',  'Realtime conversation'),
    ], required=True, index=True)
    provider     = fields.Selection([
        ('eleven',  'ElevenLabs'),
        ('openai',  'OpenAI'),
        ('azure',   'Azure Neural'),
        ('google',  'Google Cloud'),
        ('browser', 'Browser Web Speech (fallback)'),
    ], required=True, index=True)
    partner_id   = fields.Many2one('res.partner', string='Customer', index=True,
                                   ondelete='set null')
    chars        = fields.Integer(string='Characters', default=0,
        help='For TTS: text length. For STT: transcript length.')
    seconds      = fields.Float(string='Audio seconds', default=0.0,
        help='For STT/Realtime: audio duration. For TTS: estimated playback time.')
    success      = fields.Boolean(default=True, index=True)
    cached       = fields.Boolean(default=False, index=True,
        help='True when a TTS request was served entirely from the cache (no API call).')
    cost_usd     = fields.Float(string='Estimated cost (USD)', digits=(8, 5), default=0.0,
        help='Best-effort cost estimate from the provider price card.')
    voice_id     = fields.Char(string='Voice ID')
    model_used   = fields.Char(string='Provider model')
    text_hash    = fields.Char(string='Cache key', index=True,
        help='MD5(text + voice + model). Set for TTS, blank for STT.')
    error        = fields.Char(string='Error (if failed)')

    @api.depends('kind', 'provider', 'partner_id', 'chars', 'seconds')
    def _compute_display_name(self):
        for r in self:
            who = r.partner_id.name if r.partner_id else 'Guest'
            if r.kind == 'tts':
                meta = '%d chars' % (r.chars or 0)
            else:
                meta = '%.1fs' % (r.seconds or 0)
            r.display_name = f'[{(r.provider or "?").upper()}] {r.kind} · {who} · {meta}'
