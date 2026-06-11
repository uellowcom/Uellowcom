# -*- coding: utf-8 -*-
"""mobile.page — visually-designed pages rendered by the Flutter app.

Each page is a list of blocks (stored as JSON) plus a theme reference and
targeting (websites, countries, languages). The Flutter app fetches the
page by slug from /api/mobile/v2/pages/<slug> and renders the blocks.
"""
import json
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


KIND_SEL = [
    ('home',       'Home'),
    ('campaign',   'Campaign / Promo'),
    ('brand',      'Brand showcase'),
    ('collection', 'Curated collection'),
    ('info',       'Info / Policy'),
    ('custom',     'Custom'),
]
STATUS_SEL = [
    ('draft',     'Draft'),
    ('scheduled', 'Scheduled'),
    ('published', 'Published'),
    ('archived',  'Archived'),
]


class MobilePage(models.Model):
    _name = 'mobile.page'
    _description = 'Mobile dynamic page'
    _order = 'pinned desc, write_date desc'
    _rec_name = 'name'

    # i18n via Odoo's translate=True — works with res.lang automatically
    name = fields.Char(required=True, translate=True)
    slug = fields.Char(required=True, index=True, copy=False,
                       help='URL-safe identifier; used by the app to fetch this page')
    kind = fields.Selection(KIND_SEL, default='custom', required=True)
    status = fields.Selection(STATUS_SEL, default='draft', required=True, index=True)
    pinned = fields.Boolean(
        help='Only one page per (website, lang) may be pinned — that one is the home of the app')

    # Targeting
    website_ids = fields.Many2many('website', 'mobile_page_website_rel',
                                   'page_id', 'website_id', string='Websites')
    country_ids = fields.Many2many('res.country', 'mobile_page_country_rel',
                                   'page_id', 'country_id', string='Countries')
    lang_ids = fields.Many2many('res.lang', 'mobile_page_lang_rel',
                                'page_id', 'lang_id', string='Languages enabled',
                                help='Languages with translated content on this page')

    # Theme (reference to preset OR inline override JSON)
    theme_preset_id = fields.Many2one('mobile.theme.preset', string='Theme preset',
                                      ondelete='set null')
    theme_override = fields.Text(
        default='{}',
        help='JSON: override individual theme tokens, e.g. {"primary":"#FF0000"}')

    # Blocks — list of {id, kind, props, cond, hidden}
    blocks_json = fields.Text(default='[]', string='Blocks (JSON)',
                              help='Serialized block tree designed by the builder')

    # Schedule
    publish_at = fields.Datetime()
    unpublish_at = fields.Datetime()

    # SEO / share
    seo_title = fields.Char(translate=True)
    seo_description = fields.Text(translate=True)
    seo_image = fields.Char()

    # Stats (denormalized for the builder library cards)
    views_7d = fields.Integer(default=0, readonly=True)

    # Versioning
    version_ids = fields.One2many('mobile.page.version', 'page_id',
                                  string='Version history')
    current_version = fields.Integer(default=1, readonly=True)

    _sql_constraints = [
        ('slug_uniq', 'unique(slug)',
         'Slug must be unique — pick a different one'),
    ]

    @api.constrains('slug')
    def _check_slug(self):
        for r in self:
            if not r.slug:
                continue
            if any(ch in r.slug for ch in ' \t\n?#'):
                raise ValidationError(_('Slug must not contain spaces or "?#"'))

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for r in recs:
            r._snapshot_version('Initial')
        return recs

    def write(self, vals):
        # Snapshot when blocks change in a meaningful way (publishing or
        # explicit save). We avoid snapshotting every keystroke by gating
        # on the `with_version_snapshot` context flag.
        # `release_notes` is a synthetic key — not a real DB field. Strip
        # it before delegating so super().write() doesn't choke.
        release_notes = vals.pop('release_notes', None)
        # `_skip_snapshot` is set by _snapshot_version below so the recursive
        # write that increments current_version doesn't trigger another
        # snapshot (and so on, infinitely).
        skip = self.env.context.get('_skip_snapshot')
        should_snapshot = (not skip) and (
            self.env.context.get('with_version_snapshot')
            or vals.get('status') == 'published'
        )
        res = super().write(vals)
        if should_snapshot:
            note = release_notes or self.env.context.get('release_notes') or 'Auto save'
            for r in self:
                r._snapshot_version(note)
        return res

    def _snapshot_version(self, note=''):
        self.ensure_one()
        new_version = (self.current_version or 0) + 1
        # Bump the version field WITHOUT re-triggering the snapshot logic
        # (otherwise write() would recurse forever).
        self.with_context(_skip_snapshot=True).current_version = new_version
        self.env['mobile.page.version'].sudo().create({
            'page_id': self.id,
            'version_no': new_version,
            'blocks_json': self.blocks_json,
            'theme_override': self.theme_override,
            'note': note,
        })

    # ----- Serialization for the public + admin APIs -----

    def to_admin_dict(self):
        """Returns the rich dict used by the builder UI."""
        self.ensure_one()
        return {
            'id': self.id,
            'name': self._tr_map('name'),
            'slug': self.slug,
            'kind': self.kind,
            'status': self.status,
            'pinned': self.pinned,
            'website_ids': self.website_ids.ids,
            'country_codes': [c.code for c in self.country_ids],
            'lang_codes': [l.code for l in self.lang_ids],
            'theme': self._theme_dict(),
            'blocks': self._safe_json(self.blocks_json) or [],
            'publish_at': self.publish_at and self.publish_at.isoformat() or None,
            'unpublish_at': self.unpublish_at and self.unpublish_at.isoformat() or None,
            'seo': {
                'title': self._tr_map('seo_title'),
                'description': self._tr_map('seo_description'),
                'image': self.seo_image,
            },
            'views_7d': self.views_7d,
            'updated_at': self.write_date and self.write_date.isoformat(),
            'current_version': self.current_version,
        }

    def to_public_dict(self, lang=None):
        """Lean dict sent to the mobile app. Strings are flattened to the
        requested language (falling back to English)."""
        self.ensure_one()
        return {
            'id': self.id,
            'slug': self.slug,
            'kind': self.kind,
            'name': self._tr(lang, 'name'),
            'theme': self._theme_dict(),
            'blocks': self._public_blocks(lang),
            'seo': {
                'title': self._tr(lang, 'seo_title'),
                'description': self._tr(lang, 'seo_description'),
                'image': self.seo_image,
            },
        }

    def _theme_dict(self):
        base = self.theme_preset_id and self.theme_preset_id.to_dict() or {}
        try:
            ov = json.loads(self.theme_override or '{}')
        except Exception:
            ov = {}
        # v2.0.59 — surface the raw override dict separately so the builder
        # can show what was set without merging back into the preset.
        base.update({k: v for k, v in ov.items() if v})
        if not base:
            base = {'id': 'uellow', 'primary': '#F5C320', 'dark': '#412402',
                    'page_bg': '#FAF6EB',
                    'hero_bg': 'linear-gradient(135deg,#412402,#6b3a05 60%,#F5C320)'}
        base['override'] = ov
        return base

    def _public_blocks(self, lang):
        """Strip hidden blocks, drop those whose conditions don't match,
        and resolve each block's data (categories, products, vendors,
        images) server-side so the app can render real content directly."""
        from .block_resolver import resolve_block
        blocks = self._safe_json(self.blocks_json) or []
        short_lang = (lang or 'en').split('_')[0]
        # v2.2.26 — Brain Phase 3: one shared diversity context per page so
        # the same product never repeats across blocks. Guarded: only when
        # the engine + diversity service are on.
        ctx = None
        try:
            Cfg = self.env.get('uellow.brain.config')
            if Cfg is not None:
                cfg = Cfg.get_config()
                if cfg.enabled and cfg.div_no_repeat:
                    ctx = {'cfg': cfg, 'seen': set(),
                           'brand_n': {}, 'cat_n': {}}
        except Exception:
            ctx = None
        out = []
        for b in blocks:
            if b.get('hidden'):
                continue
            cond = b.get('cond') or {}
            langs = cond.get('languages') or []
            if langs and lang and short_lang.upper() not in [l.upper() for l in langs]:
                continue
            out.append(resolve_block(self.env, b, short_lang, ctx=ctx))
        return out

    def _tr(self, lang, field_name):
        if lang:
            return self.with_context(lang=lang)[field_name] or self[field_name] or ''
        return self[field_name] or ''

    def _tr_map(self, field_name):
        """Return {lang_code: translated_value} so the builder can show
        all language tabs at once."""
        result = {}
        active_langs = self.lang_ids or self.env['res.lang'].search([('active', '=', True)])
        for lng in active_langs:
            result[lng.code.split('_')[0]] = self.with_context(lang=lng.code)[field_name] or ''
        if 'en' not in result:
            result['en'] = self[field_name] or ''
        return result

    @staticmethod
    def _safe_json(raw):
        try:
            return json.loads(raw or '[]')
        except Exception:
            return []

    # ----- Actions used by the builder -----

    def action_publish(self):
        self.write({'status': 'published',
                    'release_notes': self.env.context.get('release_notes', '')})

    def action_archive(self):
        self.write({'status': 'archived'})

    def action_pin_as_home(self):
        # Unpin any other page on the same website set
        for r in self:
            (self.search([('id', '!=', r.id), ('pinned', '=', True),
                          ('website_ids', 'in', r.website_ids.ids)])
                .write({'pinned': False}))
            r.pinned = True


class MobilePageVersion(models.Model):
    _name = 'mobile.page.version'
    _description = 'Mobile page version snapshot'
    _order = 'page_id, version_no desc'

    page_id = fields.Many2one('mobile.page', ondelete='cascade', required=True)
    version_no = fields.Integer(required=True)
    blocks_json = fields.Text()
    theme_override = fields.Text()
    note = fields.Char()

    def action_restore(self):
        self.ensure_one()
        self.page_id.write({
            'blocks_json': self.blocks_json,
            'theme_override': self.theme_override,
        })
