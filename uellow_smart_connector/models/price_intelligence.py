"""Competitor price intelligence — fetches and compares each monitored URL."""
import json
import logging
import re

from odoo import models, fields, api, _

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
    _description = 'مراقبة أسعار المنافسين'
    _rec_name = 'product_id'
    _order = 'price_diff_pct desc'

    product_id = fields.Many2one(
        'product.template', required=True, ondelete='cascade', index=True,
        string='المنتج',
    )
    source_name = fields.Char('المصدر', required=True)
    source_url = fields.Char('رابط المنافس', required=True)
    our_price = fields.Float('سعرنا', related='product_id.list_price', store=True)
    competitor_price = fields.Float('سعر المنافس', readonly=True)
    competitor_currency = fields.Char('عملة المنافس', readonly=True)
    last_checked = fields.Datetime('آخر فحص', readonly=True)
    last_error = fields.Char('آخر خطأ', readonly=True)
    price_diff_pct = fields.Float('فرق السعر (%)', readonly=True, store=True)

    state = fields.Selection([
        ('ok',      'طبيعي'),
        ('cheaper', 'نحن أرخص'),
        ('pricier', 'نحن أغلى'),
        ('error',   'خطأ في الفحص'),
    ], default='ok', string='الحالة', index=True)

    alert_sent = fields.Boolean('تنبيه أُرسل', default=False)

    @api.model
    def cron_check_prices(self):
        """Daily cron: refresh competitor prices in batches.

        Was sequential blocking HTTP with no commits — a 200-URL queue
        meant ~67 minutes locked in one transaction. Now we commit per
        _CRON_CHUNK so a failure in row 150 doesn't roll back rows 1-149.
        """
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
        import requests
        try:
            resp = requests.get(
                self.source_url,
                headers={'User-Agent': 'Mozilla/5.0 (compatible; Uellow/1.0)'},
                timeout=_HTTP_TIMEOUT_S,
            )
            resp.raise_for_status()
        except Exception as e:
            self.state = 'error'
            self.last_error = str(e)[:240]
            self.last_checked = fields.Datetime.now()
            _logger.warning('Price check fetch failed for %s: %s', self.source_url, e)
            return

        price, currency = self._extract_price(resp.text)
        if price is None:
            self.state = 'error'
            self.last_error = _('تعذّر استخراج سعر من الصفحة (لا توجد JSON-LD أو OG tags).')
            self.last_checked = fields.Datetime.now()
            return

        our_currency = (self.env.company.currency_id.name or '').upper()
        comp_currency = (currency or our_currency).upper()
        if our_currency and comp_currency and our_currency != comp_currency:
            # Refuse to compare — would produce wildly wrong "diff %"
            self.state = 'error'
            self.last_error = _(
                'عملة المنافس (%s) لا تطابق عملتنا (%s) — تجاوز الفحص.'
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

    def action_check_now(self):
        for rec in self:
            rec._check_price()
