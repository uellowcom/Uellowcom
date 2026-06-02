# -*- coding: utf-8 -*-
"""Phase 7 v2 — Rich blog generator + direct publishing.

Major upgrade over v1:
- Article HTML is structured (H2/H3, callouts, FAQs, TL;DR, reading time)
- Embeds REAL product recommendations pulled from your catalog by
  keyword/category match. Each product is rendered as a card with
  image, name, price, and a buy-now link.
- Embeds product images inline between sections.
- Comparison table when ≥ 2 products recommended.
- FAQPage JSON-LD ready (auto-attached to the published page).
- One-click publish to website.blog.post + back-link to the suggestion.
- Settings honored: target language, length, voice, image count, etc.
"""
import json
import logging
import re

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

try:
    import anthropic
except Exception:
    anthropic = None


class SEOContentSuggestion(models.Model):
    _name = 'uellow.seo.content.suggestion'
    _description = 'AI-suggested blog topic'
    _order = 'priority desc, id desc'

    # ── Core fields ───────────────────────────────────────────────────
    title = fields.Char(required=True)
    angle = fields.Text(help='Suggested angle / outline')
    target_keywords = fields.Char()
    target_category_id = fields.Many2one('product.public.category')
    priority = fields.Selection([
        ('high', '🔴 High'),
        ('med',  '🟡 Medium'),
        ('low',  '🔵 Low'),
    ], default='med')
    state = fields.Selection([
        ('todo',      'To write'),
        ('drafted',   'Drafted'),
        ('published', 'Published'),
        ('skipped',   'Skipped'),
    ], default='todo')

    # ── Generated content ─────────────────────────────────────────────
    generated_html = fields.Html(string='Generated draft')
    summary_tldr = fields.Text(string='TL;DR summary')
    reading_time = fields.Integer(string='Reading time (min)')
    faq_json = fields.Text(string='FAQs (JSON-LD)',
        help='Stored as JSON list of {q, a} — rendered as FAQPage schema on publish.')
    recommended_product_ids = fields.Many2many('product.template',
        'uellow_seo_sugg_product_rel', 'sugg_id', 'product_id',
        string='Products featured in this article')

    # ── Publishing ────────────────────────────────────────────────────
    blog_post_id = fields.Many2one('blog.post', string='Published article',
        help='The website.blog.post created when the suggestion was published.')
    blog_post_url = fields.Char(compute='_compute_blog_post_url',
        string='Published URL')
    scheduled_publish_at = fields.Datetime(string='Scheduled publish date',
        help='If set, a cron auto-publishes this article at this date/time. '
             'The draft must already exist. Leave empty to publish manually.')
    tokens_used = fields.Integer(string='Tokens consumed', readonly=True,
        help='Approximate token cost of generating this article (sum of '
             'input + output across all AI calls for this suggestion).')
    estimated_cost_usd = fields.Float(string='Cost (USD)', readonly=True,
        digits=(8, 4))

    @api.depends('blog_post_id')
    def _compute_blog_post_url(self):
        Param = self.env['ir.config_parameter'].sudo()
        base = (Param.get_param('web.base.url') or '').rstrip('/')
        for r in self:
            if r.blog_post_id:
                r.blog_post_url = base + (r.blog_post_id.website_url or
                                          f'/blog/post/{r.blog_post_id.id}')
            else:
                r.blog_post_url = False

    # ── AI Draft generation ──────────────────────────────────────────
    def action_generate_draft(self):
        """User-facing entry — async draft."""
        for r in self:
            try:
                r._ai_draft_rich()
            except Exception:
                _logger.exception('Blog draft failed for %s', r.id)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': 'Blog draft',
                       'message': 'Drafted in the background. Refresh in ~30 seconds.',
                       'type': 'info', 'sticky': False},
        }

    def _ai_draft_rich(self):
        """Generate a rich blog article: HTML body + recommended products
        + reading time + FAQs."""
        self.ensure_one()
        if anthropic is None:
            return False
        cfg = self.env['uellow.seo.config'].sudo().get_config()
        if not cfg.anthropic_api_key:
            return False

        # 1. Find candidate products that match the topic keywords/category.
        Tmpl = self.env['product.template']
        dom = [('is_published', '=', True), ('sale_ok', '=', True)]
        if self.target_category_id:
            dom.append(('public_categ_ids', 'in', [self.target_category_id.id]))
        # Also keyword search
        kws = [k.strip() for k in (self.target_keywords or '').split(',') if k.strip()]
        if kws:
            or_kw = []
            for k in kws[:3]:
                or_kw.extend(['|', ('name', 'ilike', k), ('default_code', 'ilike', k)])
            # OR-merge with the existing AND
            dom = ['&'] + dom + or_kw if or_kw else dom
        candidates = Tmpl.search(dom, limit=int(cfg.blog_recommend_count or 6),
                                 order='write_date desc')
        # Fallback: most-recent products if nothing matched
        if not candidates:
            candidates = Tmpl.search(
                [('is_published','=',True),('sale_ok','=',True)],
                limit=int(cfg.blog_recommend_count or 6), order='write_date desc')
        self.recommended_product_ids = [(6, 0, candidates.ids)]

        Param = self.env['ir.config_parameter'].sudo()
        base = (Param.get_param('web.base.url') or '').rstrip('/')
        prod_lines = []
        prod_data = []
        for p in candidates:
            cur = p.currency_id.symbol if p.currency_id else 'KD'
            url = base + (p.website_url or f'/shop/{p.id}')
            img = f'{base}/web/image/product.template/{p.id}/image_512'
            prod_data.append({
                'id': p.id, 'name': p.name or '', 'url': url, 'img': img,
                'price': float(p.list_price or 0), 'currency': cur,
            })
            prod_lines.append(f"  - {p.name} ({p.list_price:.3f} {cur}) [PROD:{p.id}]")
        prod_text = '\n'.join(prod_lines) if prod_lines else '  (none — write a general guide)'

        # 2. Build the prompt
        lang = cfg.blog_target_lang or 'en_US'
        word_target = {'short': '500-700', 'medium': '900-1200',
                       'long': '1500-2000'}.get(cfg.blog_length, '900-1200')
        prompt = self._build_blog_prompt(cfg, prod_text, prod_data, word_target, lang)

        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        # Use the blog-specific model (Sonnet by default — better narrative).
        # Single call, longer output, justifies the higher per-token cost.
        try:
            resp = client.messages.create(
                model=cfg.ai_model_blog or cfg.ai_model or 'claude-sonnet-4-6',
                max_tokens=6000,
                messages=[{'role': 'user', 'content': prompt}],
            )
            text = ''.join(b.text for b in resp.content if hasattr(b, 'text'))
            # Token accounting — Anthropic returns usage on every response
            in_tok = getattr(resp.usage, 'input_tokens', 0) if resp.usage else 0
            out_tok = getattr(resp.usage, 'output_tokens', 0) if resp.usage else 0
            # Sonnet rates: $3/M input, $15/M output → blog ≈ $0.04
            cost = (in_tok * 3 + out_tok * 15) / 1_000_000
            self.tokens_used = (self.tokens_used or 0) + in_tok + out_tok
            self.estimated_cost_usd = (self.estimated_cost_usd or 0) + cost
            cfg.write({
                'ai_last_call_at': fields.Datetime.now(),
                'ai_call_count': (cfg.ai_call_count or 0) + 1,
            })
        except Exception:
            _logger.exception('Claude blog call failed for suggestion %s', self.id)
            return False

        parsed = self._parse_blog_json(text)
        if not parsed:
            return False

        # 3. Post-process: replace [PROD:N] markers with rich product cards.
        body = parsed.get('body_html', '')
        body = self._replace_product_markers(body, prod_data)
        # Append comparison table if AI didn't include one and we have ≥ 2 products
        if '<table' not in body and len(prod_data) >= 2:
            body += self._build_comparison_table(prod_data, lang)
        # Append related-products grid
        if cfg.blog_show_related_grid:
            body += self._build_related_grid(prod_data, lang)

        # 4. Persist on the suggestion
        self.write({
            'generated_html': body,
            'summary_tldr': parsed.get('tldr', '')[:1500],
            'reading_time': int(parsed.get('reading_min') or self._estimate_reading_time(body)),
            'faq_json': json.dumps(parsed.get('faqs', []), ensure_ascii=False)[:8000],
            'state': 'drafted',
        })
        return True

    def _build_blog_prompt(self, cfg, prod_text, prod_data, word_target, lang):
        """Compose the strict-JSON blog prompt."""
        country = cfg.ai_country_focus or 'Kuwait'
        voice = cfg.ai_brand_voice or ''
        language_name = 'Arabic' if lang.startswith('ar') else 'English'
        return f"""You are a senior SEO content strategist for Uellow, an e-commerce marketplace in {country}.

Write a high-quality blog article in {language_name} on this topic:

Title: {self.title}
Angle: {self.angle or '(infer from title)'}
Target keywords (use naturally, 3-7x each): {self.target_keywords or '(infer)'}
Target length: {word_target} words

Brand voice: {voice}

Catalog products you may recommend (use ONLY these — never invent products):
{prod_text}

When you want to recommend a product in the article body, write the literal token
`[PROD:<id>]` (e.g. `[PROD:1786]`). We replace it server-side with a rich product
card (image, name, price, buy-now button). Use 3-5 product mentions total, spaced
throughout the body. Each `[PROD:N]` must be on its own line/paragraph.

ARTICLE STRUCTURE (return as `body_html` — clean HTML, no <html>/<body> tags):
1. <p><strong>TL;DR:</strong> 2-3 sentences executive summary</p>
2. <h2>Intro section</h2> — set context, hook the reader
3. <h2>Main analysis</h2> — 3-5 H3 subsections, each with concrete advice
4. <h2>Our top picks</h2> — embed 3-5 [PROD:N] tokens with 1-2 sentence rationale each
5. <h2>How to choose</h2> — buying-guide bullets
6. <h2>FAQs</h2> — 4-6 Q&A pairs (also returned as `faqs` array for schema)
7. <h2>The bottom line</h2> — short conclusion + CTA to shop on Uellow

STYLE:
- Short paragraphs (2-4 sentences each)
- Lots of <h3>, <ul><li>, <strong>, occasional <em>
- One <blockquote> callout in the middle for a stat or quote
- No filler ("amazing", "ultimate", etc.) — concrete benefits only
- {language_name} only — no language mixing

OUTPUT STRICT JSON:
{{
  "body_html": "the full article HTML (no markdown, no scripts)",
  "tldr": "1-paragraph plain-text summary (for OG description)",
  "reading_min": <integer estimated minutes>,
  "faqs": [
    {{"q": "Question 1", "a": "Answer 1 (1-2 sentences)"}},
    ...
  ]
}}

CRITICAL: Output ONLY the JSON object, nothing before or after."""

    def _parse_blog_json(self, text):
        text = (text or '').strip()
        if text.startswith('```'):
            text = text.strip('`')
            if text.lower().startswith('json'):
                text = text[4:].lstrip()
        start = text.find('{'); end = text.rfind('}')
        if start < 0 or end <= start:
            return None
        try:
            return json.loads(text[start:end+1])
        except Exception as e:
            _logger.warning('Blog JSON parse failed: %s', e)
            return None

    def _replace_product_markers(self, html, products):
        """Swap each [PROD:N] for a rich product card. Unknown ids are
        replaced with the first available product (graceful fallback)."""
        by_id = {p['id']: p for p in products}
        def _card(p):
            return (f'<div style="border:1px solid #e5dcc2;border-radius:12px;'
                    f'padding:14px;margin:18px 0;display:flex;gap:14px;'
                    f'background:#fff">'
                    f'<a href="{p["url"]}" style="flex-shrink:0">'
                    f'<img src="{p["img"]}" alt="{p["name"]}" loading="lazy" '
                    f'style="width:130px;height:130px;object-fit:cover;'
                    f'border-radius:8px;background:#f5e8dd"/></a>'
                    f'<div style="flex:1">'
                    f'<a href="{p["url"]}" style="font-size:16px;'
                    f'font-weight:800;color:#412402;text-decoration:none">{p["name"]}</a>'
                    f'<div style="font-size:18px;font-weight:900;color:#412402;'
                    f'margin-top:6px">{p["price"]:.3f} {p["currency"]}</div>'
                    f'<a href="{p["url"]}" style="display:inline-block;'
                    f'margin-top:10px;padding:8px 16px;background:#412402;'
                    f'color:#F5C320;border-radius:6px;font-weight:700;'
                    f'text-decoration:none;font-size:13px">Shop now →</a>'
                    f'</div></div>')
        def _sub(m):
            pid = int(m.group(1))
            p = by_id.get(pid) or (products[0] if products else None)
            return _card(p) if p else ''
        return re.sub(r'\[PROD:(\d+)\]', _sub, html)

    def _build_comparison_table(self, products, lang):
        """Build a HTML comparison table when ≥ 2 products are recommended."""
        ar = lang.startswith('ar')
        h_prod = 'المنتج' if ar else 'Product'
        h_price = 'السعر' if ar else 'Price'
        h_link = 'الرابط' if ar else 'Link'
        h_cta = 'تسوّق' if ar else 'Shop'
        h_title = 'مقارنة سريعة' if ar else 'Quick comparison'
        rows = []
        for p in products[:6]:
            rows.append(
                f'<tr><td style="padding:10px;border-bottom:1px solid #f3edde">'
                f'<a href="{p["url"]}" style="color:#412402;font-weight:600">'
                f'{p["name"]}</a></td>'
                f'<td style="padding:10px;border-bottom:1px solid #f3edde;'
                f'font-weight:800">{p["price"]:.3f} {p["currency"]}</td>'
                f'<td style="padding:10px;border-bottom:1px solid #f3edde">'
                f'<a href="{p["url"]}" style="color:#F5C320;background:#412402;'
                f'padding:6px 12px;border-radius:6px;text-decoration:none;'
                f'font-weight:700;font-size:12px">{h_cta} →</a></td></tr>'
            )
        return (
            f'<h2>{h_title}</h2>'
            f'<table style="width:100%;border-collapse:collapse;'
            f'background:#fff;border-radius:10px;overflow:hidden;'
            f'margin:18px 0">'
            f'<thead><tr style="background:#412402;color:#F5C320">'
            f'<th style="padding:12px;text-align:left">{h_prod}</th>'
            f'<th style="padding:12px;text-align:left">{h_price}</th>'
            f'<th style="padding:12px;text-align:left">{h_link}</th>'
            f'</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
        )

    def _build_related_grid(self, products, lang):
        """Show a small grid of related-products at the very end."""
        if not products:
            return ''
        ar = lang.startswith('ar')
        h = 'منتجات قد تعجبك' if ar else 'You might also like'
        cards = []
        for p in products[:4]:
            cards.append(
                f'<a href="{p["url"]}" style="text-decoration:none;color:inherit">'
                f'<div style="border:1px solid #f3edde;border-radius:10px;'
                f'padding:10px;background:#fff;height:100%">'
                f'<img src="{p["img"]}" alt="{p["name"]}" loading="lazy" '
                f'style="width:100%;aspect-ratio:1;object-fit:cover;'
                f'border-radius:6px;background:#f5e8dd"/>'
                f'<div style="font-size:13px;font-weight:700;color:#412402;'
                f'margin-top:8px">{p["name"]}</div>'
                f'<div style="font-size:14px;font-weight:900;color:#412402;'
                f'margin-top:4px">{p["price"]:.3f} {p["currency"]}</div>'
                f'</div></a>')
        return (
            f'<h2>{h}</h2>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:18px 0">'
            + ''.join(cards) + '</div>'
        )

    def _estimate_reading_time(self, html):
        text = re.sub(r'<[^>]+>', ' ', html or '')
        words = len([w for w in text.split() if w.strip()])
        return max(1, round(words / 200))

    # ── Publishing ────────────────────────────────────────────────────
    def action_publish(self):
        """Create (or update) a website.blog.post from this suggestion."""
        self.ensure_one()
        if not self.generated_html:
            raise self.env['ir.actions.act_window'] and Exception(
                'No draft yet — click "Draft via AI" first.')
        Blog = self.env['blog.blog']
        Post = self.env['blog.post']
        cfg = self.env['uellow.seo.config'].sudo().get_config()

        # Pick the blog that maps to the MAIN customer-facing website
        # (uellow.com, typically website_id=1). The previous code picked
        # the first blog by id, which often lands on the B2B / portal /
        # other website and yields 404s for end-users.
        #
        # Preference order:
        #   1. blog where website_id matches the current request's website
        #   2. blog where website_id IS NULL (shared across all websites)
        #   3. blog on website_id=1 (the main public site)
        #   4. first blog (last resort)
        current_website_id = False
        try:
            from odoo.http import request as _req
            if _req and getattr(_req, 'website', False):
                current_website_id = _req.website.id
        except Exception:
            pass
        candidates = []
        if current_website_id:
            candidates += Blog.search([('website_id', '=', current_website_id)], limit=1)
        candidates += Blog.search([('website_id', '=', False)], limit=1)
        candidates += Blog.search([('website_id', '=', 1)], limit=1)
        candidates += Blog.search([], limit=1)
        blog = next((b for b in candidates if b), None)
        if not blog:
            blog = Blog.create({'name': 'Uellow Blog'})

        # Build the rich subtitle = TL;DR (used in card previews)
        subtitle = self.summary_tldr or self.title

        # FAQ JSON-LD — added inline as a hidden script so theme renders it
        faq_script = ''
        try:
            faqs = json.loads(self.faq_json or '[]')
            if faqs:
                faq_jsonld = {
                    '@context': 'https://schema.org/',
                    '@type': 'FAQPage',
                    'mainEntity': [
                        {'@type': 'Question', 'name': f.get('q', ''),
                         'acceptedAnswer': {'@type': 'Answer', 'text': f.get('a', '')}}
                        for f in faqs if f.get('q') and f.get('a')
                    ],
                }
                faq_script = (
                    '<script type="application/ld+json">'
                    + json.dumps(faq_jsonld, ensure_ascii=False)
                    + '</script>'
                )
        except Exception:
            pass

        body = (self.generated_html or '') + faq_script

        # The actual customer-facing website. Used to set BOTH blog.website_id
        # AND post.website_id so the published-post record rule allows
        # public reads (the rule filters by website_published which is
        # computed from is_published AND website match).
        target_website_id = (blog.website_id.id if blog.website_id else None) \
            or (self.env['website'].search([], limit=1).id)

        post_vals = {
            'blog_id': blog.id,
            'name': self.title,
            'subtitle': subtitle,
            'content': body,
            'is_published': True,
            'website_id': target_website_id,
        }
        if self.blog_post_id:
            self.blog_post_id.write(post_vals)
        else:
            post = Post.create(post_vals)
            self.blog_post_id = post.id
        # Ensure the blog itself is on the same website
        if blog.website_id.id != target_website_id and target_website_id:
            try:
                blog.write({'website_id': target_website_id})
            except Exception:
                pass
        self.state = 'published'
        return {
            'type': 'ir.actions.act_url',
            'url': self.blog_post_url or '/blog',
            'target': 'new',
        }

    # ── Cron jobs ─────────────────────────────────────────────────────
    @api.model
    def cron_publish_scheduled(self):
        """Publish suggestions whose scheduled_publish_at is now-or-past."""
        due = self.search([
            ('state', '=', 'drafted'),
            ('scheduled_publish_at', '!=', False),
            ('scheduled_publish_at', '<=', fields.Datetime.now()),
        ], limit=20)
        for r in due:
            try:
                r.action_publish()
            except Exception:
                _logger.exception('Scheduled publish failed for %s', r.id)
        return len(due)

    @api.model
    def cron_weekly_auto_blog(self):
        """Each run: pick the highest-priority TODO topic, generate the
        draft, optionally auto-publish. Keeps the blog fed without manual
        clicks. Controlled by `blog_auto_schedule_enable` in settings."""
        cfg = self.env['uellow.seo.config'].sudo().get_config()
        if not cfg.blog_auto_schedule_enable:
            return 0
        count = max(1, int(cfg.blog_auto_schedule_count or 1))
        # If there aren't enough TODO topics, top up via AI first
        todo = self.search([('state', '=', 'todo')], limit=count)
        if len(todo) < count:
            try:
                self.action_suggest_gaps()
                todo = self.search([('state', '=', 'todo')], limit=count)
            except Exception:
                pass
        n = 0
        for r in todo[:count]:
            try:
                r._ai_draft_rich()
                if cfg.blog_auto_publish:
                    r.action_publish()
                n += 1
            except Exception:
                _logger.exception('Auto-blog failed for %s', r.id)
        return n

    # ── Bulk topic discovery ─────────────────────────────────────────
    @api.model
    def action_suggest_gaps(self):
        """Use AI to propose blog topics that fill gaps in current catalog."""
        if anthropic is None:
            return 0
        cfg = self.env['uellow.seo.config'].sudo().get_config()
        if not cfg.anthropic_api_key:
            return 0

        Cat = self.env['product.public.category']
        cats = Cat.search([], limit=20)
        cat_list = ', '.join(cats.mapped('name'))

        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        n_to_suggest = int(cfg.blog_topics_per_run or 10)
        prompt = (
            f"You're an SEO strategist for Uellow, an e-commerce marketplace in "
            f"{cfg.ai_country_focus or 'Kuwait'}.\n"
            f"Existing categories: {cat_list}\n\n"
            f"Suggest {n_to_suggest} blog-post topics that would attract organic search "
            f"from buyers in {cfg.ai_country_focus or 'Kuwait'}/GCC. Each should target "
            f"a long-tail keyword that converts to a product purchase.\n\n"
            "Output strict JSON: a list of objects with keys: "
            '"title" (50-60 chars), "angle" (1 sentence), '
            '"target_keywords" (comma-separated, 3-5 long-tail keywords), '
            '"priority" ("high"/"med"/"low"). Output the JSON array only.'
        )
        try:
            resp = client.messages.create(
                model=cfg.ai_model or 'claude-sonnet-4-6',
                max_tokens=3000,
                messages=[{'role': 'user', 'content': prompt}],
            )
            text = ''.join(b.text for b in resp.content if hasattr(b, 'text'))
            start = text.find('['); end = text.rfind(']')
            items = json.loads(text[start:end+1]) if start >= 0 else []
        except Exception as e:
            _logger.warning('AI suggest failed: %s', e)
            return 0

        n = 0
        for it in items:
            try:
                self.create({
                    'title': (it.get('title') or '')[:200],
                    'angle': it.get('angle', ''),
                    'target_keywords': (it.get('target_keywords') or '')[:255],
                    'priority': it.get('priority', 'med') if it.get('priority') in ('high','med','low') else 'med',
                })
                n += 1
            except Exception:
                pass
        return n
