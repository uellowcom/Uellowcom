"""Competitor product discovery / new-SKU crawl (idea #29 extension).

Crawls a competitor listing/category page, extracts the products it exposes
via schema.org structured data, fuzzy-matches each against our catalog, and
flags the ones we DON'T sell as expansion opportunities. Bounded (max items),
SSRF-guarded, suggestion-only (never auto-creates products), gated by the
feat_discovery switch.
"""
import json
import logging
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from .utils import is_safe_public_url

_logger = logging.getLogger(__name__)

_HTTP_TIMEOUT_S = 20


class CompetitorSource(models.Model):
    _name = 'uellow.sc.competitor.source'
    _description = 'Competitor Crawl Source'
    _order = 'name'

    name = fields.Char('Competitor', required=True)
    url = fields.Char('Listing / Category URL', required=True)
    active = fields.Boolean(default=True)
    last_run = fields.Datetime('Last Scan', readonly=True)
    last_found = fields.Integer('Found (last scan)', readonly=True)
    last_new = fields.Integer('New (last scan)', readonly=True)
    last_error = fields.Char('Last Error', readonly=True)
    discovery_ids = fields.One2many(
        'uellow.sc.discovery', 'source_id', string='Discoveries')
    discovery_count = fields.Integer(compute='_compute_counts')
    new_count = fields.Integer(compute='_compute_counts')

    @api.depends('discovery_ids.state')
    def _compute_counts(self):
        for s in self:
            s.discovery_count = len(s.discovery_ids)
            s.new_count = len(s.discovery_ids.filtered(lambda d: d.state == 'new'))

    def action_scan_now(self):
        for s in self:
            s._scan()
        return True

    def _scan(self):
        self.ensure_one()
        settings = self.env['uellow.connector.settings'].get_settings()
        if not settings.get('feat_discovery'):
            raise UserError(_('Competitor Discovery is disabled in Settings.'))
        ok, reason = is_safe_public_url(self.url)
        if not ok:
            self.write({'last_error': _('Unsafe URL: %s') % reason,
                        'last_run': fields.Datetime.now()})
            return

        import requests
        try:
            resp = requests.get(
                self.url, timeout=_HTTP_TIMEOUT_S,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Uellow/1.0)'})
            resp.raise_for_status()
        except Exception as e:                       # noqa: BLE001
            self.write({'last_error': str(e)[:240], 'last_run': fields.Datetime.now()})
            return

        cap = max(1, int(settings.get('discovery_max_items') or 100))
        listings = self._extract_listings(resp.text)[:cap]
        threshold = int(settings.get('discovery_match_threshold') or 75)

        # candidate catalog names for fuzzy matching
        our = self.env['product.template'].search(
            [('sale_ok', '=', True), ('active', '=', True),
             ('is_dropship', '=', False)])  # exclude Uellow World products
        names = our.mapped('name')
        try:
            from thefuzz import process, fuzz
            have_fuzz = True
        except ImportError:
            have_fuzz = False

        existing_titles = set(self.discovery_ids.mapped('title'))
        found, new = 0, 0
        to_create = []
        for item in listings:
            title = (item.get('title') or '').strip()
            if not title or title in existing_titles:
                continue
            found += 1
            score, match_id = 0, False
            if have_fuzz and names:
                best = process.extractOne(title, names, scorer=fuzz.token_set_ratio)
                if best:
                    score = best[1]
                    match = our.filtered(lambda p: p.name == best[0])[:1]
                    match_id = match.id if match else False
            state = 'have' if score >= threshold else 'new'
            if state == 'new':
                new += 1
            to_create.append({
                'source_id': self.id, 'title': title[:300],
                'url': (item.get('url') or '')[:500],
                'price': item.get('price') or 0.0,
                'match_score': score, 'our_product_id': match_id, 'state': state,
            })
            existing_titles.add(title)
        if to_create:
            self.env['uellow.sc.discovery'].create(to_create)
        self.write({'last_run': fields.Datetime.now(), 'last_error': False,
                    'last_found': found, 'last_new': new})
        self.env.cr.commit()

    @staticmethod
    def _extract_listings(html):
        """Pull product entries from schema.org JSON-LD (Product / ItemList)."""
        out = []

        def walk(node):
            if isinstance(node, dict):
                t = node.get('@type')
                types = t if isinstance(t, list) else [t]
                if 'Product' in types and node.get('name'):
                    offer = node.get('offers') or {}
                    if isinstance(offer, list):
                        offer = offer[0] if offer else {}
                    price = 0.0
                    try:
                        price = float(offer.get('price') or 0) if isinstance(offer, dict) else 0.0
                    except (TypeError, ValueError):
                        price = 0.0
                    out.append({'title': str(node.get('name')),
                                'url': str(node.get('url') or ''), 'price': price})
                # listing pages: ListItem entries that carry a bare name/url
                elif 'ListItem' in types and node.get('name') and not node.get('item'):
                    out.append({'title': str(node.get('name')),
                                'url': str(node.get('url') or ''), 'price': 0.0})
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        for match in re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL | re.IGNORECASE):
            try:
                walk(json.loads(match))
            except (json.JSONDecodeError, ValueError):
                continue
        return out

    @api.model
    def cron_crawl_competitors(self):
        if not self.env['uellow.connector.settings'].get_settings().get('feat_discovery'):
            return
        for s in self.search([('active', '=', True)]):
            try:
                s._scan()
            except Exception as e:                   # noqa: BLE001
                _logger.warning('Competitor crawl failed for %s: %s', s.name, e)


class Discovery(models.Model):
    _name = 'uellow.sc.discovery'
    _description = 'Competitor Product Discovery'
    _order = 'create_date desc'

    source_id = fields.Many2one('uellow.sc.competitor.source', ondelete='cascade',
                                string='Competitor', index=True)
    title = fields.Char('Product Title', required=True)
    url = fields.Char('URL')
    price = fields.Float('Competitor Price')
    match_score = fields.Integer('Best Match %')
    our_product_id = fields.Many2one('product.template', string='Closest Match')
    state = fields.Selection([
        ('new',     'New opportunity'),
        ('have',    'Already sell'),
        ('ignored', 'Ignored'),
    ], default='new', index=True)

    def action_ignore(self):
        for r in self:
            r.state = 'ignored'
