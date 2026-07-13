# -*- coding: utf-8 -*-
"""dropship.provider — one record per dropshipping provider (AliExpress, CJ, ...).

Holds credentials, routing (which countries/categories this provider serves),
and the pricing markup. The core resolves an adapter via ``self._adapter()``.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..adapters import base as adapter_base

_logger = logging.getLogger(__name__)


class DropshipProvider(models.Model):
    _name = 'dropship.provider'
    _description = 'Dropshipping Provider'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Selection(
        selection='_selection_code', required=True, default='manual',
        help="Which adapter serves this provider.")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    is_primary = fields.Boolean(
        string="Primary", help="Preferred provider when several match a route.")
    fallback_provider_id = fields.Many2one(
        'dropship.provider', string="Fallback",
        help="Used automatically when this provider fails or returns a poor result.")

    # --- credentials (generic + AliExpress OAuth) --------------------- #
    app_key = fields.Char(string="App Key")
    app_secret = fields.Char(string="App Secret")
    access_token = fields.Char(string="Access Token")
    refresh_token = fields.Char(string="Refresh Token")
    token_expiry = fields.Datetime(string="Token Expires")
    redirect_uri = fields.Char(
        string="OAuth Redirect URI",
        help="Callback registered on the provider console; receives ?code=...")
    endpoint = fields.Char(
        string="API Gateway", default="https://api-sg.aliexpress.com/sync")

    # --- routing + pricing ------------------------------------------- #
    country_ids = fields.Many2many(
        'res.country', string="Ships To",
        help="Leave empty to serve all countries.")
    category_routing = fields.Char(
        string="Category Routing",
        help="Comma-separated provider category ids this provider is preferred for.")
    feed_name = fields.Char(
        string="Feed Name",
        help="AliExpress promo feed to import from (see action_list_feeds).")
    markup_percent = fields.Float(
        string="Markup %", default=0.0,
        help="Added on top of landed cost for this provider (overrides global).")
    currency = fields.Char(default="USD")
    default_country = fields.Char(default="KW")
    manual_shipping_cost = fields.Float(string="Manual Shipping Cost", default=0.0)

    # --- stats -------------------------------------------------------- #
    product_count = fields.Integer(compute='_compute_product_count')
    last_sync = fields.Datetime(readonly=True)
    state = fields.Selection([
        ('draft', 'Not Connected'),
        ('connected', 'Connected'),
        ('error', 'Error'),
    ], default='draft', readonly=True)
    status_message = fields.Char(readonly=True)

    @api.model
    def _selection_code(self):
        # driven by the adapter registry so new adapters appear automatically
        labels = {'manual': 'Manual / Curated', 'aliexpress': 'AliExpress DS',
                  'cj': 'CJ Dropshipping', 'spocket': 'Spocket'}
        codes = adapter_base.registered_codes()
        return [(c, labels.get(c, c.title())) for c in codes]

    def _compute_product_count(self):
        counts = dict(self.env['dropship.product']._read_group(
            [('provider_id', 'in', self.ids)], ['provider_id'], ['__count']))
        for p in self:
            p.product_count = counts.get(p, 0)

    # --- adapter access ---------------------------------------------- #
    def _adapter(self):
        """Return an adapter instance for this provider."""
        self.ensure_one()
        return adapter_base.get_adapter(self)

    def _feed_list(self):
        """Parse feed_name into a list (supports comma / newline separated)."""
        self.ensure_one()
        raw = (self.feed_name or '').replace('\n', ',')
        return [f.strip() for f in raw.split(',') if f.strip()]

    # --- UI actions --------------------------------------------------- #
    def action_authorize_url(self):
        """Show the OAuth consent URL to open once (AliExpress etc.)."""
        self.ensure_one()
        adapter = self._adapter()
        url = getattr(adapter, 'authorize_url', lambda: None)()
        if not url:
            raise UserError(_("This provider has no OAuth authorize step."))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_exchange_code(self):
        """Wizard-less exchange: expects code in status_message field temporarily.

        In practice the redirect handler stores the code; this button lets an
        admin paste a code into ``status_message`` and exchange it.
        """
        self.ensure_one()
        code = (self.status_message or '').strip()
        if not code:
            raise UserError(_("Paste the OAuth ?code=... value into the status field first."))
        adapter = self._adapter()
        getattr(adapter, 'exchange_code')(code)
        self.write({'state': 'connected', 'status_message': 'Token stored.'})
        return True

    def action_list_feeds(self):
        """Fetch available promo feeds and show them (AliExpress)."""
        self.ensure_one()
        adapter = self._adapter()
        if not hasattr(adapter, 'get_feed_names'):
            raise UserError(_("This provider has no feed list."))
        feeds = adapter.get_feed_names()
        top = sorted(feeds, key=lambda f: -(f.get('count') or 0))[:15]
        lines = "\n".join("• %s  (%s products)" % (f['name'], f.get('count')) for f in top)
        msg = _("%s feeds available. Top by size:\n%s") % (len(feeds), lines)
        return self._notify(msg, kind='info')

    def action_test_connection(self):
        self.ensure_one()
        try:
            self._adapter().authenticate()
            self.write({'state': 'connected', 'status_message': _("Connection OK.")})
        except Exception as e:  # noqa: BLE001 - surface any adapter error to the admin
            self.write({'state': 'error', 'status_message': str(e)})
            raise UserError(_("Connection failed: %s") % e)
        return self._notify(_("AliExpress connection OK."))

    def _notify(self, msg, kind='success'):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'message': msg, 'type': kind, 'sticky': False},
        }

    # --- routing resolution ------------------------------------------ #
    @api.model
    def _resolve(self, country_code=None, category=None):
        """Pick the best provider for a given country/category (+ fallbacks)."""
        domain = [('active', '=', True), ('state', '=', 'connected')]
        providers = self.search(domain, order='is_primary desc, sequence, id')
        if country_code:
            providers = providers.filtered(
                lambda p: not p.country_ids or country_code in p.country_ids.mapped('code'))
        if category:
            providers = providers.filtered(
                lambda p: not p.category_routing or category in [c.strip() for c in p.category_routing.split(',')]
            ) or providers
        return providers
