from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

from .utils import is_safe_public_url

# Centralised list of (field, ICP key, default, type) tuples — single source
# of truth so default_get / get_settings / action_save can't drift.
_PARAMS = [
    # field name              ICP key                          default                                  type
    ('anthropic_api_key',     'uellow.sc.anthropic_key',       '',                                       str),
    ('default_warranty_text', 'uellow.sc.warranty',            'ضمان Uellow سنة كاملة — توصيل خلال 24 ساعة', str),
    ('default_price_variance','uellow.sc.price_variance',      20.0,                                     float),
    # Import: suggested sale price for NEW products when the sheet has no price
    # column — derived as cost + this markup %. 0 = leave price at 0.
    ('import_default_markup_pct','uellow.sc.import_markup',     30.0,                                     float),
    ('enable_ai_default',     'uellow.sc.enable_ai_default',   True,                                     bool),
    ('max_products_default',  'uellow.sc.max_products_default',500,                                      int),
    ('price_check_enabled',   'uellow.sc.price_check',         True,                                     bool),
    ('internal_price_watch',  'uellow.sc.internal_price_watch',True,                                     bool),
    ('price_check_sources',   'uellow.sc.price_sources',       '',                                       str),
    ('dead_stock_days',       'uellow.sc.dead_stock_days',     30,                                       int),
    ('dead_stock_alert_email','uellow.sc.dead_stock_email',    True,                                     bool),
    # Dynamic repricing (idea #28) — all percentages
    ('reprice_undercut_pct',  'uellow.sc.reprice_undercut',    2.0,                                      float),
    ('reprice_min_margin_pct','uellow.sc.reprice_min_margin',  10.0,                                     float),
    ('reprice_max_change_pct','uellow.sc.reprice_max_change',  15.0,                                     float),
    # Reorder forecast (idea #25)
    ('reorder_velocity_days', 'uellow.sc.reorder_velocity',    60,                                       int),
    ('reorder_lead_days',     'uellow.sc.reorder_lead',        14,                                       int),
    ('reorder_safety_days',   'uellow.sc.reorder_safety',      7,                                        int),
    # ── Per-feature on/off master switches (standing rule) ──
    ('feat_translation',      'uellow.sc.feat_translation',    True,                                     bool),
    ('feat_dead_stock',       'uellow.sc.feat_dead_stock',     True,                                     bool),
    ('feat_seasonality',      'uellow.sc.feat_seasonality',    True,                                     bool),
    ('feat_repricing',        'uellow.sc.feat_repricing',      True,                                     bool),
    ('feat_reorder',          'uellow.sc.feat_reorder',        True,                                     bool),
    ('feat_scorecard',        'uellow.sc.feat_scorecard',      True,                                     bool),
    ('feat_radar',            'uellow.sc.feat_radar',          True,                                     bool),
    ('feat_copilot',          'uellow.sc.feat_copilot',        True,                                     bool),
    ('feat_visual_intake',    'uellow.sc.feat_visual_intake',  True,                                     bool),
    ('feat_multimarket',      'uellow.sc.feat_multimarket',    True,                                     bool),
    ('feat_discovery',        'uellow.sc.feat_discovery',      True,                                     bool),
    ('discovery_match_threshold','uellow.sc.discovery_threshold',75,                                     int),
    ('discovery_max_items',   'uellow.sc.discovery_max_items', 100,                                      int),
    # ── Extra detailed knobs ──
    ('season_lookahead_months','uellow.sc.season_lookahead',   3,                                        int),
    ('scorecard_window_days', 'uellow.sc.scorecard_window',    180,                                      int),
    # ── Publish Studio (pre-publish workspace) ──
    ('feat_publish_studio',   'uellow.sc.feat_publish_studio', True,                                     bool),
    ('image_search_provider', 'uellow.sc.img_provider',        'none',                                   str),
    ('image_search_api_key',  'uellow.sc.img_key',             '',                                       str),
    ('image_search_cx',       'uellow.sc.img_cx',              '',                                       str),
    ('image_search_count',    'uellow.sc.img_count',           8,                                        int),
    ('publish_set_published', 'uellow.sc.publish_set_published',True,                                    bool),
    # Max images attached per product on import (1 main + the rest as gallery)
    ('import_images_per_product','uellow.sc.import_img_per_product',5,                                   int),
    # Daily safety-net cron: auto-translate any published product still missing
    # an Arabic name (catches manual/Beena/Publish-Studio products too).
    ('autotranslate_names',   'uellow.sc.autotranslate_names', True,                                     bool),
]


