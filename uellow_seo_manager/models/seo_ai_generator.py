# -*- coding: utf-8 -*-
"""Phase 2 — AI-powered SEO meta generator.

Calls Anthropic Claude API (key from uellow.seo.config) to produce
keyword-rich, bilingual meta titles + descriptions + alt text + keyword
suggestions per product/category. Falls back to the rule-based
`_seo_default_*` builders if no key is set or the API fails.

Pricing (Claude Sonnet 4.5 as of 2026-01):
  ~$0.003 per product (input + output tokens)
  ~1800 products ≈ $5.40 for a full-catalog regen.
"""
import json
import logging
import time

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Anthropic SDK is bundled with uellow_seo_auto's external_dependencies
try:
    import anthropic
except Exception:
    anthropic = None


class SEOConfigAI(models.Model):
    _inherit = 'uellow.seo.config'

    ai_model = fields.Char(string='AI model',
        default='claude-haiku-4-5',
        help='Anthropic model id. Default is Haiku 4.5 — ~12× cheaper than '
             'Sonnet 4.6 with very good quality for SEO copy. Switch to '
             'claude-sonnet-4-6 only for premium long-form blog content.')
    ai_model_blog = fields.Char(string='AI model — long-form blog',
        default='claude-sonnet-4-6',
        help='Used only by the blog generator (long-form, fewer calls). '
             'Sonnet costs ~$5/M output tokens vs Haiku ~$1.25/M — use '
             'Sonnet here for better narrative quality. Per-blog cost ~$0.04.')
    ai_use_prompt_cache = fields.Boolean(string='Enable Anthropic prompt cache',
        default=True,
        help='Cache the static parts of prompts (brand voice, schema, '
             'rules) at the API level. 5-minute TTL. After warm-up, '
             'these tokens cost 0.1× — typically -40-60% on bulk runs.')
    ai_skip_vision_in_bulk = fields.Boolean(string='Skip vision in bulk runs',
        default=True,
        help='Vision adds ~1500-3000 input tokens per call (~$0.005). '
             'When running bulk (cron + bulk wizard), skip vision and '
             'use product name + specs only. Single-product runs still '
             'use vision for richer copy.')
    ai_country_focus = fields.Char(string='Country focus',
        default='Kuwait',
        help='Primary market — appears in generated copy (e.g. "in Kuwait & GCC").')
    ai_brand_voice = fields.Text(string='Brand voice',
        default=('Friendly, helpful, modern. Speak directly to the customer. '
                 'Highlight value (price, free shipping, fast delivery). '
                 'Avoid fluff and generic adjectives like "amazing" or "best".'),
        help='Free-form brand voice guidelines passed to the AI prompt.')
    ai_auto_on_create = fields.Boolean(string='Auto-generate via AI on create',
        default=True,
        help='When a new product is published, queue it for AI meta generation. '
             'A rule-based meta is set instantly; AI replaces it within the hour.')
    ai_use_vision = fields.Boolean(string='Send product images to AI (vision)',
        default=True,
        help='Claude reads the actual product image and writes copy that '
             'describes what is in the image. Costs ~2x more tokens.')
    ai_write_body = fields.Boolean(string='Also write full product description (body)',
        default=True,
        help='In addition to the SEO meta tags, generate the full product '
             'page description (website_description) in both EN and AR. '
             'Includes a features list rendered as HTML.')
    ai_overwrite_existing_body = fields.Boolean(string='Overwrite existing body descriptions',
        default=False,
        help='If OFF (default), only fills products with empty website_description. '
             'Turn ON to refresh all products — destructive, use carefully.')
    ai_embed_images = fields.Boolean(string='Embed product images in the body (Image SEO)',
        default=True,
        help='AI inserts <img> tags throughout the description body using the '
             'product images. Each image gets AI-generated alt text in EN+AR. '
             'Major Image-SEO boost — Google Image Search picks up the product.')

    # ── Blog generation settings ───────────────────────────────────────
    blog_target_lang = fields.Selection([
        ('en_US', 'English'),
        ('ar_001', 'Arabic'),
    ], string='Blog target language', default='en_US',
        help='Default language for AI-drafted blog posts.')
    blog_length = fields.Selection([
        ('short', 'Short (500-700 words)'),
        ('medium','Medium (900-1200 words)'),
        ('long',  'Long (1500-2000 words)'),
    ], string='Article length', default='medium')
    blog_recommend_count = fields.Integer(string='Products recommended per article',
        default=6,
        help='How many products from the catalog are featured in each article.')
    blog_topics_per_run = fields.Integer(string='Topics generated per run',
        default=10,
        help='How many blog-topic suggestions to create when you click "AI: suggest blog topics".')
    blog_show_related_grid = fields.Boolean(string='Append related-products grid to articles',
        default=True)
    blog_auto_publish = fields.Boolean(string='Auto-publish drafts',
        default=False,
        help='Skip the draft step — publish directly when the AI finishes. Use carefully.')
    blog_auto_schedule_enable = fields.Boolean(string='Enable weekly auto-blog cron',
        default=False,
        help='Cron generates topics + drafts + publishes 1 article every Sunday. Set the count below.')
    blog_auto_schedule_count = fields.Integer(string='Auto-blogs per week',
        default=1)
    blog_author_name = fields.Char(string='Author name (E-A-T)',
        default='Uellow Editorial',
        help='Shown on published articles as the author — supports E-A-T (expertise, authority, trust) signals to Google.')

    ai_last_call_at = fields.Datetime(readonly=True)
    ai_call_count = fields.Integer(readonly=True, default=0)


