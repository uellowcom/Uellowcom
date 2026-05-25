import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


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
    last_checked = fields.Datetime('آخر فحص', readonly=True)
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
        """Called by daily cron to refresh competitor prices."""
        records = self.search([])
        for rec in records:
            rec._check_price()

    def _check_price(self):
        """Fetch competitor price from source_url."""
        import requests, re
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; Uellow/1.0)'}
            resp = requests.get(self.source_url, headers=headers, timeout=20)
            # Try to find price in page — basic regex approach
            # In production: site-specific extractors
            price_matches = re.findall(
                r'(?:price|سعر)["\s:]*(\d+\.?\d*)', resp.text, re.IGNORECASE)
            if price_matches:
                comp_price = float(price_matches[0])
                self.competitor_price = comp_price
                if self.our_price > 0:
                    diff = (comp_price - self.our_price) / self.our_price * 100
                    self.price_diff_pct = diff
                    self.state = 'cheaper' if diff < -5 else ('pricier' if diff > 5 else 'ok')
            self.last_checked = fields.Datetime.now()
            self.alert_sent = False
        except Exception as e:
            self.state = 'error'
            _logger.warning('Price check failed for %s: %s', self.source_url, e)

    def action_check_now(self):
        for rec in self:
            rec._check_price()
