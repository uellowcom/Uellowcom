from odoo import models, fields, api


class AiConfig(models.TransientModel):
    _name = 'ai.config.settings'
    _description = 'Beena AI Settings'

    # ── Identity ──────────────────────────────────────────
    ai_enabled = fields.Boolean(string='تفعيل Beena', default=True)
    ai_assistant_name = fields.Char(string='اسم المساعد', default='Beena')
    ai_assistant_subtitle = fields.Char(string='العنوان التوضيحي', default='مساعدة Uellow الذكية')
    ai_welcome_message = fields.Char(
        string='رسالة الترحيب',
        default='أهلاً! أنا Beena 🐝 كيف أقدر أساعدك اليوم؟',
    )
    ai_button_color = fields.Char(string='لون الزر', default='#F5C320')

    # ── Claude API ────────────────────────────────────────
    ai_claude_api_key = fields.Char(string='Claude API Key')
    ai_claude_model = fields.Selection([
        ('claude-sonnet-4-6',          'Claude Sonnet 4.6 (موصى به)'),
        ('claude-opus-4-6',            'Claude Opus 4.6 (أقوى)'),
        ('claude-haiku-4-5-20251001',  'Claude Haiku 4.5 (أسرع)'),
    ], string='نموذج Claude', default='claude-sonnet-4-6')
    ai_max_tokens = fields.Integer(string='Max Tokens', default=1024)

    # ── Behaviour ─────────────────────────────────────────
    ai_float_button = fields.Boolean(string='زر Float في كل الصفحات', default=True)
    ai_buy_with_ai = fields.Boolean(string='زر Buy with AI', default=True)
    ai_proactive_nudge = fields.Boolean(string='Proactive Nudge', default=True,
        help='Show a soft "Need help?" prompt after a few seconds of idle.')
    ai_nudge_delay = fields.Integer(string='Nudge delay (seconds)', default=30,
        help='How long to wait before nudging the customer.')
    ai_nudge_auto_open = fields.Boolean(string='Auto-open chat on nudge', default=True,
        help='When the nudge fires on a product page, open the Beena panel automatically.')
    ai_nudge_message = fields.Boolean(string='Greet with a contextual message', default=True,
        help='Once Beena auto-opens, drop a friendly "Can I help with this product?" greeting.')

    # ── Auto-open & nudge mode (desktop vs mobile) ────────
    ai_autoopen_desktop_enabled = fields.Boolean(
        string='Auto-open on desktop', default=True,
        help='If enabled, the Beena panel opens automatically on desktop after the configured delay.')
    ai_autoopen_desktop_seconds = fields.Integer(
        string='Desktop delay (seconds)', default=60,
        help='Seconds to wait on desktop before auto-opening (or showing the message-only nudge).')
    ai_autoopen_mobile_enabled = fields.Boolean(
        string='Auto-open on mobile', default=False,
        help='If enabled, the Beena panel opens automatically on mobile after the configured delay.')
    ai_autoopen_mobile_seconds = fields.Integer(
        string='Mobile delay (seconds)', default=120,
        help='Seconds to wait on mobile before auto-opening (or showing the message-only nudge).')
    ai_nudge_mode = fields.Selection([
        ('open',    'Open the chat panel'),
        ('message', 'Send a message only (with animated unread badge)'),
    ], string='Nudge style', default='message',
       help='"Open": panel opens automatically. "Message": Beena types a message in the background and the float button shows an animated unread badge that nudges the customer to open it.')
    ai_nudge_anim = fields.Selection([
        ('pulse',  'Pulse (default)'),
        ('bounce', 'Bounce'),
        ('shake',  'Shake'),
        ('glow',   'Glow'),
    ], string='Badge animation', default='bounce',
       help='Animation applied to the float button when a background nudge is waiting.')

    # ── Delivery / fulfillment timing (used by Beena to answer "how long?") ──
    ai_delivery_time_text = fields.Text(
        string='Delivery time policy',
        default='Same-day delivery for orders before 2pm in Kuwait City. '
                '24–48 hours for the rest of Kuwait. '
                'International orders: 5–7 business days via DHL.',
        help='Plain-language policy injected into Beena\'s system prompt so she can answer '
             '"how long will my order take?" consistently. Keep this concise — 2-3 sentences.')
    ai_default_language = fields.Selection([
        ('auto', 'تلقائي حسب العميل'),
        ('ar',   'عربي دائماً'),
        ('en',   'إنجليزي دائماً'),
    ], string='لغة الرد', default='auto')
    ai_session_ttl = fields.Integer(string='مدة حفظ الجلسة (ساعة)', default=24)
    ai_max_upsell = fields.Integer(string='حد الـ Upsell', default=3)

    # ── Web Search ────────────────────────────────────────
    ai_web_search_enabled = fields.Boolean(string='تفعيل Web Search', default=False)
    ai_cod_enabled = fields.Boolean(string='الدفع عند الاستلام (COD)', default=True)
    ai_brave_api_key = fields.Char(string='Brave Search API Key')

    # ── Company location (shared when customer asks where Uellow is) ────────
    ai_company_name        = fields.Char(string='Company name', default='Uellow')
    ai_company_address     = fields.Text(string='Address',
        help='Free-text address shown to customers, including building, block, street, city.')
    ai_company_phone       = fields.Char(string='Phone', help='Customer-facing phone, with country code.')
    ai_company_whatsapp    = fields.Char(string='WhatsApp', help='WhatsApp number (digits only, country code).')
    ai_company_hours       = fields.Char(string='Working hours',
        help='Free-text, e.g. "Sat–Thu 10:00–22:00".')
    ai_company_lat         = fields.Float(string='Location latitude',  digits=(9, 6))
    ai_company_lng         = fields.Float(string='Location longitude', digits=(9, 6))
    ai_company_map_url     = fields.Char(string='Google Maps URL',
        help='Direct share link to the location on Google Maps.')
    ai_company_photo_urls  = fields.Text(string='Photo URLs',
        help='One URL per line. Photos of the store/showroom shown in the location card.')

    # ── Cost Control ──────────────────────────────────────
    ai_daily_cost_limit = fields.Float(string='Daily Cost Limit (USD)', default=10.0)
    ai_price_in = fields.Float(string='Claude Input Price (per 1M tokens)', default=3.0)
    ai_price_out = fields.Float(string='Claude Output Price (per 1M tokens)', default=15.0)

    # ── Prompt Caching ────────────────────────────────────
    ai_prompt_cache_enabled = fields.Boolean(string='Enable Prompt Caching', default=True)

    # ── Answer Cache ──────────────────────────────────────
    ai_cache_enabled = fields.Boolean(string='Enable Answer Cache', default=False)
    ai_cache_similarity = fields.Integer(string='Cache Match Threshold (%)', default=100)

    # ── Database Routing ──────────────────────────────────
    ai_routing_enabled = fields.Boolean(string='Enable DB Routing', default=False)

    # ── Archiving ─────────────────────────────────────────
    ai_archive_enabled = fields.Boolean(string='Enable Conversation Archive', default=True)
    ai_archive_retention_days = fields.Integer(string='Archive Retention (days)', default=90)

    # ── Cache Keywords ────────────────────────────────────
    ai_generic_keywords = fields.Text(
        string='Generic (Store-wide) Keywords',
        help='Comma/newline separated. Questions containing any of these are cached store-wide (not per-product).')

    # ── History Trimming ──────────────────────────────────
    ai_history_limit = fields.Integer(
        string='Conversation History Limit',
        default=8,
        help='Max past messages sent to Claude per request. Lower = cheaper. 0 = send all.')

    # ── Search Translations ───────────────────────────────
    ai_search_translations = fields.Text(
        string='Search Translations (ar=en per line)',
        help='Extra Arabic=English pairs to help product search. One per line, e.g. سماعة=headphone')

    # ── Variable Keywords (never cached, answered live) ───
    ai_variable_keywords = fields.Text(
        string='Variable Info Keywords',
        help='Questions with these (price, stock, colors) are answered live and NEVER cached. Comma/newline separated. Added to defaults.')

    # ── Virtual Try-On ────────────────────────────────────
    ai_tryon_enabled = fields.Boolean(string='تفعيل Virtual Try-On', default=False,
        help='Master switch for the Replicate-powered virtual try-on flow inside Beena.')
    ai_tryon_replicate_token = fields.Char(string='Replicate API Token',
        help='From replicate.com/account/api-tokens. Starts with r8_.')
    ai_tryon_replicate_model = fields.Char(string='Replicate Model',
        default='cuuupid/idm-vton',
        help='Slug of the Replicate model to use for generation.')
    ai_tryon_min_price_kd = fields.Float(string='Min Product Price (KD)', default=5.0,
        help='Try-on is only offered for products at or above this price.')
    ai_tryon_eligible_categories = fields.Text(string='Eligible Categories',
        default='shirt,tshirt,dress',
        help='Comma-separated category keywords that allow try-on (matched against product name/category).')
    ai_tryon_monthly_usd_cap = fields.Float(string='Monthly USD Cap', default=50.0,
        help='Hard stop on total Replicate spend per calendar month.')
    ai_tryon_monthly_gen_cap = fields.Integer(string='Monthly Generation Cap', default=1000,
        help='Hard stop on total generations per calendar month across all customers.')
    ai_tryon_daily_per_customer_cap = fields.Integer(string='Daily Cap per Customer', default=5,
        help='Max generations a single customer can request per calendar day.')

    # ── FASHN AI (premium provider, fashn.ai) ─────────────
    ai_tryon_fashn_enabled = fields.Boolean(string='Enable FASHN AI', default=False,
        help='Enable FASHN AI (fashn.ai) as a try-on provider.')
    ai_tryon_fashn_token = fields.Char(string='FASHN AI API Key',
        help='From fashn.ai dashboard — Bearer token used for /v1/run.')
    ai_tryon_fashn_model = fields.Char(string='FASHN Model',
        default='tryon-v1.5',
        help='FASHN model name. Common values: tryon-v1.5 (best quality), '
             'tryon-v1 (faster/cheaper).')

    # ── Provider routing ─────────────────────────────────
    ai_tryon_provider_primary = fields.Selection([
        ('fashn',     'FASHN AI (recommended)'),
        ('replicate', 'Replicate (legacy / cheaper)'),
    ], string='Primary provider', default='fashn',
       help='Which provider to call first for each generation.')
    ai_tryon_provider_fallback = fields.Selection([
        ('none',      'No fallback'),
        ('replicate', 'Replicate'),
        ('fashn',     'FASHN AI'),
    ], string='Fallback provider', default='none',
       help='If the primary provider fails, try this one.')

    # ── Try-On feature toggles (UI add-ons on the result card) ───────────
    ai_tryon_feat_color_swap        = fields.Boolean(string='Color swap',
        default=True,
        help='Show color chips after generation; pick a color → regenerate using that color\'s product image.')
    ai_tryon_feat_styling_tips      = fields.Boolean(string='AI styling tips',
        default=True,
        help='Beena suggests outfit pairings and 3 matching catalog products.')
    ai_tryon_feat_save_wishlist     = fields.Boolean(string='Save to wishlist with photo',
        default=True,
        help='"💾 Save" button adds the product to the wishlist and attaches the generated image.')
    ai_tryon_feat_pdf_download      = fields.Boolean(string='PDF download',
        default=True,
        help='"📄 PDF" button generates a watermarked PDF.')
    ai_tryon_feat_reviewer_opinion  = fields.Boolean(string='Ask reviewer opinion',
        default=True,
        help='"👥 Ask reviewer" creates a review.request and notifies a category-matched reviewer.')
    ai_tryon_feat_background_swap   = fields.Boolean(string='Background swap',
        default=False,
        help='"🏞 Change background" lets customers pick a preset background. Costs an extra generation each time.')
    ai_tryon_feat_outfit_composer   = fields.Boolean(string='Outfit composer (multi-product)',
        default=False,
        help='Try top + bottom (+ shoes) layered in one image. Costs multiple generations per outfit.')
    ai_tryon_feat_compare_models    = fields.Boolean(string='Compare FASHN models',
        default=False,
        help='"🔄 Compare" generates the same try-on with the alternate FASHN model side-by-side.')

    # ══════════════════════════════════════════════════════════════════════
    # Voice (TTS + STT + Realtime conversational)
    # 4-provider stack with smart language/length routing and a fallback chain.
    # Persisted under ir.config_parameter keys prefixed `uellow_ai.voice_*`.
    # ══════════════════════════════════════════════════════════════════════

    # ── Master switches ──────────────────────────────────────────────────
    ai_voice_enabled       = fields.Boolean(string='Enable Voice', default=False,
        help='Master switch for the entire voice stack. When off, Beena falls '
             'back to the browser-native Web Speech APIs.')
    ai_voice_phase_a_enabled = fields.Boolean(string='Enable Button-based Voice (Phase A)',
        default=True,
        help='Mic button → record → upload → STT → reply → TTS. The standard '
             'round-trip experience.')
    ai_voice_phase_b_enabled = fields.Boolean(string='Enable Realtime Voice Call (Phase B)',
        default=False,
        help='Adds a 📞 Voice Call button that opens a live conversational '
             'session via OpenAI Realtime API or ElevenLabs Conversational AI.')
    ai_voice_cache_enabled = fields.Boolean(string='Cache generated audio', default=True,
        help='Stores TTS output as ir.attachment keyed by MD5(text+voice+model). '
             'Common replies (greetings, etc.) reuse the same audio — huge cost saver.')
    ai_voice_cache_days    = fields.Integer(string='Cache TTL (days)', default=30,
        help='Audio attachments older than this are pruned by a daily cron.')
    ai_voice_autoplay_replies = fields.Boolean(string='Auto-play assistant replies',
        default=False,
        help='When ON, Beena automatically speaks each reply as it arrives '
             '(only after the user enables voice at least once).')
    ai_voice_max_monthly_minutes = fields.Integer(string='Monthly minute cap',
        default=1000,
        help='Hard stop on total voice minutes (TTS + STT + Realtime) per month.')
    ai_voice_max_per_customer_minutes = fields.Integer(
        string='Per-customer monthly minute cap', default=30,
        help='Max voice minutes a single customer can consume per calendar month.')

    # ── ElevenLabs ───────────────────────────────────────────────────────
    ai_voice_eleven_enabled = fields.Boolean(string='Enable ElevenLabs', default=False)
    ai_voice_eleven_api_key = fields.Char(string='ElevenLabs API Key',
        help='From elevenlabs.io → Profile → API Keys. Starts with sk_.')
    ai_voice_eleven_voice_ar = fields.Char(string='ElevenLabs voice (AR)',
        default='pNInz6obpgDQGcFmaJgB',
        help='Voice ID for Arabic replies. Browse voices at elevenlabs.io/voices.')
    ai_voice_eleven_voice_en = fields.Char(string='ElevenLabs voice (EN)',
        default='EXAVITQu4vr4xnSDxMaL',
        help='Voice ID for English replies.')
    ai_voice_eleven_model    = fields.Selection([
        ('eleven_flash_v2_5',        'Flash v2.5 (fastest, cheap)'),
        ('eleven_turbo_v2_5',        'Turbo v2.5 (balanced)'),
        ('eleven_multilingual_v2',   'Multilingual v2 (highest quality)'),
    ], string='ElevenLabs model', default='eleven_flash_v2_5')

    # ── OpenAI ───────────────────────────────────────────────────────────
    ai_voice_openai_enabled  = fields.Boolean(string='Enable OpenAI Voice', default=False)
    ai_voice_openai_api_key  = fields.Char(string='OpenAI API Key',
        help='From platform.openai.com/api-keys. Starts with sk-.')
    ai_voice_openai_tts_model = fields.Selection([
        ('gpt-4o-mini-tts', 'gpt-4o-mini-tts (newest, supports style instructions)'),
        ('tts-1-hd',        'tts-1-hd (highest legacy quality — best for Arabic)'),
        ('tts-1',           'tts-1 (legacy, fast & cheap)'),
    ], string='OpenAI TTS model', default='gpt-4o-mini-tts',
        help='For Arabic content, tts-1-hd often sounds the most natural. '
             'For English, gpt-4o-mini-tts is newer and supports style hints.')
    ai_voice_openai_tts_voice = fields.Selection([
        # New gpt-4o-mini-tts voices (richer, more expressive)
        ('alloy',   'alloy — neutral, balanced'),
        ('ash',     'ash — calm male (new)'),
        ('ballad',  'ballad — gentle storyteller (new)'),
        ('coral',   'coral — bright female (new)'),
        ('echo',    'echo — soft male'),
        ('fable',   'fable — expressive narrator'),
        ('nova',    'nova — warm female ⭐ (recommended)'),
        ('onyx',    'onyx — deep male'),
        ('sage',    'sage — clear female (new)'),
        ('shimmer', 'shimmer — friendly female'),
        ('verse',   'verse — confident male (new)'),
    ], string='OpenAI TTS voice', default='nova',
        help='nova / shimmer work best for Arabic. onyx / verse are deeper '
             'male voices. The new voices (ash/ballad/coral/sage/verse) are '
             'only available on gpt-4o-mini-tts.')

    # Style instructions — only honoured by gpt-4o-mini-tts. Examples:
    # "Speak in a warm, friendly Kuwaiti customer-support tone."
    ai_voice_openai_tts_instructions = fields.Text(
        string='Voice style instructions',
        default='Speak in a warm, friendly tone — calm pace, like a helpful boutique assistant.',
        help='Only honoured by the gpt-4o-mini-tts model. Leave empty to '
             'use the default voice character. Try: "Speak slowly and '
             'clearly, like a professional store advisor."')
    ai_voice_openai_stt_model = fields.Selection([
        ('whisper-1',         'whisper-1 (most languages)'),
        ('gpt-4o-transcribe', 'gpt-4o-transcribe (newest)'),
    ], string='OpenAI STT model', default='whisper-1')

    # ── Azure Neural ─────────────────────────────────────────────────────
    ai_voice_azure_enabled = fields.Boolean(string='Enable Azure Neural', default=False)
    ai_voice_azure_key     = fields.Char(string='Azure Speech key',
        help='From portal.azure.com → Speech resource → Keys and Endpoint.')
    ai_voice_azure_region  = fields.Char(string='Azure region',
        default='eastus',
        help='e.g. eastus, westeurope. Must match the Speech resource region.')
    ai_voice_azure_voice_ar = fields.Char(string='Azure voice (AR)',
        default='ar-KW-NouraNeural',
        help='Kuwaiti dialect by default. Other options: ar-SA-ZariyahNeural, ar-EG-SalmaNeural.')
    ai_voice_azure_voice_en = fields.Char(string='Azure voice (EN)',
        default='en-US-AriaNeural')

    # ── Google Cloud ─────────────────────────────────────────────────────
    ai_voice_google_enabled    = fields.Boolean(string='Enable Google Cloud Voice', default=False)
    ai_voice_google_credentials = fields.Text(string='Google service-account JSON',
        help='Paste the full JSON of a service account with Speech-to-Text + Text-to-Speech roles.')
    ai_voice_google_voice_ar    = fields.Char(string='Google voice (AR)',
        default='ar-XA-Wavenet-D')
    ai_voice_google_voice_en    = fields.Char(string='Google voice (EN)',
        default='en-US-Neural2-C')

    # ── Smart routing ────────────────────────────────────────────────────
    # Per-language primary/fallback. "auto" means the smart selector picks the
    # best-matching ENABLED provider in this order: eleven → openai → azure → google.
    _VOICE_PROVIDER_SEL = [
        ('auto',       'Auto (best enabled)'),
        ('eleven',     'ElevenLabs'),
        ('openai',     'OpenAI'),
        ('azure',      'Azure Neural'),
        ('google',     'Google WaveNet'),
        ('none',       'Disabled'),
    ]
    ai_voice_tts_primary_ar  = fields.Selection(_VOICE_PROVIDER_SEL,
        string='TTS primary (Arabic)',  default='eleven')
    ai_voice_tts_fallback_ar = fields.Selection(_VOICE_PROVIDER_SEL,
        string='TTS fallback (Arabic)', default='openai')
    ai_voice_tts_primary_en  = fields.Selection(_VOICE_PROVIDER_SEL,
        string='TTS primary (English)',  default='openai')
    ai_voice_tts_fallback_en = fields.Selection(_VOICE_PROVIDER_SEL,
        string='TTS fallback (English)', default='eleven')

    _VOICE_STT_SEL = [
        ('auto',         'Auto (best enabled)'),
        ('openai',       'OpenAI Whisper'),
        ('eleven',       'ElevenLabs Scribe'),
        ('azure',        'Azure'),
        ('google',       'Google'),
    ]
    ai_voice_stt_primary  = fields.Selection(_VOICE_STT_SEL,
        string='STT primary',  default='openai')
    ai_voice_stt_fallback = fields.Selection(_VOICE_STT_SEL + [('none', 'No fallback')],
        string='STT fallback', default='eleven')

    # Length-based override — short replies favour fast/cheap models, long
    # replies favour high-quality models. Threshold in characters.
    ai_voice_short_text_threshold = fields.Integer(
        string='Short-text threshold (chars)', default=120,
        help='Replies shorter than this use the fast/cheap quality tier when '
             'the provider supports it (e.g. ElevenLabs Flash, OpenAI tts-1).')
    ai_voice_long_text_threshold  = fields.Integer(
        string='Long-text threshold (chars)', default=500,
        help='Replies longer than this use the HD quality tier when available '
             '(e.g. ElevenLabs Multilingual v2, OpenAI tts-1-hd).')

    # ── Realtime (Phase B) ───────────────────────────────────────────────
    ai_voice_realtime_provider = fields.Selection([
        ('openai',    'OpenAI Realtime (gpt-4o-audio)'),
        ('eleven',    'ElevenLabs Conversational AI'),
        ('none',      'Disabled'),
    ], string='Realtime provider', default='openai')
    ai_voice_realtime_max_seconds = fields.Integer(
        string='Realtime max call duration (sec)', default=300,
        help='Hard cap per call. After this the WebSocket is closed.')

    # ── Helpers ───────────────────────────────────────────
    @api.model
    def _get_param(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param(
            f'uellow_ai.{key}', default
        )

    def _set_param(self, key, value):
        self.env['ir.config_parameter'].sudo().set_param(
            f'uellow_ai.{key}', str(value) if not isinstance(value, str) else value
        )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        p = self._get_param
        mapping = {
            'ai_enabled':            ('enabled',           True),
            'ai_assistant_name':     ('assistant_name',    'Beena'),
            'ai_assistant_subtitle': ('assistant_subtitle','مساعدة Uellow الذكية'),
            'ai_welcome_message':    ('welcome_message',   'أهلاً! أنا Beena 🐝'),
            'ai_button_color':       ('button_color',      '#F5C320'),
            'ai_claude_api_key':     ('claude_api_key',    ''),
            'ai_claude_model':       ('claude_model',      'claude-sonnet-4-6'),
            'ai_max_tokens':         ('max_tokens',        '1024'),
            'ai_float_button':       ('float_button',      True),
            'ai_buy_with_ai':        ('buy_with_ai',       True),
            'ai_proactive_nudge':    ('proactive_nudge',   True),
            'ai_nudge_delay':        ('nudge_delay',       '30'),
            'ai_nudge_auto_open':    ('nudge_auto_open',   True),
            'ai_nudge_message':      ('nudge_message',     True),
            'ai_autoopen_desktop_enabled': ('autoopen_desktop_enabled', True),
            'ai_autoopen_desktop_seconds': ('autoopen_desktop_seconds', '60'),
            'ai_autoopen_mobile_enabled':  ('autoopen_mobile_enabled',  False),
            'ai_autoopen_mobile_seconds':  ('autoopen_mobile_seconds',  '120'),
            'ai_nudge_mode':         ('nudge_mode',        'message'),
            'ai_nudge_anim':         ('nudge_anim',        'bounce'),
            'ai_delivery_time_text': ('delivery_time_text',
                'Same-day delivery for orders before 2pm in Kuwait City. '
                '24–48 hours for the rest of Kuwait. '
                'International orders: 5–7 business days via DHL.'),
            'ai_default_language':   ('default_language',  'auto'),
            'ai_session_ttl':        ('session_ttl',       '24'),
            'ai_web_search_enabled': ('web_search_enabled',False),
            'ai_cod_enabled':        ('cod_enabled',         True),
            'ai_brave_api_key':      ('brave_api_key',     ''),
            'ai_company_name':       ('company_name',      'Uellow'),
            'ai_company_address':    ('company_address',   ''),
            'ai_company_phone':      ('company_phone',     ''),
            'ai_company_whatsapp':   ('company_whatsapp',  ''),
            'ai_company_hours':      ('company_hours',     ''),
            'ai_company_lat':        ('company_lat',       0.0),
            'ai_company_lng':        ('company_lng',       0.0),
            'ai_company_map_url':    ('company_map_url',   ''),
            'ai_company_photo_urls': ('company_photo_urls',''),
            'ai_tryon_enabled':              ('tryon_enabled',              False),
            'ai_tryon_replicate_token':      ('tryon_replicate_token',      ''),
            'ai_tryon_replicate_model':      ('tryon_replicate_model',      'cuuupid/idm-vton'),
            'ai_tryon_min_price_kd':         ('tryon_min_price_kd',         5.0),
            'ai_tryon_eligible_categories':  ('tryon_eligible_categories',  'shirt,tshirt,dress'),
            'ai_tryon_monthly_usd_cap':      ('tryon_monthly_usd_cap',      50.0),
            'ai_tryon_monthly_gen_cap':      ('tryon_monthly_gen_cap',      1000),
            'ai_tryon_daily_per_customer_cap': ('tryon_daily_per_customer_cap', 5),
            'ai_tryon_fashn_enabled':        ('tryon_fashn_enabled',        False),
            'ai_tryon_fashn_token':          ('tryon_fashn_token',          ''),
            'ai_tryon_fashn_model':          ('tryon_fashn_model',          'tryon-v1.5'),
            'ai_tryon_provider_primary':     ('tryon_provider_primary',     'fashn'),
            'ai_tryon_provider_fallback':    ('tryon_provider_fallback',    'none'),
            'ai_tryon_feat_color_swap':       ('tryon_feat_color_swap',       True),
            'ai_tryon_feat_styling_tips':     ('tryon_feat_styling_tips',     True),
            'ai_tryon_feat_save_wishlist':    ('tryon_feat_save_wishlist',    True),
            'ai_tryon_feat_pdf_download':     ('tryon_feat_pdf_download',     True),
            'ai_tryon_feat_reviewer_opinion': ('tryon_feat_reviewer_opinion', True),
            'ai_tryon_feat_background_swap':  ('tryon_feat_background_swap',  False),
            'ai_tryon_feat_outfit_composer':  ('tryon_feat_outfit_composer',  False),
            'ai_tryon_feat_compare_models':   ('tryon_feat_compare_models',   False),
            # ── Voice stack ───────────────────────────────────────────────
            'ai_voice_enabled':                ('voice_enabled',                False),
            'ai_voice_phase_a_enabled':        ('voice_phase_a_enabled',        True),
            'ai_voice_phase_b_enabled':        ('voice_phase_b_enabled',        False),
            'ai_voice_cache_enabled':          ('voice_cache_enabled',          True),
            'ai_voice_cache_days':             ('voice_cache_days',             '30'),
            'ai_voice_autoplay_replies':       ('voice_autoplay_replies',       False),
            'ai_voice_max_monthly_minutes':    ('voice_max_monthly_minutes',    '1000'),
            'ai_voice_max_per_customer_minutes': ('voice_max_per_customer_minutes', '30'),
            'ai_voice_eleven_enabled':         ('voice_eleven_enabled',         False),
            'ai_voice_eleven_api_key':         ('voice_eleven_api_key',         ''),
            'ai_voice_eleven_voice_ar':        ('voice_eleven_voice_ar',        'pNInz6obpgDQGcFmaJgB'),
            'ai_voice_eleven_voice_en':        ('voice_eleven_voice_en',        'EXAVITQu4vr4xnSDxMaL'),
            'ai_voice_eleven_model':           ('voice_eleven_model',           'eleven_flash_v2_5'),
            'ai_voice_openai_enabled':         ('voice_openai_enabled',         False),
            'ai_voice_openai_api_key':         ('voice_openai_api_key',         ''),
            'ai_voice_openai_tts_model':       ('voice_openai_tts_model',       'gpt-4o-mini-tts'),
            'ai_voice_openai_tts_voice':       ('voice_openai_tts_voice',       'nova'),
            'ai_voice_openai_tts_instructions': ('voice_openai_tts_instructions',
                'Speak in a warm, friendly tone — calm pace, like a helpful boutique assistant.'),
            'ai_voice_openai_stt_model':       ('voice_openai_stt_model',       'whisper-1'),
            'ai_voice_azure_enabled':          ('voice_azure_enabled',          False),
            'ai_voice_azure_key':              ('voice_azure_key',              ''),
            'ai_voice_azure_region':           ('voice_azure_region',           'eastus'),
            'ai_voice_azure_voice_ar':         ('voice_azure_voice_ar',         'ar-KW-NouraNeural'),
            'ai_voice_azure_voice_en':         ('voice_azure_voice_en',         'en-US-AriaNeural'),
            'ai_voice_google_enabled':         ('voice_google_enabled',         False),
            'ai_voice_google_credentials':     ('voice_google_credentials',     ''),
            'ai_voice_google_voice_ar':        ('voice_google_voice_ar',        'ar-XA-Wavenet-D'),
            'ai_voice_google_voice_en':        ('voice_google_voice_en',        'en-US-Neural2-C'),
            'ai_voice_tts_primary_ar':         ('voice_tts_primary_ar',         'eleven'),
            'ai_voice_tts_fallback_ar':        ('voice_tts_fallback_ar',        'openai'),
            'ai_voice_tts_primary_en':         ('voice_tts_primary_en',         'openai'),
            'ai_voice_tts_fallback_en':        ('voice_tts_fallback_en',        'eleven'),
            'ai_voice_stt_primary':            ('voice_stt_primary',            'openai'),
            'ai_voice_stt_fallback':           ('voice_stt_fallback',           'eleven'),
            'ai_voice_short_text_threshold':   ('voice_short_text_threshold',   '120'),
            'ai_voice_long_text_threshold':    ('voice_long_text_threshold',    '500'),
            'ai_voice_realtime_provider':      ('voice_realtime_provider',      'openai'),
            'ai_voice_realtime_max_seconds':   ('voice_realtime_max_seconds',   '300'),
        }
        for field, (param, default) in mapping.items():
            if field in fields_list:
                val = p(param, str(default) if not isinstance(default, str) else default)
                # Cast booleans
                if isinstance(default, bool):
                    res[field] = val in ('True', '1', 'true', True)
                elif isinstance(default, float) or field in ('ai_daily_cost_limit', 'ai_price_in', 'ai_price_out',
                                                              'ai_tryon_min_price_kd', 'ai_tryon_monthly_usd_cap'):
                    try:
                        res[field] = float(val)
                    except Exception:
                        res[field] = default
                elif isinstance(default, int) or field in ('ai_max_tokens', 'ai_nudge_delay', 'ai_session_ttl', 'ai_cache_similarity', 'ai_archive_retention_days', 'ai_history_limit',
                                                            'ai_tryon_monthly_gen_cap', 'ai_tryon_daily_per_customer_cap',
                                                            'ai_autoopen_desktop_seconds', 'ai_autoopen_mobile_seconds',
                                                            'ai_voice_cache_days', 'ai_voice_max_monthly_minutes',
                                                            'ai_voice_max_per_customer_minutes',
                                                            'ai_voice_short_text_threshold', 'ai_voice_long_text_threshold',
                                                            'ai_voice_realtime_max_seconds'):
                    try:
                        res[field] = int(val)
                    except Exception:
                        res[field] = default
                else:
                    res[field] = val
        return res

    def execute(self):
        self._set_param('enabled',            str(self.ai_enabled))
        self._set_param('assistant_name',     self.ai_assistant_name or 'Beena')
        self._set_param('assistant_subtitle', self.ai_assistant_subtitle or '')
        self._set_param('welcome_message',    self.ai_welcome_message or '')
        self._set_param('button_color',       self.ai_button_color or '#F5C320')
        self._set_param('claude_api_key',     self.ai_claude_api_key or '')
        self._set_param('claude_model',       self.ai_claude_model or 'claude-sonnet-4-6')
        self._set_param('max_tokens',         str(self.ai_max_tokens or 1024))
        self._set_param('float_button',       str(self.ai_float_button))
        self._set_param('buy_with_ai',        str(self.ai_buy_with_ai))
        self._set_param('proactive_nudge',    str(self.ai_proactive_nudge))
        self._set_param('nudge_delay',        str(self.ai_nudge_delay or 30))
        self._set_param('nudge_auto_open',    str(self.ai_nudge_auto_open))
        self._set_param('nudge_message',      str(self.ai_nudge_message))
        self._set_param('autoopen_desktop_enabled', str(self.ai_autoopen_desktop_enabled))
        self._set_param('autoopen_desktop_seconds', str(self.ai_autoopen_desktop_seconds or 60))
        self._set_param('autoopen_mobile_enabled',  str(self.ai_autoopen_mobile_enabled))
        self._set_param('autoopen_mobile_seconds',  str(self.ai_autoopen_mobile_seconds or 120))
        self._set_param('nudge_mode',         self.ai_nudge_mode or 'message')
        self._set_param('nudge_anim',         self.ai_nudge_anim or 'bounce')
        self._set_param('delivery_time_text', self.ai_delivery_time_text or '')
        self._set_param('default_language',   self.ai_default_language or 'auto')
        self._set_param('session_ttl',        str(self.ai_session_ttl or 24))
        self._set_param('web_search_enabled', str(self.ai_web_search_enabled))
        self._set_param('cod_enabled',         str(self.ai_cod_enabled))
        self._set_param('brave_api_key',      self.ai_brave_api_key or '')
        self._set_param('company_name',       self.ai_company_name or 'Uellow')
        self._set_param('company_address',    self.ai_company_address or '')
        self._set_param('company_phone',      self.ai_company_phone or '')
        self._set_param('company_whatsapp',   self.ai_company_whatsapp or '')
        self._set_param('company_hours',      self.ai_company_hours or '')
        self._set_param('company_lat',        str(self.ai_company_lat or 0.0))
        self._set_param('company_lng',        str(self.ai_company_lng or 0.0))
        self._set_param('company_map_url',    self.ai_company_map_url or '')
        self._set_param('company_photo_urls', self.ai_company_photo_urls or '')
        self._set_param('daily_cost_limit',       str(self.ai_daily_cost_limit or 0.0))
        self._set_param('price_in_per_mtok',      str(self.ai_price_in or 3.0))
        self._set_param('price_out_per_mtok',     str(self.ai_price_out or 15.0))
        self._set_param('prompt_cache_enabled',   str(self.ai_prompt_cache_enabled))
        self._set_param('cache_enabled',          str(self.ai_cache_enabled))
        self._set_param('cache_similarity',       str(self.ai_cache_similarity or 100))
        self._set_param('routing_enabled',        str(self.ai_routing_enabled))
        self._set_param('archive_enabled',        str(self.ai_archive_enabled))
        self._set_param('archive_retention_days', str(self.ai_archive_retention_days or 90))
        self._set_param('generic_keywords',       self.ai_generic_keywords or '')
        self._set_param('history_limit',          str(self.ai_history_limit or 8))
        self._set_param('search_translations',    self.ai_search_translations or '')
        self._set_param('variable_keywords',      self.ai_variable_keywords or '')
        self._set_param('tryon_enabled',          str(self.ai_tryon_enabled))
        self._set_param('tryon_replicate_token',  self.ai_tryon_replicate_token or '')
        self._set_param('tryon_replicate_model',  self.ai_tryon_replicate_model or 'cuuupid/idm-vton')
        self._set_param('tryon_min_price_kd',     str(self.ai_tryon_min_price_kd or 0.0))
        self._set_param('tryon_eligible_categories', self.ai_tryon_eligible_categories or '')
        self._set_param('tryon_monthly_usd_cap',  str(self.ai_tryon_monthly_usd_cap or 0.0))
        self._set_param('tryon_monthly_gen_cap',  str(self.ai_tryon_monthly_gen_cap or 0))
        self._set_param('tryon_daily_per_customer_cap', str(self.ai_tryon_daily_per_customer_cap or 0))
        self._set_param('tryon_fashn_enabled',    str(self.ai_tryon_fashn_enabled))
        self._set_param('tryon_fashn_token',      self.ai_tryon_fashn_token or '')
        self._set_param('tryon_fashn_model',      self.ai_tryon_fashn_model or 'tryon-v1.5')
        self._set_param('tryon_provider_primary', self.ai_tryon_provider_primary or 'fashn')
        self._set_param('tryon_provider_fallback', self.ai_tryon_provider_fallback or 'none')
        self._set_param('tryon_feat_color_swap',       str(self.ai_tryon_feat_color_swap))
        self._set_param('tryon_feat_styling_tips',     str(self.ai_tryon_feat_styling_tips))
        self._set_param('tryon_feat_save_wishlist',    str(self.ai_tryon_feat_save_wishlist))
        self._set_param('tryon_feat_pdf_download',     str(self.ai_tryon_feat_pdf_download))
        self._set_param('tryon_feat_reviewer_opinion', str(self.ai_tryon_feat_reviewer_opinion))
        self._set_param('tryon_feat_background_swap',  str(self.ai_tryon_feat_background_swap))
        self._set_param('tryon_feat_outfit_composer',  str(self.ai_tryon_feat_outfit_composer))
        self._set_param('tryon_feat_compare_models',   str(self.ai_tryon_feat_compare_models))
        # Voice stack
        self._set_param('voice_enabled',                str(self.ai_voice_enabled))
        self._set_param('voice_phase_a_enabled',        str(self.ai_voice_phase_a_enabled))
        self._set_param('voice_phase_b_enabled',        str(self.ai_voice_phase_b_enabled))
        self._set_param('voice_cache_enabled',          str(self.ai_voice_cache_enabled))
        self._set_param('voice_cache_days',             str(self.ai_voice_cache_days or 30))
        self._set_param('voice_autoplay_replies',       str(self.ai_voice_autoplay_replies))
        self._set_param('voice_max_monthly_minutes',    str(self.ai_voice_max_monthly_minutes or 0))
        self._set_param('voice_max_per_customer_minutes', str(self.ai_voice_max_per_customer_minutes or 0))
        self._set_param('voice_eleven_enabled',         str(self.ai_voice_eleven_enabled))
        self._set_param('voice_eleven_api_key',         self.ai_voice_eleven_api_key or '')
        self._set_param('voice_eleven_voice_ar',        self.ai_voice_eleven_voice_ar or '')
        self._set_param('voice_eleven_voice_en',        self.ai_voice_eleven_voice_en or '')
        self._set_param('voice_eleven_model',           self.ai_voice_eleven_model or 'eleven_flash_v2_5')
        self._set_param('voice_openai_enabled',         str(self.ai_voice_openai_enabled))
        self._set_param('voice_openai_api_key',         self.ai_voice_openai_api_key or '')
        self._set_param('voice_openai_tts_model',       self.ai_voice_openai_tts_model or 'gpt-4o-mini-tts')
        self._set_param('voice_openai_tts_voice',       self.ai_voice_openai_tts_voice or 'nova')
        self._set_param('voice_openai_tts_instructions', self.ai_voice_openai_tts_instructions or '')
        self._set_param('voice_openai_stt_model',       self.ai_voice_openai_stt_model or 'whisper-1')
        self._set_param('voice_azure_enabled',          str(self.ai_voice_azure_enabled))
        self._set_param('voice_azure_key',              self.ai_voice_azure_key or '')
        self._set_param('voice_azure_region',           self.ai_voice_azure_region or 'eastus')
        self._set_param('voice_azure_voice_ar',         self.ai_voice_azure_voice_ar or '')
        self._set_param('voice_azure_voice_en',         self.ai_voice_azure_voice_en or '')
        self._set_param('voice_google_enabled',         str(self.ai_voice_google_enabled))
        self._set_param('voice_google_credentials',     self.ai_voice_google_credentials or '')
        self._set_param('voice_google_voice_ar',        self.ai_voice_google_voice_ar or '')
        self._set_param('voice_google_voice_en',        self.ai_voice_google_voice_en or '')
        self._set_param('voice_tts_primary_ar',         self.ai_voice_tts_primary_ar or 'eleven')
        self._set_param('voice_tts_fallback_ar',        self.ai_voice_tts_fallback_ar or 'openai')
        self._set_param('voice_tts_primary_en',         self.ai_voice_tts_primary_en or 'openai')
        self._set_param('voice_tts_fallback_en',        self.ai_voice_tts_fallback_en or 'eleven')
        self._set_param('voice_stt_primary',            self.ai_voice_stt_primary or 'openai')
        self._set_param('voice_stt_fallback',           self.ai_voice_stt_fallback or 'eleven')
        self._set_param('voice_short_text_threshold',   str(self.ai_voice_short_text_threshold or 120))
        self._set_param('voice_long_text_threshold',    str(self.ai_voice_long_text_threshold or 500))
        self._set_param('voice_realtime_provider',      self.ai_voice_realtime_provider or 'openai')
        self._set_param('voice_realtime_max_seconds',   str(self.ai_voice_realtime_max_seconds or 300))
        return {
            'type':  'ir.actions.client',
            'tag':   'display_notification',
            'params': {
                'message': 'تم حفظ إعدادات Beena بنجاح ✓',
                'type':    'success',
                'sticky':  False,
            },
        }

    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}
