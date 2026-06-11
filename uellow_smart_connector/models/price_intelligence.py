"""Competitor price intelligence — fetches and compares each monitored URL."""
import json
import logging
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError

from .utils import is_safe_public_url

_logger = logging.getLogger(__name__)

# Knobs
_CRON_CHUNK = 50           # commit interval inside cron_check_prices
_HTTP_TIMEOUT_S = 15       # per-URL fetch ceiling
_DIFF_THRESHOLD_PCT = 5    # |diff| > this flips state away from 'ok'


class PriceIntelligence(models.Model):
    """
    Monitors competitor prices for products.
    Each record = one product monitored against one source URL.
    Cron runs daily to check current competitor price.
    """
    _name = 'uellow.price.intelligence'
    _description = 'Competitor Price Intelligence'
    _rec_name = 'product_id'
    _order = 'price_diff_pct desc'

    product_id = fields.Many2one(
        'product.template', required=True, ondelete='cascade', index=True,
        string='Product',
    )
    source_name = fields.Char('Source', required=True)
    source_url = fields.Char('Competitor URL', required=True)
    # v2.1 — NOT stored: a stored related re-wrote every monitored row each
    # time any product's list_price changed (N writes per price edit).
    our_price = fields.Float('Our Price', related='product_id.list_price', store=False)
    competitor_price = fields.Float('Competitor Price', readonly=True)
    competitor_currency = fields.Char('Competitor Currency', readonly=True)
    last_checked = fields.Datetime('Last Checked', readonly=True)
    last_error = fields.Char('Last Error', readonly=True)
    price_diff_pct = fields.Float('Price Diff (%)', readonly=True, store=True)

    state = fields.Selection([
        ('ok',      'Normal'),
        ('cheaper', 'We are cheaper'),
        ('pricier', 'We are pricier'),
        ('error',   'Check failed'),
    ], default='ok', string='Status', index=True)

    alert_sent = fields.Boolean('Alert Sent', default=False)

    # Dynamic repricing (idea #28) — suggestion is staged, never auto-applied.
    suggested_price = fields.Float('Suggested Price', readonly=True)
    reprice_note = fields.Char('Repricing Note', readonly=True)
    reprice_gain_pct = fields.Float('Potential Change (%)', readonly=True,
                                    help='Suggested price vs our current price.')

    # Competitor radar (idea #29) — availability tracking
    competitor_in_stock = fields.Boolean('Competitor In Stock', readonly=True, default=True)
    competitor_availability = fields.Char('Competitor Availability', readonly=True)
    opportunity = fields.Boolean(
        'Opportunity', readonly=True, default=False,
        help='Competitor is out of stock while we have it — chance to win the sale / raise price.')

    @api.model
    def cron_check_prices(self):
        """Daily cron: refresh competitor prices in batches.

        Was sequential blocking HTTP with no commits — a 200-URL queue
        meant ~67 minutes locked in one transaction. Now we commit per
        _CRON_CHUNK so a failure in row 150 doesn't roll back rows 1-149.
        """
        if not self.env['uellow.connector.settings'].get_settings().get('price_check_enabled'):
            return
        records = self.search([])
        total = len(records)
        for offset in range(0, total, _CRON_CHUNK):
            chunk = records[offset:offset + _CRON_CHUNK]
            for rec in chunk:
                rec._check_price()
            self.env.cr.commit()
            _logger.info('Smart Connector price-check: %d/%d done',
                         min(offset + _CRON_CHUNK, total), total)

    def _check_price(self):
        """Fetch competitor price.

        Uses JSON-LD `offers.price` first (reliable structured data) and
        falls back to OG meta tags. Regex over raw text was hopelessly
        noisy — it would pick up shipping prices, RRP, "from $X" etc.,
        and didn't even verify currency.
        """
        self.ensure_one()
        import time
        import requests
        # SSRF guard — never let a saved URL hit internal hosts.
        ok, reason = is_safe_public_url(self.source_url)
        if not ok:
            self.state = 'error'
            self.last_error = _('Unsafe URL rejected: %s') % reason
            self.last_checked = fields.Datetime.now()
            return
        # up to 2 attempts with a short backoff for transient network errors
        resp = None
        last_exc = None
        for attempt in range(2):
            try:
                resp = requests.get(
                    self.source_url,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; Uellow/1.0)'},
                    timeout=_HTTP_TIMEOUT_S,
                )
                resp.raise_for_status()
                break
            except Exception as e:
                last_exc = e
                resp = None
                if attempt == 0:
                    time.sleep(1.5)
        if resp is None:
            self.state = 'error'
            self.last_error = str(last_exc)[:240]
            self.last_checked = fields.Datetime.now()
            _logger.warning('Price check fetch failed for %s: %s', self.source_url, last_exc)
            return

        price, currency = self._extract_price(resp.text)
        if price is None:
            self.state = 'error'
            self.last_error = _('Could not extract a price from the page (no JSON-LD or OG tags).')
            self.last_checked = fields.Datetime.now()
            return

        our_currency = (self.env.company.currency_id.name or '').upper()
        comp_currency = (currency or our_currency).upper()
        if our_currency and comp_currency and our_currency != comp_currency:
            # Refuse to compare — would produce wildly wrong "diff %"
            self.state = 'error'
            self.last_error = _(
                'Competitor currency (%s) does not match ours (%s) — check skipped.'
            ) % (comp_currency, our_currency)
            self.competitor_price = price
            self.competitor_currency = comp_currency
            self.last_checked = fields.Datetime.now()
            return

        self.competitor_price = price
        self.competitor_currency = comp_currency
        self.last_error = False
        self.last_checked = fields.Datetime.now()
        self.alert_sent = False

        # competitor radar — availability + opportunity flag (gated)
        radar_on = self.env['uellow.connector.settings'].get_settings().get('feat_radar')
        avail = self._extract_availability(resp.text) if radar_on else None
        if avail is not None:
            self.competitor_availability = avail
            in_stock = 'outofstock' not in (avail or '').replace(' ', '').lower() \
                and 'soldout' not in (avail or '').replace(' ', '').lower()
            self.competitor_in_stock = in_stock
            self.opportunity = not in_stock
        else:
            self.competitor_availability = False
            self.competitor_in_stock = True
            self.opportunity = False

        if self.our_price > 0:
            diff = (price - self.our_price) / self.our_price * 100
            self.price_diff_pct = diff
            if diff < -_DIFF_THRESHOLD_PCT:
                self.state = 'cheaper'
            elif diff > _DIFF_THRESHOLD_PCT:
                self.state = 'pricier'
            else:
                self.state = 'ok'
        else:
            self.price_diff_pct = 0.0
            self.state = 'ok'

        self._compute_reprice()

    def _compute_reprice(self):
        """Suggest an optimal price: undercut the competitor, but never below
        the margin floor, and never move more than the max single change.

        Pure analysis — writes only the suggestion fields, NOT the live price.
        """
        self.ensure_one()
        s = self.env['uellow.connector.settings'].get_settings()
        comp = self.competitor_price or 0.0
        our = self.our_price or 0.0
        if not s.get('feat_repricing') or comp <= 0 or our <= 0:
            self.suggested_price = 0.0
            self.reprice_note = False
            self.reprice_gain_pct = 0.0
            return

        undercut = (s.get('reprice_undercut_pct') or 0.0) / 100.0
        min_margin = (s.get('reprice_min_margin_pct') or 0.0) / 100.0
        max_change = (s.get('reprice_max_change_pct') or 0.0) / 100.0

        cost = self.product_id.standard_price or 0.0
        floor = cost * (1 + min_margin) if cost else 0.0

        target = comp * (1 - undercut)          # aim just under the competitor
        note_bits = [_('undercut %s by %.0f%%') % (self.source_name or 'competitor',
                                                   undercut * 100)]
        if floor and target < floor:
            target = floor
            note_bits.append(_('raised to margin floor'))
        # clamp to ±max_change of our current price
        if max_change:
            hi, lo = our * (1 + max_change), our * (1 - max_change)
            if target > hi:
                target = hi
                note_bits.append(_('capped at +%.0f%%') % (max_change * 100))
            elif target < lo:
                target = lo
                note_bits.append(_('capped at -%.0f%%') % (max_change * 100))

        target = round(target, 3)
        change = (target - our) / our * 100 if our else 0.0
        # only surface a suggestion that meaningfully moves the price
        if abs(change) < 1.0:
            self.suggested_price = 0.0
            self.reprice_note = _('Price already optimal')
            self.reprice_gain_pct = 0.0
            return
        self.suggested_price = target
        self.reprice_gain_pct = change
        self.reprice_note = ' · '.join(b for b in note_bits if b)

    @staticmethod
    def _extract_price(html):
        """Return (price_float, currency_iso) parsed from the page, or (None, None).

        Order of preference: JSON-LD → OG meta → None.
        """
        # 1) JSON-LD
        for match in re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL | re.IGNORECASE,
        ):
            try:
                data = json.loads(match)
            except (json.JSONDecodeError, ValueError):
                continue
            candidates = data if isinstance(data, list) else (
                data.get('@graph', [data]) if isinstance(data, dict) else []
            )
            for item in candidates:
                if not isinstance(item, dict) or item.get('@type') != 'Product':
                    continue
                offer = item.get('offers') or {}
                if isinstance(offer, list):
                    offer = offer[0] if offer else {}
                try:
                    return (float(offer.get('price') or 0),
                            (offer.get('priceCurrency') or '').upper() or None)
                except (TypeError, ValueError):
                    continue

        # 2) OG meta tags
        m_price = re.search(
            r'<meta[^>]+property=["\']product:price:amount["\'][^>]+content=["\']([\d.]+)["\']',
            html, re.IGNORECASE,
        )
        m_curr = re.search(
            r'<meta[^>]+property=["\']product:price:currency["\'][^>]+content=["\']([A-Z]{3})["\']',
            html, re.IGNORECASE,
        )
        if m_price:
            try:
                return float(m_price.group(1)), (m_curr.group(1).upper() if m_curr else None)
            except (TypeError, ValueError):
                pass

        return None, None

    @staticmethod
    def _extract_availability(html):
        """Return a normalised availability string (e.g. 'InStock'), or None.

        Reads schema.org JSON-LD offers.availability first, then OG meta.
        """
        for match in re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL | re.IGNORECASE,
        ):
            try:
                data = json.loads(match)
            except (json.JSONDecodeError, ValueError):
                continue
            candidates = data if isinstance(data, list) else (
                data.get('@graph', [data]) if isinstance(data, dict) else [])
            for item in candidates:
                if not isinstance(item, dict) or item.get('@type') != 'Product':
                    continue
                offer = item.get('offers') or {}
                if isinstance(offer, list):
                    offer = offer[0] if offer else {}
                avail = offer.get('availability') if isinstance(offer, dict) else None
                if avail:
                    # 'http://schema.org/InStock' → 'InStock'
                    return str(avail).rstrip('/').split('/')[-1]
        m = re.search(
            r'<meta[^>]+property=["\']product:availability["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    def action_check_now(self):
        for rec in self:
            rec._check_price()

    def action_apply_reprice(self):
        """Apply the staged suggestion to the product's list price (deliberate).

        Guarded: needs a positive suggestion that differs from the current
        price. The change is reversible by the manager and gets picked up by
        the price-history snapshot.
        """
        for rec in self:
            sp = rec.suggested_price or 0.0
            if sp <= 0:
                raise UserError(_('No price suggestion to apply for %s.')
                                % (rec.product_id.display_name))
            rec.product_id.list_price = sp
            rec.reprice_note = _('Applied: %.3f') % sp
            rec.suggested_price = 0.0
            rec.reprice_gain_pct = 0.0
        return True
