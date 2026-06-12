# -*- coding: utf-8 -*-
"""SEO product-name cleanup.

Supplier imports often carry a 40-word product name (every spec crammed in),
which makes an ugly URL slug and poor SEO. This shortens such names into a
concise, SEO-friendly title (brand + model + type + one key spec + colour)
using the cheap Haiku model — for existing products (wizard + daily cron) and
new imports (gated by a setting).

Changing the name is link-safe: Odoo resolves /shop/<slug>-<id> by the trailing
ID, so old URLs keep working after the slug changes.
"""
import json
import logging
import re

from odoo import api, fields, models, _

from .utils import resolve_ai_config

_logger = logging.getLogger(__name__)
_AI_TIMEOUT_S = 60
_LONG_WORDS = 7          # names longer than this are candidates for cleanup

_SYS = (
    "You rewrite long e-commerce product names into concise, SEO-friendly "
    "titles for an electronics store. For each name keep: the brand, the model "
    "number/code, the core product type, ONE key spec (wattage, capacity, size "
    "or similar) and the colour. DROP the spec dump (long feature lists, "
    "voltages, ports, waterproof ratings, marketing words). Title Case. Max 8 "
    "words / ~65 characters. Keep brand, model numbers and units in Latin. "
    "Return ONLY a JSON object mapping the given number (as a string) to the "
    "shortened name — no prose, no code fences.")


class ProductTemplateSeoName(models.Model):
    _inherit = 'product.template'

    @api.model
    def _sc_shorten_names(self, names):
        """names: list[str] → dict {index(str): short_name}. Uses Haiku."""
        if not names:
            return {}
        api_key, model = resolve_ai_config(self.env)
        if not api_key:
            return {}
        ICP = self.env['ir.config_parameter'].sudo()
        model = (ICP.get_param('uellow.sc.translate_model') or 'claude-haiku-4-5').strip() or model
        listing = "\n".join("%d. %s" % (i, n or '') for i, n in enumerate(names))
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=_AI_TIMEOUT_S)
            msg = client.messages.create(
                model=model, max_tokens=1500, system=_SYS,
                messages=[{'role': 'user',
                           'content': 'Shorten these product names:\n' + listing}])
            text = msg.content[0].text if msg.content else '{}'
            text = re.sub(r'^```(?:json)?\s*', '', text.strip())
            text = re.sub(r'\s*```$', '', text)
            return json.loads(text)
        except Exception as e:               # noqa: BLE001
            _logger.warning('SEO name cleanup failed: %s', e)
            return {}

    @api.model
    def _sc_name_is_long(self, name):
        return len((name or '').split()) > _LONG_WORDS

    def _sc_apply_short_names(self, batch=20):
        """Shorten the English name of the products in self (in batches).
        Returns the number of products renamed."""
        recs = list(self)
        done = 0
        for s in range(0, len(recs), batch):
            chunk = recs[s:s + batch]
            names = [c.with_context(lang='en_US').name or '' for c in chunk]
            out = self._sc_shorten_names(names)
            for i, c in enumerate(chunk):
                short = (out.get(str(i)) or '').strip()
                if short and short != names[i] and 0 < len(short) < len(names[i]):
                    c.with_context(lang='en_US').write({'name': short})
                    done += 1
            self.env.cr.commit()
        return done

    # ── description cleanup: strip price + country ────────────────────
    @api.model
    def _sc_clean_one_description(self, en_html, ar_text):
        """Remove price/amount/currency and any specific country name from the
        two description fields, keeping all other wording and HTML identical.
        Returns (en, ar) or (None, None) if nothing changed / on failure."""
        if not (en_html or ar_text):
            return None, None
        api_key, model = resolve_ai_config(self.env)
        if not api_key:
            return None, None
        ICP = self.env['ir.config_parameter'].sudo()
        model = (ICP.get_param('uellow.sc.translate_model') or 'claude-haiku-4-5').strip() or model
        sysmsg = (
            "You clean e-commerce product descriptions. Remove EVERY specific "
            "price, amount, currency or money phrase (KD/KWD/دينار/د.ك/فلس/$/USD "
            "and the numbers with them), and EVERY specific country name "
            "(Kuwait/الكويت, Saudi/السعودية, UAE/الإمارات, Qatar, Bahrain, Oman, "
            "Gulf-country names). Replace a country reference with neutral wording "
            "('the region' / 'منطقتك' / 'your door'). Keep ALL other wording and "
            "ALL HTML tags exactly as-is — change nothing else. Return STRICT JSON "
            '{"en":"...","ar":"..."} only, no code fences.')
        payload = json.dumps({'en': en_html or '', 'ar': ar_text or ''}, ensure_ascii=False)
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=_AI_TIMEOUT_S)
            msg = client.messages.create(
                model=model, max_tokens=2500, system=sysmsg,
                messages=[{'role': 'user', 'content': 'Clean this:\n' + payload}])
            text = msg.content[0].text if msg.content else ''
            text = re.sub(r'^```(?:json)?\s*', '', (text or '').strip())
            text = re.sub(r'\s*```$', '', text)
            out = json.loads(text)
            return (out.get('en'), out.get('ar'))
        except Exception as e:               # noqa: BLE001
            _logger.warning('Description cleanup failed: %s', e)
            return None, None

    _PRICE_RE = re.compile(
        r'([0-9][0-9.,]*\s*(KD|KWD|USD|\$|د\.ك|دينار|فلس))|(\b(KD|KWD)\s*[0-9][0-9.,]*)', re.I)
    # Arabic alternatives need explicit non-letter boundaries — \b doesn't work
    # for Arabic, so "عمان" would otherwise match inside "يدعمان".
    _COUNTRY_RE = re.compile(
        r'\b(Kuwait|Saudi(?: Arabia)?|UAE|Emirates|Qatar|Bahrain|Oman)\b|'
        r'(?<![؀-ۿ])(الكويت|السعودية|الإمارات|قطر|البحرين|عُمان|عمان)(?![؀-ۿ])')

    def _sc_desc_needs_clean(self):
        self.ensure_one()
        blob = '%s %s' % (self.website_description or '', self.description_sale or '')
        return bool(self._PRICE_RE.search(blob) or self._COUNTRY_RE.search(blob))

    def _sc_apply_clean_descriptions(self, batch_commit=5):
        """Clean website_description (EN) + description_sale (AR) for the
        products in self that contain a price or country. Returns count."""
        done = 0
        for i, p in enumerate(self):
            try:
                if not p._sc_desc_needs_clean():
                    continue
                en, ar = self._sc_clean_one_description(
                    p.website_description or '', p.description_sale or '')
                vals = {}
                if en and en.strip() and en != (p.website_description or ''):
                    vals['website_description'] = en
                if ar and ar.strip() and ar != (p.description_sale or ''):
                    vals['description_sale'] = ar
                if vals:
                    p.write(vals)
                    done += 1
                if (i + 1) % batch_commit == 0:
                    self.env.cr.commit()
            except Exception as e:           # noqa: BLE001
                _logger.warning('Desc clean failed for %s: %s', p.id, e)
        self.env.cr.commit()
        return done

    # daily forward automation (gated)
    @api.model
    def cron_sc_shorten_names(self, limit=60):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('uellow.sc.seo_shorten_names', '1') not in ('1', 'True', 'true'):
            return
        recs = self.search([('is_published', '=', True), ('sale_ok', '=', True)])
        todo = recs.filtered(
            lambda p: self._sc_name_is_long(p.with_context(lang='en_US').name))[:limit]
        if todo:
            n = todo._sc_apply_short_names()
            _logger.info('SEO name cleanup cron: shortened %d product name(s)', n)


