"""Lightweight 301 redirect manager (F10).

Wraps Odoo's `website.rewrite` with a friendlier model + hit-count tracking,
so the marketing team can manage rename-induced redirects without leaving
the Smart Connector / SEO menus.
"""
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SEORedirect(models.Model):
    _name = 'uellow.seo.redirect'
    _description = 'SEO URL Redirect'
    _rec_name = 'source_url'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    source_url = fields.Char('Source URL', required=True, index=True,
        help='e.g. /old-page')
    target_url = fields.Char('Target URL', required=True,
        help='e.g. /new-page or full https://...')
    redirect_type = fields.Selection([
        ('301', '301 — Moved Permanently'),
        ('302', '302 — Found (Temporary)'),
        ('308', '308 — Permanent Redirect (preserves method)'),
    ], default='301', required=True)
    active = fields.Boolean(default=True)
    hit_count = fields.Integer('Hits', readonly=True, default=0)
    last_hit  = fields.Datetime('Last hit', readonly=True)
    notes     = fields.Char('Notes')

    _sql_constraints = [
        ('unique_source', 'UNIQUE(source_url)',
         'A redirect for this source URL already exists.'),
    ]

    @api.constrains('source_url', 'target_url')
    def _check_urls(self):
        for r in self:
            if not r.source_url.startswith('/'):
                raise ValidationError(_('Source URL must start with "/" (e.g. /old-page).'))
            if not (r.target_url.startswith('/')
                    or r.target_url.startswith('http://')
                    or r.target_url.startswith('https://')):
                raise ValidationError(_('Target URL must start with "/" or "http(s)://".'))
            if r.source_url == r.target_url:
                raise ValidationError(_('Source and target URLs cannot be the same.'))

    def record_hit(self):
        """Atomic counter bump — called by the http handler."""
        for r in self:
            self.env.cr.execute(
                'UPDATE uellow_seo_redirect '
                'SET hit_count = hit_count + 1, last_hit = NOW() '
                'WHERE id = %s',
                [r.id])
