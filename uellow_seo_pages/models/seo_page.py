"""SEO landing page model with draft/publish workflow, slug validation,
atomic visit counter, FAQ schema support.

Bugfix history:
  - B5/F6: slug auto-generated from title + regex-validated on write.
  - F7: state machine (draft/review/published/archived); controller only
    serves `published` pages publicly (preview mode for staff).
  - A7: visit_count incremented via raw SQL UPDATE (atomic).
  - B11: h1 cascade fallback in helper.
"""
import logging
import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

try:
    from odoo.tools import slugify
except ImportError:  # very old Odoo fallback
    def slugify(s):
        return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')

_logger = logging.getLogger(__name__)

_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]{1,80}[a-z0-9]$')


class SEOLandingPage(models.Model):
    _name = 'uellow.seo.page'
    _description = 'SEO Landing Page'
    _rec_name = 'title_en'
    _order = 'sequence, id desc'

    sequence = fields.Integer(default=10)

    # Content — bilingual primary
    title_en = fields.Char('Title (EN)', required=True)
    title_ar = fields.Char('Title (AR)')
    slug = fields.Char('URL Slug', required=True, index=True,
        help='Lowercase letters, digits, dashes only. Auto-generated from title if empty.')
    meta_desc_en = fields.Text('Meta Description (EN)')
    meta_desc_ar = fields.Text('Meta Description (AR)')
    h1_en = fields.Char('H1 (EN)')
    h1_ar = fields.Char('H1 (AR)')
    intro_en = fields.Text('Intro Paragraph (EN)')
    intro_ar = fields.Text('Intro Paragraph (AR)')

    # State machine (F7)
    state = fields.Selection([
        ('draft',     'Draft'),
        ('review',    'In Review'),
        ('published', 'Published'),
        ('archived',  'Archived'),
    ], default='draft', required=True, tracking=True, index=True)

    # Product source
    product_source = fields.Selection([
        ('category',    'Category'),
        ('tag',         'Product Tag'),
        ('manual',      'Manual Selection'),
        ('top_sellers', 'Top Sellers'),
    ], default='category', required=True)
    category_id = fields.Many2one('product.category')
    tag_ids = fields.Many2many('product.tag', string='Product Tags')
    manual_product_ids = fields.Many2many(
        'product.template', string='Products',
        domain="[('website_published','=',True)]",
    )
    max_products = fields.Integer('Max Products', default=12)

    # OG image (F5)
    og_image = fields.Binary('Social Share Image', attachment=True,
        help='1200x630 recommended. Falls back to first product image.')

    # Stats — write via SQL for atomicity (A7)
    active = fields.Boolean(default=True)
    visit_count = fields.Integer('Visit Count', default=0, readonly=True)
    last_visited = fields.Datetime('Last Visited', readonly=True)
    created_by_ai = fields.Boolean('AI Generated', default=False)

    # FAQ (F13)
    faq_ids = fields.One2many('uellow.seo.page.faq', 'page_id', string='FAQ entries')

    _sql_constraints = [
        ('unique_slug', 'UNIQUE(slug)', 'Page slug must be unique.'),
    ]

    # ── Validation + auto-slug ──────────────────────────────────────
    @api.constrains('slug')
    def _check_slug(self):
        for r in self:
            if not _SLUG_RE.match(r.slug or ''):
                raise ValidationError(_(
                    'Invalid slug "%s". Use lowercase letters, digits, dashes; '
                    'no spaces or special characters.') % r.slug)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if not (v.get('slug') or '').strip() and v.get('title_en'):
                v['slug'] = self._uniqueify_slug(slugify(v['title_en']))
            elif v.get('slug'):
                v['slug'] = (v['slug'] or '').strip().lower()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('slug'):
            vals['slug'] = (vals['slug'] or '').strip().lower()
        return super().write(vals)

    def _uniqueify_slug(self, base):
        """Append -2 / -3 until unique. base must already be a valid slug."""
        if not base:
            base = 'page'
        candidate = base
        i = 2
        while self.search_count([('slug', '=', candidate)]):
            candidate = f'{base}-{i}'
            i += 1
        return candidate

    # ── Product source ──────────────────────────────────────────────
    def get_products(self, limit=12):
        """Resolve product_source → recordset, capped at `limit`."""
        self.ensure_one()
        domain = [('website_published', '=', True)]
        ProductT = self.env['product.template'].sudo()
        if self.product_source == 'category' and self.category_id:
            domain.append(('categ_id', 'child_of', self.category_id.id))
        elif self.product_source == 'tag' and self.tag_ids:
            domain.append(('product_tag_ids', 'in', self.tag_ids.ids))
        elif self.product_source == 'manual':
            # Filter manual selection by published status defensively.
            return self.manual_product_ids.filtered('website_published')[:limit]
        elif self.product_source == 'top_sellers':
            # Order by sales count if available
            try:
                return ProductT.search(domain, limit=limit, order='sales_count desc')
            except Exception:
                pass
        return ProductT.search(domain, limit=limit)

    # ── Helpers used by the template ────────────────────────────────
    def localized(self, lang_code):
        """Return (title, h1, intro, meta_desc) cascading EN ↔ AR."""
        self.ensure_one()
        is_ar = (lang_code or '').startswith('ar')
        title    = (self.title_ar or self.title_en) if is_ar else (self.title_en or self.title_ar)
        # B11: cascade so a missing language doesn't render blank
        h1       = (self.h1_ar or self.h1_en or self.title_ar or self.title_en) if is_ar else \
                   (self.h1_en or self.h1_ar or self.title_en or self.title_ar)
        intro    = (self.intro_ar or self.intro_en or '') if is_ar else \
                   (self.intro_en or self.intro_ar or '')
        meta     = (self.meta_desc_ar or self.meta_desc_en or '') if is_ar else \
                   (self.meta_desc_en or self.meta_desc_ar or '')
        return title, h1, intro, meta

    def record_visit(self):
        """Atomic visit-count bump (A7)."""
        self.ensure_one()
        self.env.cr.execute(
            'UPDATE uellow_seo_page '
            'SET visit_count = visit_count + 1, last_visited = NOW() '
            'WHERE id = %s', [self.id])

    # ── State machine buttons ───────────────────────────────────────
    def action_submit_for_review(self):
        for r in self:
            if r.state != 'draft':
                continue
            r.state = 'review'

    def action_publish(self):
        for r in self:
            r.state = 'published'

    def action_unpublish(self):
        for r in self:
            r.state = 'draft'

    def action_archive(self):
        for r in self:
            r.state = 'archived'
            r.active = False

    def action_preview(self):
        """Open the live page in preview mode (works even in draft)."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/guides/{self.slug}?preview=1',
            'target': 'new',
        }