class SeoNameCleanup(models.TransientModel):
    _name = 'uellow.seo.name.cleanup'
    _description = 'SEO Product-Name Cleanup'

    scope_categ_id = fields.Many2one('product.public.category', string='Category')
    scope_brand_id = fields.Many2one('product.brand', string='Brand')
    long_only = fields.Boolean('Only long names', default=True)
    min_words = fields.Integer('Longer than N words', default=_LONG_WORDS)
    published_only = fields.Boolean('Published only', default=True)
    limit = fields.Integer('Max products per run', default=40)
    dry_run = fields.Boolean('Dry run (preview, no changes)', default=True)
    result_html = fields.Html('Result', readonly=True)

    def _targets(self):
        Tmpl = self.env['product.template']
        domain = [('sale_ok', '=', True)]
        if self.published_only:
            domain.append(('is_published', '=', True))
        if self.scope_categ_id:
            domain.append(('public_categ_ids', 'child_of', self.scope_categ_id.id))
        if self.scope_brand_id and 'brand_id' in Tmpl._fields:
            domain.append(('brand_id', '=', self.scope_brand_id.id))
        recs = Tmpl.search(domain, order='create_date desc')
        if self.long_only:
            recs = recs.filtered(
                lambda p: len((p.with_context(lang='en_US').name or '').split())
                > max(1, self.min_words))
        return recs[:max(1, self.limit)]

    def action_run(self):
        self.ensure_one()
        Tmpl = self.env['product.template']
        targets = self._targets()
        if not targets:
            self.result_html = "<p>No matching products.</p>"
            return self._reopen()
        if self.dry_run:
            names = [t.with_context(lang='en_US').name or '' for t in targets[:20]]
            out = Tmpl._sc_shorten_names(names)
            rows = "".join(
                "<tr><td style='color:#888'>%s</td><td>→</td><td><b>%s</b></td></tr>"
                % ((names[i][:70]), (out.get(str(i)) or '—'))
                for i in range(len(names)))
            self.result_html = (
                "<p><b>Dry run</b> — %d product(s) match; preview of first %d:</p>"
                "<table style='font-size:12px'>%s</table>"
                "<p>Untick <b>Dry run</b> and Run to apply to all %d.</p>"
                % (len(targets), len(names), rows, len(targets)))
            return self._reopen()
        n = targets._sc_apply_short_names()
        self.result_html = "<p>✅ Shortened <b>%d</b> product name(s).</p>" % n
        return self._reopen()

    def _reopen(self):
        return {'type': 'ir.actions.act_window', 'res_model': self._name,
                'res_id': self.id, 'view_mode': 'form', 'target': 'new'}