class ProductTemplateAI(models.Model):
    _inherit = 'product.template'

    seo_needs_ai_regen = fields.Boolean(string='Queued for AI regen',
        default=False, index=True,
        help='Set automatically on create. Hourly cron picks these up.')

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        try:
            cfg = self.env['uellow.seo.config'].sudo().get_config()
            if cfg.ai_auto_on_create and cfg.anthropic_api_key:
                for r in recs:
                    if r.is_published or vals_list and any(v.get('is_published') for v in vals_list):
                        r.seo_needs_ai_regen = True
        except Exception:
            pass
        return recs

    def write(self, vals):
        res = super().write(vals)
        # Mark for AI regen if product just got published or got an image
        try:
            if vals.get('is_published') or vals.get('image_1920'):
                cfg = self.env['uellow.seo.config'].sudo().get_config()
                if cfg.ai_auto_on_create and cfg.anthropic_api_key:
                    for r in self:
                        if r.is_published:
                            r.with_context(skip_seo_autofill=True).write(
                                {'seo_needs_ai_regen': True})
        except Exception:
            pass
        return res

    def _seo_ai_generate(self):
        """Generate {title_en, title_ar, desc_en, desc_ar, alt_en, alt_ar,
        keywords} via Claude. Writes results into website_meta_title /
        description + a hint stored in the product chatter."""
        self.ensure_one()
        if anthropic is None:
            _logger.warning('anthropic SDK not installed — falling back to rule-based')
            return False
        cfg = self.env['uellow.seo.config'].sudo().get_config()
        key = cfg.anthropic_api_key
        if not key:
            _logger.info('No Anthropic API key — skipping AI gen for product %s', self.id)
            return False

        client = anthropic.Anthropic(api_key=key)
        prompt = self._seo_ai_build_prompt(cfg)

        # v2.0.49 cost optimization: skip vision in bulk/cron paths where
        # the per-product economy of using image tokens isn't worth it.
        # The single-product Regenerate-via-AI button still uses vision.
        skip_vision = bool(self.env.context.get('seo_skip_vision')) and cfg.ai_skip_vision_in_bulk
        use_vision = cfg.ai_use_vision and self.image_1920 and not skip_vision

        # v2.0.43 — Vision support: attach the product image so Claude can
        # actually SEE the product and describe colors/materials/details
        # it can't infer from the name alone. Convert to JPEG so the
        # media-type is always correct (Odoo stores some as WebP).
        content_blocks = []
        if use_vision:
            try:
                import base64, io
                from PIL import Image as PILImage
                # Odoo's Image field returns base64 bytes/str OR raw bytes
                # depending on context. Handle both.
                img_data = self.image_1920
                if isinstance(img_data, str):
                    img_data = img_data.encode('ascii')
                # Try decode first, fall back to raw bytes
                try:
                    raw = base64.b64decode(img_data, validate=True)
                except Exception:
                    raw = bytes(img_data)
                im = PILImage.open(io.BytesIO(raw))
                if im.mode in ('RGBA', 'LA', 'P'):
                    im = im.convert('RGB')
                # Cap at 1024px on the long side to keep token cost down
                im.thumbnail((1024, 1024), PILImage.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, format='JPEG', quality=85, optimize=True)
                img_b64 = base64.b64encode(buf.getvalue()).decode('ascii')
                content_blocks.append({
                    'type': 'image',
                    'source': {
                        'type': 'base64',
                        'media_type': 'image/jpeg',
                        'data': img_b64,
                    },
                })
            except Exception:
                _logger.warning('Image attach failed for product %s', self.id, exc_info=True)
        content_blocks.append({'type': 'text', 'text': prompt})

        try:
            # When body generation is on, allow more output tokens (HTML body
            # in two languages averages ~3000 tokens). Without body it stays
            # tight at ~700.
            max_t = 4500 if cfg.ai_write_body else 700
            # Prompt caching: mark the prompt as cacheable so Anthropic
            # serves it from the cache for 5 minutes (10× cheaper than
            # the regular input rate after warm-up). Big win for bulk runs.
            if cfg.ai_use_prompt_cache and content_blocks:
                last_text_block = next(
                    (b for b in reversed(content_blocks) if b.get('type') == 'text'),
                    None)
                if last_text_block:
                    last_text_block['cache_control'] = {'type': 'ephemeral'}
            resp = client.messages.create(
                model=cfg.ai_model or 'claude-haiku-4-5',
                max_tokens=max_t,
                messages=[{'role': 'user', 'content': content_blocks}],
            )
            text = ''.join(b.text for b in resp.content if hasattr(b, 'text'))
            # Token accounting
            try:
                u = resp.usage
                in_tok = (getattr(u, 'input_tokens', 0) or 0)
                cache_read = (getattr(u, 'cache_read_input_tokens', 0) or 0)
                out_tok = (getattr(u, 'output_tokens', 0) or 0)
                # Haiku rates: $0.25/M input, $1.25/M output, $0.025/M cache-read
                cost = (in_tok * 0.25 + cache_read * 0.025 + out_tok * 1.25) / 1_000_000
                cfg.write({
                    'ai_last_call_at': fields.Datetime.now(),
                    'ai_call_count': (cfg.ai_call_count or 0) + 1,
                })
                _logger.info('[SEO-AI %s] cost=$%.5f  in=%s  cache=%s  out=%s',
                             self.id, cost, in_tok, cache_read, out_tok)
            except Exception:
                pass
        except Exception as e:
            _logger.exception('Claude call failed for product %s', self.id)
            return False

        data = self._seo_ai_parse(text)
        if not data:
            return False
        # Debug: log which language Claude actually returned for body_en
        try:
            be = (data.get('body_en') or '')[:80]
            ba = (data.get('body_ar') or '')[:80]
            _logger.info('[SEO-AI %s] body_en preview: %r', self.id, be)
            _logger.info('[SEO-AI %s] body_ar preview: %r', self.id, ba)
        except Exception:
            pass
        # Persist meta tags
        vals = {}
        if data.get('title_en'):    vals['website_meta_title'] = data['title_en'][:70]
        if data.get('desc_en'):     vals['website_meta_description'] = data['desc_en'][:160]
        if data.get('keywords'):    vals['website_meta_keywords'] = data['keywords'][:255]

        # Body description — only write if enabled AND (empty OR overwrite is on).
        # Field selection: `website_description` is the HTML body rendered on
        # the PUBLIC product page (the "Description" tab). It's the
        # SEO-visible content. NOT `description_sale` (that one appears on
        # sales QUOTATIONS, which is internal — writing AI marketing copy
        # there pollutes the quote document the customer sees).
        cfg3 = self.env['uellow.seo.config'].sudo().get_config()
        body_field = 'website_description'
        if cfg3.ai_write_body and data.get('body_en'):
            current_body = (self[body_field] or '').strip()
            if not current_body or cfg3.ai_overwrite_existing_body:
                body_html = self._seo_inject_images_into_body(
                    data['body_en'], data.get('image_alts_en') or [])
                vals[body_field] = body_html

        # Body must go to specific lang slots. The standard Odoo write
        # path can't reliably hit specific jsonb keys for translated HTML
        # in a non-en_US session, so we bypass it with raw SQL upsert on
        # the jsonb dict. The non-translated fields go through the normal
        # ORM (so triggers, hooks, etc. still fire).
        body_html_en = vals.pop('website_description', None)
        if vals:
            super(ProductTemplateAI, self.with_context(skip_seo_autofill=True)).write(vals)
        if body_html_en:
            try:
                self.env.cr.execute(
                    """UPDATE product_template
                       SET website_description = COALESCE(website_description, '{}'::jsonb)
                           || jsonb_build_object('en_US', %s::text)
                       WHERE id = %s""",
                    [body_html_en, self.id])
                self.invalidate_recordset(['website_description'])
            except Exception:
                _logger.warning('EN body SQL write failed for product %s',
                                self.id, exc_info=True)

        # Arabic translations — meta + body.
        # We always write the AR translation when ai_write_body is on,
        # because Odoo's translatable field falls back to the source
        # language on read when no AR translation exists — so a "current
        # not empty" check is misleading. The EN body was just written;
        # the AR translation for this regen cycle is by definition new.
        has_ar = self.env['res.lang'].search([('code', '=', 'ar_001')], limit=1)
        if data.get('title_ar') and has_ar:
            ar = self.with_context(lang='ar_001')
            try:
                ar.website_meta_title = data['title_ar'][:70]
                if data.get('desc_ar'):
                    ar.website_meta_description = data['desc_ar'][:160]
            except Exception:
                _logger.warning('AR meta translation failed for product %s', self.id, exc_info=True)
        # AR body — raw SQL on the same jsonb dict so it doesn't clobber EN
        if has_ar and cfg3.ai_write_body and data.get('body_ar'):
            ar_html = self._seo_inject_images_into_body(
                data['body_ar'], data.get('image_alts_ar') or [])
            try:
                self.env.cr.execute(
                    """UPDATE product_template
                       SET website_description = COALESCE(website_description, '{}'::jsonb)
                           || jsonb_build_object('ar_001', %s::text)
                       WHERE id = %s""",
                    [ar_html, self.id])
                self.invalidate_recordset(['website_description'])
            except Exception:
                _logger.warning('AR body SQL write failed for product %s',
                                self.id, exc_info=True)
        # Clear the regen queue flag
        try:
            self.with_context(skip_seo_autofill=True).write({'seo_needs_ai_regen': False})
        except Exception:
            pass
        # Audit trail
        try:
            self.message_post(body=_(
                "🤖 SEO meta regenerated via AI<br/>"
                "<b>EN title:</b> %s<br/>"
                "<b>EN desc:</b> %s<br/>"
                "<b>AR title:</b> %s<br/>"
                "<b>Keywords:</b> %s"
            ) % (data.get('title_en',''), data.get('desc_en',''),
                 data.get('title_ar',''), data.get('keywords','')))
        except Exception:
            pass
        return data

    # ───────────────────────────────────────────────────────────────
    # Image-SEO: turn <!--IMG:N--> markers into real <img> tags
    # ───────────────────────────────────────────────────────────────
    def _seo_image_urls(self):
        """Return ordered list of full image URLs for this product (main +
        extras), suitable for embedding into the website body."""
        self.ensure_one()
        Param = self.env['ir.config_parameter'].sudo()
        base = (Param.get_param('web.base.url') or '').rstrip('/')
        urls = []
        if self.image_1920:
            urls.append(f'{base}/web/image/product.template/{self.id}/image_1024')
        for img in (self.product_template_image_ids or []):
            urls.append(f'{base}/web/image/product.image/{img.id}/image_1024')
        return urls

    def _seo_inject_images_into_body(self, body_html, alts):
        """Replace `<!--IMG:N-->` placeholders the AI emitted with real
        <img> tags using product images + AI-supplied alt text. If the AI
        didn't add markers (e.g. older response), append the main image
        once after the lead paragraph so the article still benefits from
        Image SEO."""
        import re
        self.ensure_one()
        if not body_html:
            return body_html
        urls = self._seo_image_urls()
        if not urls:
            return body_html

        def _img_tag(idx):
            url = urls[idx] if idx < len(urls) else urls[0]
            alt = (alts[idx] if idx < len(alts) else (self.name or ''))
            alt = (alt or '').replace('"', '&quot;')
            return (f'<p style="text-align:center;margin:18px 0">'
                    f'<img src="{url}" alt="{alt}" loading="lazy" '
                    f'style="max-width:100%;height:auto;border-radius:8px"/></p>')

        # Replace explicit markers
        def _sub(m):
            try:
                n = int(m.group(1)) - 1  # 1-based in markers
            except Exception:
                n = 0
            return _img_tag(max(0, n))

        replaced = re.sub(r'<!--\s*IMG\s*:\s*(\d+)\s*-->', _sub, body_html)

        # Safety net: if no markers at all but we have an image, drop the
        # first image after the lead paragraph (or just at the top).
        if '<img' not in replaced and urls:
            inserted = re.sub(r'(</p>)', r'\1' + _img_tag(0), replaced, count=1)
            if inserted == replaced:  # no </p> found
                inserted = _img_tag(0) + replaced
            replaced = inserted
        return replaced

    # ───────────────────────────────────────────────────────────────
    def _seo_ai_build_prompt(self, cfg):
        """Craft the prompt — keep tight, ask for JSON only."""
        country = (cfg.ai_country_focus or 'Kuwait').strip()
        voice   = (cfg.ai_brand_voice or '').strip()
        name = self.name or ''
        cur = self.currency_id.symbol if self.currency_id else 'KD'
        price = self.list_price or 0
        # Brand
        brand = ''
        if getattr(self, 'brand_id', False) and self.brand_id.name:
            brand = self.brand_id.name
        else:
            for line in self.attribute_line_ids:
                an = (line.attribute_id.name or '').lower()
                if 'brand' in an or 'ماركة' in an:
                    v = line.value_ids[:1]
                    if v: brand = v.name or ''
                    break
        # Body description (trim)
        body = (self.description_sale or self.description or '').strip()[:500]
        cats = ', '.join(self.public_categ_ids.mapped('name'))[:120]

        cfg2 = self.env['uellow.seo.config'].sudo().get_config()
        has_img = bool(self.image_1920) and cfg2.ai_use_vision
        write_body = cfg2.ai_write_body
        vision_hint = ('You will receive a product image attached to this '
                       'message. Use what you SEE (colors, materials, design '
                       'details, who it suits) to enrich the copy.') if has_img else ''

        # Product attribute lines = real technical specs.
        # Build a compact spec sheet to feed the model.
        spec_lines = []
        for line in self.attribute_line_ids:
            attr = (line.attribute_id.name or '').strip()
            vals = ' / '.join(v.name for v in line.value_ids if v.name)
            if attr and vals:
                spec_lines.append(f'  - {attr}: {vals}')
        spec_text = '\n'.join(spec_lines) if spec_lines else '  (no attributes defined)'

        # Collect available product images so the AI can plan where to
        # embed them and craft alt text per image.
        image_count = 0
        if self.image_1920:
            image_count += 1
        extra_imgs = self.product_template_image_ids or []
        image_count += len(extra_imgs)

        body_schema = ''
        body_instructions = ''
        if write_body:
            embed_imgs = cfg2.ai_embed_images and image_count > 0
            img_block = ''
            if embed_imgs:
                img_block = (
                    f"\n\nThis product has {image_count} image(s). To embed them in the article "
                    f"for Image SEO, insert placeholders <!--IMG:1-->, <!--IMG:2--> etc. inside "
                    f"the body HTML at natural break points (e.g. after the lead paragraph, "
                    f"between sections). Use each image at most once. We replace each placeholder "
                    f"with an <img> tag whose alt text you provide in `image_alts_en`/`image_alts_ar` "
                    f"arrays (one entry per image, 20-90 chars each, descriptive + keyword-rich).\n"
                )
            body_instructions = (
                "\n\nIMPORTANT: Also produce the FULL product page description "
                "as clean HTML — both languages. Structure:\n"
                "  1. <p> Lead paragraph (2-3 sentences hook tied to the product image).\n"
                "  2. <h3>Key features</h3> <ul><li>...</li></ul> — 4-7 bullets, "
                "concrete benefits tied to the actual specs.\n"
                "  3. <h3>What's in the box</h3> <ul>...</ul> — infer plausibly if not stated.\n"
                "  4. <h3>Why buy from Uellow</h3> <p>...</p> — short trust paragraph "
                "(authentic, warranty, fast delivery in {country}).\n"
                "Use clean HTML only — no <html>, <body>, no markdown, no inline styles.\n"
            ).format(country=country) + img_block
            body_schema = (
                ',\n  "body_en":   "MUST BE ENGLISH ONLY. Long-form HTML body description, ~250-400 words. Every word must be in English. No Arabic characters allowed in this field.",\n'
                '  "body_ar":   "MUST BE ARABIC ONLY. Long-form HTML body description, ~250-400 words. Every word must be in Arabic. English brand/model names like HainoTeko-18 are allowed to stay as-is, but everything else must be Arabic."'
            )
            if embed_imgs:
                body_schema += (
                    ',\n  "image_alts_en": ["alt for image 1", "alt for image 2", ...],'
                    '\n  "image_alts_ar": ["نص بديل للصورة ١", "نص بديل للصورة ٢", ...]'
                )

        return f"""You are an SEO copywriter for Uellow, an e-commerce marketplace in {country}.

Generate SEO meta + body description for this product. Output STRICT JSON only, no markdown, no commentary.

{vision_hint}

Product:
  Name: {name}
  Brand: {brand or '(unknown)'}
  Categories: {cats or '(none)'}
  Price: {price:.3f} {cur}
  Existing description (may be empty): {body or '(none — infer from name, image, and specs below)'}

Technical specifications (from product attributes — use these in the body):
{spec_text}

Brand voice: {voice}{body_instructions}

Output schema:
{{
  "title_en":  "55-65 chars. Include product name + brand + 'Uellow'. Power words OK.",
  "title_ar":  "Arabic translation, 55-65 chars. Same structure.",
  "desc_en":   "140-158 chars. Hook + key spec + delivery promise + CTA.",
  "desc_ar":   "Arabic translation, 140-158 chars.",
  "alt_en":    "20-90 chars. Describes the product image for alt text.",
  "alt_ar":    "Arabic alt text.",
  "keywords":  "Comma-separated, 5-10 long-tail keywords, mix of EN+AR if natural."{body_schema}
}}

CRITICAL: Output ONLY the JSON object, nothing before or after."""

    def _seo_ai_parse(self, text):
        """Extract JSON object from Claude's response."""
        text = (text or '').strip()
        # Strip code fences if present
        if text.startswith('```'):
            text = text.strip('`')
            if text.lower().startswith('json'):
                text = text[4:].lstrip()
        # Find first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start < 0 or end <= start:
            _logger.warning('AI response had no JSON: %s', text[:200])
            return None
        try:
            return json.loads(text[start:end+1])
        except Exception as e:
            _logger.warning('JSON parse failed: %s — text: %s', e, text[:300])
            return None

    # ───────────────────────────────────────────────────────────────
    # Public wrappers (for buttons / server actions)
    # ───────────────────────────────────────────────────────────────
    def action_seo_ai_generate_single(self):
        """Button entry point — runs the AI regen in the BACKGROUND so the
        Odoo web client doesn't time out with "Connection lost. Trying to
        reconnect…" (Claude calls take 10-20s; the default longpoll budget
        is shorter than that).

        Flow:
          1. Mark product(s) queued + commit so they're durable.
          2. Spawn a thread that opens its own cursor and runs the AI.
          3. Return a notification immediately — UI stays responsive.
        """
        import threading
        from odoo.modules.registry import Registry

        # Persist the queue flag before we return
        ids = self.ids
        self.with_context(skip_seo_autofill=True).write({'seo_needs_ai_regen': True})
        self.env.cr.commit()

        db_name = self.env.cr.dbname
        uid = self.env.uid

        def _run_ai_in_background():
            try:
                from odoo import api, SUPERUSER_ID
                with Registry(db_name).cursor() as new_cr:
                    new_env = api.Environment(new_cr, uid, {})
                    Tmpl = new_env['product.template']
                    for pid in ids:
                        try:
                            Tmpl.browse(pid)._seo_ai_generate()
                            new_cr.commit()
                        except Exception:
                            new_cr.rollback()
                            _logger.exception('AI regen failed for product %s', pid)
            except Exception:
                _logger.exception('Background AI thread crashed')

        threading.Thread(target=_run_ai_in_background, daemon=True,
                         name='uellow-seo-ai-%s' % ids[0] if ids else 'uellow-seo-ai').start()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '🤖 Queued for AI regeneration',
                'message': (
                    'Claude is regenerating SEO meta + body in the background. '
                    'This takes ~15 seconds per product. Refresh the page in a '
                    'moment to see the updated content.'
                ),
                'type': 'info',
                'sticky': False,
            },
        }

    # ───────────────────────────────────────────────────────────────
    # Bulk
    # ───────────────────────────────────────────────────────────────
    @api.model
    def action_seo_ai_regenerate_bulk(self, batch=20, only_missing=True):
        """Regenerate AI meta for `batch` products. Bulk runs flag the
        context with `seo_skip_vision=True` so vision tokens aren't
        burned per-product — major cost saver for full-catalog passes."""
        dom_base = [('is_published', '=', True), ('sale_ok', '=', True)]
        queued = self.search(dom_base + [('seo_needs_ai_regen', '=', True)], limit=batch)
        if len(queued) < batch and only_missing:
            extra = self.search(dom_base + [
                ('id', 'not in', queued.ids),
                '|',
                ('website_meta_description', '=', False),
                ('website_meta_description', '=', ''),
            ], limit=batch - len(queued))
            recs = queued + extra
        elif only_missing:
            recs = queued
        else:
            recs = self.search(dom_base, limit=batch)
        n = 0
        # Pass skip-vision flag down via context — cuts ~$0.005 per product
        for r in recs.with_context(seo_skip_vision=True):
            if r._seo_ai_generate():
                n += 1
            time.sleep(0.3)  # polite — avoids rate-limit
        return n

    @api.model
    def action_seo_fix_misplaced_descriptions(self):
        """One-time migration: move AI-generated content out of the
        `description_sale` field (which appears on sales QUOTATIONS — the
        wrong place) into `website_description` (the product page).

        We detect AI-generated content by its signature HTML structure:
        contains `<h3>Key features</h3>` (EN) or `<h3>المميزات` (AR).
        Anything else in `description_sale` is left alone — likely a
        legitimate sales description written by the user."""
        Tmpl = self.search([('description_sale', '!=', False),
                            ('description_sale', '!=', '')])
        moved = 0
        markers = (
            '<h3>Key features</h3>', '<h3>Key Features</h3>',
            '<h3>المميزات الرئيسية</h3>',
            'Why buy from Uellow',
            '<h3>What\'s in the box</h3>',
        )
        for r in Tmpl:
            body = r.description_sale or ''
            if not any(m in body for m in markers):
                continue
            current_web = (r.website_description or '').strip()
            new_vals = {'description_sale': False}
            if not current_web:
                new_vals['website_description'] = body
            r.with_context(skip_seo_autofill=True).write(new_vals)
            moved += 1
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': 'Description cleanup',
                       'message': f'Moved {moved} AI-generated descriptions from Quotation → Website page.',
                       'type': 'success', 'sticky': False},
        }

    @api.model
    def cron_seo_ai_queue_run(self):
        """Cron entry — process up to 30 queued products per run."""
        try:
            cfg = self.env['uellow.seo.config'].sudo().get_config()
            if not cfg.anthropic_api_key:
                return 0
        except Exception:
            return 0
        return self.action_seo_ai_regenerate_bulk(batch=30, only_missing=True)
