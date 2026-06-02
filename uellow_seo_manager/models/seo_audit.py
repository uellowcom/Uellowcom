# -*- coding: utf-8 -*-
"""SEO Audit Engine — scores every product/category/page against 30 checks.

The audit is run on-demand via a wizard or scheduled cron. Each audit
creates a `uellow.seo.audit` master record and one `uellow.seo.audit.issue`
row per finding. The UI shows a dashboard with site-wide score and the
worst-scoring pages.
"""
import logging
import re

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


SEVERITY_WEIGHTS = {
    'critical': 10,
    'warning':  5,
    'info':     1,
}


class SEOAudit(models.Model):
    _name = 'uellow.seo.audit'
    _description = 'SEO Audit Run'
    _order = 'create_date desc'

    name = fields.Char(default=lambda s: _('Audit %s') % fields.Datetime.now())
    create_date = fields.Datetime(readonly=True)
    state = fields.Selection([
        ('running', 'Running'),
        ('done',    'Done'),
        ('error',   'Error'),
    ], default='running')

    # ── Aggregate metrics ─────────────────────────────────────────────
    score = fields.Float(string='Overall score', help='0-100')
    pages_audited = fields.Integer()
    issue_count_total    = fields.Integer()
    issue_count_critical = fields.Integer()
    issue_count_warning  = fields.Integer()
    issue_count_info     = fields.Integer()
    duration_seconds = fields.Float()

    # ── Findings ──────────────────────────────────────────────────────
    issue_ids = fields.One2many('uellow.seo.audit.issue', 'audit_id')

    # ── Scope ─────────────────────────────────────────────────────────
    scope_products  = fields.Boolean(default=True)
    scope_categories= fields.Boolean(default=True)
    scope_pages     = fields.Boolean(default=True)
    scope_limit     = fields.Integer(default=200,
        help='Cap on how many records to audit. 0 = no cap.')

    # ──────────────────────────────────────────────────────────────────
    # Run
    # ──────────────────────────────────────────────────────────────────
    def action_run(self):
        """Synchronous audit run — for small scopes use this. For full
        site scans, call as a scheduled job (cron) instead so the UI
        doesn't time out."""
        import time
        self.ensure_one()
        t0 = time.time()
        self.write({
            'state': 'running', 'pages_audited': 0,
            'issue_count_total': 0, 'issue_count_critical': 0,
            'issue_count_warning': 0, 'issue_count_info': 0,
            'score': 0.0,
        })
        # Wipe prior findings of this audit
        self.issue_ids.unlink()

        issues = []
        pages = 0
        try:
            if self.scope_products:
                Tmpl = self.env['product.template']
                dom = [('is_published','=',True), ('sale_ok','=',True)]
                limit = self.scope_limit or None
                for rec in Tmpl.search(dom, limit=limit):
                    issues.extend(self._audit_product(rec))
                    pages += 1
            if self.scope_categories:
                Cat = self.env['product.public.category']
                limit = self.scope_limit or None
                for rec in Cat.search([], limit=limit):
                    issues.extend(self._audit_category(rec))
                    pages += 1
            if self.scope_pages:
                Page = self.env.get('website.page')
                if Page is not None:
                    limit = self.scope_limit or None
                    for rec in Page.search([('is_published','=',True)], limit=limit):
                        issues.extend(self._audit_page(rec))
                        pages += 1
            # Homepage / global checks
            issues.extend(self._audit_global())
        except Exception as e:
            _logger.exception('SEO audit failed')
            self.state = 'error'
            return False

        # Persist findings
        crit = sum(1 for i in issues if i['severity'] == 'critical')
        warn = sum(1 for i in issues if i['severity'] == 'warning')
        info = sum(1 for i in issues if i['severity'] == 'info')
        total = crit + warn + info

        # Score: 100 starting, each issue deducts weight (max -100)
        deduction = min(100, sum(SEVERITY_WEIGHTS.get(i['severity'], 1) for i in issues))
        score = max(0, 100 - deduction)

        Issue = self.env['uellow.seo.audit.issue']
        for i in issues:
            Issue.create({**i, 'audit_id': self.id})

        self.write({
            'state': 'done',
            'pages_audited': pages,
            'issue_count_total': total,
            'issue_count_critical': crit,
            'issue_count_warning': warn,
            'issue_count_info': info,
            'score': score,
            'duration_seconds': time.time() - t0,
        })
        return True

    # ──────────────────────────────────────────────────────────────────
    # Per-record checks
    # ──────────────────────────────────────────────────────────────────
    def _audit_product(self, rec):
        out = []
        title = (rec.website_meta_title or rec.name or '').strip()
        desc  = (rec.website_meta_description or '').strip()
        if not title:
            out.append(self._mk('critical', 'meta_title_missing',
                'Product has no meta title', rec, 'product.template'))
        elif len(title) > 60:
            out.append(self._mk('warning', 'meta_title_long',
                f'Title is {len(title)} chars (max 60 recommended)', rec, 'product.template'))
        elif len(title) < 30:
            out.append(self._mk('info', 'meta_title_short',
                f'Title is only {len(title)} chars (30-60 ideal)', rec, 'product.template'))

        if not desc:
            out.append(self._mk('critical', 'meta_desc_missing',
                'Product has no meta description', rec, 'product.template'))
        elif len(desc) > 160:
            out.append(self._mk('warning', 'meta_desc_long',
                f'Description is {len(desc)} chars (max 160)', rec, 'product.template'))
        elif len(desc) < 70:
            out.append(self._mk('info', 'meta_desc_short',
                f'Description only {len(desc)} chars (70-160 ideal)', rec, 'product.template'))

        # Image alt — Odoo product images don't have alt by default,
        # we synthesise from product.name in the website template, but
        # flag if the product has no name at all.
        if not rec.name:
            out.append(self._mk('critical', 'no_name',
                'Product has no name at all', rec, 'product.template'))

        # Description body
        body = (rec.description_sale or rec.description or '').strip()
        if not body or len(body) < 100:
            out.append(self._mk('warning', 'thin_content',
                'Product page has <100 chars of description text',
                rec, 'product.template'))

        # Image presence
        if not rec.image_1920:
            out.append(self._mk('warning', 'no_image',
                'Product has no image — Google Shopping needs one',
                rec, 'product.template'))

        # Brand
        if not getattr(rec, 'brand_id', False):
            # Brand attribute fallback
            has_brand_attr = any(
                'brand' in (line.attribute_id.name or '').lower()
                or 'ماركة' in (line.attribute_id.name or '')
                for line in rec.attribute_line_ids
            )
            if not has_brand_attr:
                out.append(self._mk('info', 'no_brand',
                    'Product has no brand set — useful for Product JSON-LD',
                    rec, 'product.template'))

        # Price
        if not rec.list_price:
            out.append(self._mk('info', 'no_price',
                'Product has 0 price — schema.org Offer will be skipped',
                rec, 'product.template'))

        return out

    def _audit_category(self, rec):
        out = []
        # Categories have less SEO surface but we still check name + image
        if not rec.name:
            out.append(self._mk('critical', 'cat_no_name',
                'Category has no name', rec, 'product.public.category'))
        if not rec.image_1920:
            out.append(self._mk('info', 'cat_no_image',
                'Category has no banner image', rec, 'product.public.category'))
        # Number of products
        prod_count = self.env['product.template'].search_count([
            ('public_categ_ids', 'in', [rec.id]),
            ('is_published', '=', True),
        ])
        if prod_count < 3:
            out.append(self._mk('warning', 'cat_empty',
                f'Category has only {prod_count} published products',
                rec, 'product.public.category'))
        return out

    def _audit_page(self, rec):
        out = []
        view = rec.view_id
        if not view:
            return out
        title = (view.website_meta_title or view.name or '').strip()
        desc  = (view.website_meta_description or '').strip()
        if not title:
            out.append(self._mk('critical', 'page_meta_title_missing',
                'Page has no meta title', rec, 'website.page'))
        if not desc:
            out.append(self._mk('warning', 'page_meta_desc_missing',
                'Page has no meta description', rec, 'website.page'))
        return out

    def _audit_global(self):
        """Site-wide checks not tied to a record."""
        out = []
        Param = self.env['ir.config_parameter'].sudo()
        base = (Param.get_param('web.base.url') or '').strip()
        if not base or base == 'http://localhost:8069':
            out.append(self._mk_global('critical', 'base_url_local',
                'web.base.url is set to a local address — must be public domain'))
        if not base.startswith('https'):
            out.append(self._mk_global('warning', 'base_url_no_https',
                'web.base.url is not HTTPS — search engines penalize non-HTTPS sites'))

        # Robots.txt
        try:
            cfg = self.env['uellow.seo.config'].get_config()
            if not cfg.robots_txt:
                out.append(self._mk_global('warning', 'no_robots_txt',
                    'No robots.txt configured'))
        except Exception:
            pass

        # Sitemap
        try:
            count = self.env['website'].search_count([])
            if count == 0:
                out.append(self._mk_global('critical', 'no_website',
                    'No website record exists — sitemap empty'))
        except Exception:
            pass

        # SEO config Google Search Console
        try:
            cfg = self.env['uellow.seo.config'].get_config()
            if not getattr(cfg, 'gsc_verification', False):
                out.append(self._mk_global('info', 'no_gsc',
                    'No Google Search Console verification tag set'))
            if not getattr(cfg, 'facebook_app_id', False):
                out.append(self._mk_global('info', 'no_fb_app_id',
                    'No Facebook App ID configured — affects og: sharing'))
        except Exception:
            pass

        return out

    # ──────────────────────────────────────────────────────────────────
    def _mk(self, severity, code, message, rec, model):
        return {
            'severity': severity, 'code': code, 'message': message,
            'res_model': model, 'res_id': rec.id,
            'record_name': getattr(rec, 'display_name', rec.name if hasattr(rec, 'name') else str(rec.id)),
        }

    def _mk_global(self, severity, code, message):
        return {
            'severity': severity, 'code': code, 'message': message,
            'res_model': False, 'res_id': False,
            'record_name': _('(site-wide)'),
        }

    # ──────────────────────────────────────────────────────────────────
    # Dashboard helpers
    # ──────────────────────────────────────────────────────────────────
    def action_view_issues(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Issues — %s') % self.name,
            'res_model': 'uellow.seo.audit.issue',
            'view_mode': 'list,form',
            'domain': [('audit_id', '=', self.id)],
        }

    @api.model
    def latest_for_dashboard(self):
        """Return the most-recent finished audit, or None."""
        return self.search([('state', '=', 'done')], limit=1, order='create_date desc')