def _coerce(val, typ, default):
    """Parse an ICP string into the target python type, falling back to default.

    NB: ir.config_parameter.get_param returns ``False`` (not None) for a key
    that was never saved — without catching it, ``float(False)`` etc. would
    silently coerce unset settings to 0, ignoring their default.
    """
    if val is None or val is False or val == '':
        return default
    try:
        if typ is bool:
            return str(val).strip().lower() in ('1', 'true', 'yes', 'on')
        if typ is int:
            return int(val)
        if typ is float:
            return float(val)
        return str(val)
    except (TypeError, ValueError):
        return default


class ConnectorSettings(models.TransientModel):
    """
    Global Smart Connector settings stored via ir.config_parameter.

    Bugfix history:
      - A11: `default_get` ignored 4 fields and `action_save` ignored the
        same 4; they're now driven from `_PARAMS` so adding a setting needs
        one line, not three.
      - D11: form wouldn't close after save; we now return an action_close.
    """
    _name = 'uellow.connector.settings'
    _description = 'Smart Connector Settings'

    anthropic_api_key = fields.Char('Anthropic API Key')
    default_warranty_text = fields.Char(
        'Default Warranty Text',
        default='ضمان Uellow سنة كاملة — توصيل خلال 24 ساعة',
    )
    default_price_variance = fields.Float('Default Price Variance Limit (%)', default=20.0)
    import_default_markup_pct = fields.Float(
        'Import Default Markup (%)', default=30.0,
        help='When an imported sheet has no sale-price column, NEW products get '
             'a suggested sale price of cost + this markup %. Set 0 to leave it '
             'at 0 (edit manually before approving).')
    enable_ai_default = fields.Boolean('Enable AI by Default', default=True)
    max_products_default = fields.Integer('Default Max Products', default=500)

    # Price Intelligence settings
    price_check_enabled = fields.Boolean('Enable Price Monitoring', default=True)
    internal_price_watch = fields.Boolean('Internal Price Watch (history + indicators)', default=True)
    price_check_sources = fields.Char(
        'Comparison Sources (comma-separated URLs)',
    )

    # Dead stock settings
    dead_stock_days = fields.Integer('Dead-stock Alert Days', default=30)
    dead_stock_alert_email = fields.Boolean('Send Email Alert', default=True)

    # Dynamic repricing settings
    reprice_undercut_pct = fields.Float(
        'Undercut Competitor By (%)', default=2.0,
        help='Suggested price aims this far below the competitor.')
    reprice_min_margin_pct = fields.Float(
        'Minimum Margin (%)', default=10.0,
        help='Suggested price never drops below cost + this margin.')
    reprice_max_change_pct = fields.Float(
        'Max Single Change (%)', default=15.0,
        help='A suggestion never moves the price by more than this in one step.')

    # Reorder forecast settings
    reorder_velocity_days = fields.Integer(
        'Sales Velocity Window (days)', default=60,
        help='Look-back window used to measure each product\'s daily sales rate.')
    reorder_lead_days = fields.Integer(
        'Supplier Lead Time (days)', default=14,
        help='Days to restock — products running out within this window are urgent.')
    reorder_safety_days = fields.Integer(
        'Safety Stock (days)', default=7,
        help='Extra days of cover added to the suggested reorder quantity.')

    # ── Per-feature master switches ──
    feat_translation = fields.Boolean('Enable Catalog Translation', default=True)
    feat_dead_stock = fields.Boolean('Enable Dead-stock Monitor', default=True)
    feat_seasonality = fields.Boolean('Enable Seasonality Protection', default=True)
    feat_repricing = fields.Boolean('Enable Dynamic Repricing', default=True)
    feat_reorder = fields.Boolean('Enable Reorder Forecast', default=True)
    feat_scorecard = fields.Boolean('Enable Supplier Scorecard', default=True)
    feat_radar = fields.Boolean('Enable Competitor Radar', default=True)
    feat_copilot = fields.Boolean('Enable Ops Copilot', default=True)
    feat_visual_intake = fields.Boolean('Enable Visual (Image) Intake', default=True)
    feat_multimarket = fields.Boolean('Enable Multi-Market Pricing', default=True)
    feat_discovery = fields.Boolean('Enable Competitor Discovery', default=True)
    discovery_match_threshold = fields.Integer(
        'Discovery Match Threshold (%)', default=75,
        help='A competitor product scoring below this against our catalog is '
             'flagged as a NEW opportunity.')
    discovery_max_items = fields.Integer(
        'Discovery Max Items / Scan', default=100,
        help='Cap on competitor products parsed per scan.')

    # ── Extra detailed knobs ──
    season_lookahead_months = fields.Integer(
        'Seasonality Look-ahead (months)', default=3,
        help='Protect stock that historically sells within this many upcoming months.')
    scorecard_window_days = fields.Integer(
        'Scorecard Sales Window (days)', default=180,
        help='Sales look-back window used when scoring suppliers.')

    # ── Publish Studio ──
    feat_publish_studio = fields.Boolean('Enable Publish Studio', default=True)
    image_search_provider = fields.Selection([
        ('none',       'Disabled (manual / import image only)'),
        ('google_cse', 'Google Programmable Search (CSE)'),
        ('serpapi',    'SerpAPI (Google Images)'),
        ('bing',       'Bing Image Search'),
    ], string='Image Search Provider', default='none',
        help='Provider used by Publish Studio to find product photos on the web.')
    image_search_api_key = fields.Char('Image Search API Key')
    image_search_cx = fields.Char(
        'Google CSE Engine ID (cx)',
        help='Required only for the Google Programmable Search provider.')
    image_search_count = fields.Integer('Images per Search', default=8)
    import_images_per_product = fields.Integer(
        'Max Images per Product (Import)', default=5,
        help='When importing, attach at most this many images per product — '
             'the largest becomes the main image, the rest go to the gallery. '
             'الحد الأقصى لعدد الصور لكل منتج عند الاستيراد (الأكبر تكون الرئيسية والباقي معرض الصور).')
    publish_set_published = fields.Boolean(
        'Publish products live by default', default=True,
        help='When publishing from the Studio, set the product website-published.')
    autotranslate_names = fields.Boolean(
        'Auto-translate product names to Arabic (daily)', default=True,
        help='A daily job translates any published product that still has no '
             'Arabic name, so nothing stays English-only on the /ar storefront. '
             'مهمة يومية تترجم أسماء المنتجات المنشورة التي بلا اسم عربي.')

    @api.constrains('anthropic_api_key')
    def _check_api_key(self):
        for rec in self:
            k = (rec.anthropic_api_key or '').strip()
            if k and (not k.startswith('sk-ant-') or len(k) < 40):
                raise ValidationError(_(
                    'Invalid Anthropic API key — it must start with "sk-ant-".'))

    @api.constrains('price_check_sources')
    def _check_sources(self):
        for rec in self:
            if not rec.price_check_sources:
                continue
            for u in [s.strip() for s in rec.price_check_sources.split(',') if s.strip()]:
                ok, reason = is_safe_public_url(u)
                if not ok:
                    raise ValidationError(_(
                        'Invalid or unsafe source URL "%s": %s') % (u, reason))

    @api.model
    def default_get(self, fields_list):
        """Pre-fill form with current saved values."""
        res = super().default_get(fields_list)
        ICPSudo = self.env['ir.config_parameter'].sudo()
        for field_name, key, default, typ in _PARAMS:
            res[field_name] = _coerce(ICPSudo.get_param(key), typ, default)
        return res

    @api.model
    def get_settings(self):
        """Return current settings as a plain dict (used by other models)."""
        ICPSudo = self.env['ir.config_parameter'].sudo()
        return {
            field_name: _coerce(ICPSudo.get_param(key), typ, default)
            for field_name, key, default, typ in _PARAMS
        }

    def action_save(self):
        """Persist every setting to ir_config_parameter and close the dialog."""
        ICPSudo = self.env['ir.config_parameter'].sudo()
        for field_name, key, _default, typ in _PARAMS:
            val = getattr(self, field_name, None)
            if typ is bool:
                ICPSudo.set_param(key, '1' if val else '0')
            elif val is False or val is None:
                ICPSudo.set_param(key, '')
            else:
                ICPSudo.set_param(key, str(val))
        # Notify + close — D11 fix.
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Saved'),
                'message': _('Smart Connector settings saved.'),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
