import logging
import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ImportJob(models.Model):
    """
    Core record for every import operation.
    Supports: URL scraping, Excel/PDF file upload.
    Lifecycle: draft → processing → review → done | rolled_back
    """
    _name = 'uellow.import.job'
    _description = 'عملية استيراد المنتجات'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char('رقم العملية', readonly=True, default='جديد', copy=False)
    job_type = fields.Selection([
        ('url',  'URL Import — استيراد من رابط'),
        ('file', 'File Update — تحديث ملف'),
    ], required=True, default='url', string='نوع العملية')

    state = fields.Selection([
        ('draft',       'مسودة'),
        ('processing',  'جاري التنفيذ'),
        ('review',      'مراجعة'),
        ('done',        'مكتملة'),
        ('rolled_back', 'تراجع'),
        ('error',       'خطأ'),
    ], default='draft', string='الحالة', tracking=True, index=True)

    # Source
    source_url = fields.Char('رابط المصدر')
    attachment_id = fields.Many2one(
        'ir.attachment', string='الملف المرفوع (Excel/PDF)',
        ondelete='set null',
    )

    # AI options
    enable_translation = fields.Boolean('ترجمة عربي/إنجليزي', default=True)
    enable_seo = fields.Boolean('كتابة وصف SEO', default=True)
    warranty_text = fields.Char(
        'نص ضمان Uellow',
        default='ضمان Uellow سنة كاملة — توصيل خلال 24 ساعة',
    )

    # Safety
    price_variance_limit = fields.Float(
        'حد تغير السعر (%)', default=20.0,
        help='رفض تلقائي إذا تجاوز تغيير السعر هذه النسبة',
    )
    max_products_per_run = fields.Integer('أقصى عدد منتجات', default=500)

    # Results
    imported_product_ids = fields.Many2many(
        'product.template', string='المنتجات المستوردة',
    )
    line_ids = fields.One2many(
        'uellow.import.job.line', 'job_id', string='السطور',
    )

    total_lines = fields.Integer(compute='_compute_stats', string='الإجمالي')
    new_count = fields.Integer(compute='_compute_stats', string='جديد')
    update_count = fields.Integer(compute='_compute_stats', string='تحديث')
    warning_count = fields.Integer(compute='_compute_stats', string='تحذيرات')
    approved_count = fields.Integer(compute='_compute_stats', string='معتمد')

    # Rollback snapshot — stores original product values as JSON
    rollback_data = fields.Text('بيانات الاسترجاع (JSON)', readonly=True)
    error_message = fields.Text('رسالة الخطأ', readonly=True)

    @api.depends('line_ids.line_state')
    def _compute_stats(self):
        for job in self:
            lines = job.line_ids
            job.total_lines = len(lines)
            job.new_count = len(lines.filtered(lambda l: l.product_action == 'new'))
            job.update_count = len(lines.filtered(lambda l: l.product_action == 'update'))
            job.warning_count = len(lines.filtered(lambda l: l.has_warning))
            job.approved_count = len(lines.filtered(lambda l: l.line_state == 'approved'))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'جديد') == 'جديد':
                v['name'] = self.env['ir.sequence'].next_by_code('uellow.import.job') or 'جديد'
        return super().create(vals_list)

    # ── Actions ─────────────────────────────────────────

    def action_run(self):
        """Validate then queue the import job."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('يمكن تشغيل المسودات فقط.'))
        if self.job_type == 'url' and not self.source_url:
            raise UserError(_('أدخل رابط المصدر.'))
        if self.job_type == 'file' and not self.attachment_id:
            raise UserError(_('ارفع ملفاً.'))
        self.state = 'processing'
        # Run synchronously — upgrade to queue_job later if needed
        self._process_job()

    def _process_job(self):
        """Main processing: scrape/parse → fuzzy match → AI enrich → create lines."""
        try:
            if self.job_type == 'url':
                raw_products = self._scrape_url(self.source_url)
            else:
                raw_products = self._parse_file(self.attachment_id)

            # Safety cap
            raw_products = raw_products[:self.max_products_per_run]

            # Fuzzy match against existing products
            lines_data = self._fuzzy_match_products(raw_products)

            # AI enrichment
            if self.enable_translation or self.enable_seo:
                lines_data = self._ai_enrich(lines_data)

            # Create lines
            for ld in lines_data:
                self.env['uellow.import.job.line'].create({
                    'job_id': self.id,
                    **ld,
                })

            self.state = 'review'
            self.message_post(body=_(
                'تمت المعالجة. %d منتج جاهز للمراجعة.') % len(lines_data))
        except Exception as e:
            self.state = 'error'
            self.error_message = str(e)
            _logger.exception('Smart Connector job %s failed', self.name)

    def _scrape_url(self, url):
        """Scrape product data from a URL using requests + basic parsing."""
        import requests
        from html.parser import HTMLParser

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; Uellow/1.0)'}
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            raise UserError(_('فشل الاتصال بالرابط: %s') % str(e))

        # Basic extraction — in production replace with site-specific scrapers
        products = []
        # Try to extract structured data (JSON-LD)
        import re
        json_ld_matches = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            resp.text, re.DOTALL | re.IGNORECASE)
        for match in json_ld_matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and data.get('@type') == 'Product':
                    products.append({
                        'name_en': data.get('name', ''),
                        'description_en': data.get('description', ''),
                        'price': float(data.get('offers', {}).get('price', 0) or 0),
                        'sku': data.get('sku', ''),
                        'image_url': data.get('image', '') if isinstance(data.get('image'), str) else '',
                        'source_url': url,
                    })
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

        if not products:
            # Fallback: return a placeholder so the job doesn't fail silently
            products.append({
                'name_en': f'Product from {url[:50]}',
                'description_en': '',
                'price': 0.0,
                'sku': '',
                'image_url': '',
                'source_url': url,
            })
        return products

    def _parse_file(self, attachment):
        """Parse Excel or PDF attachment into product dicts."""
        import base64
        import io

        if not attachment:
            return []

        content = base64.b64decode(attachment.datas)
        fname = (attachment.name or '').lower()

        if fname.endswith(('.xlsx', '.xls')):
            return self._parse_excel(content)
        elif fname.endswith('.pdf'):
            return self._parse_pdf(content)
        else:
            raise UserError(_('صيغة الملف غير مدعومة. يُقبل: xlsx, xls, pdf'))

    def _parse_excel(self, content):
        import io
        try:
            import openpyxl
        except ImportError:
            raise UserError(_('مكتبة openpyxl غير مثبّتة. نفّذ: pip install openpyxl'))

        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []

        headers = [str(c or '').lower().strip() for c in rows[0]]
        products = []
        for row in rows[1:]:
            if not any(row):
                continue
            d = dict(zip(headers, row))
            products.append({
                'name_en': str(d.get('name', d.get('product', d.get('item', ''))) or ''),
                'description_en': str(d.get('description', d.get('desc', '')) or ''),
                'price': float(d.get('price', d.get('sale_price', 0)) or 0),
                'sku': str(d.get('sku', d.get('barcode', d.get('code', ''))) or ''),
                'qty': int(d.get('qty', d.get('quantity', d.get('stock', 0))) or 0),
                'source_url': '',
            })
        return products

    def _parse_pdf(self, content):
        """Basic PDF text extraction — override with pdfplumber in production."""
        try:
            import pdfplumber
            import io
            products = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ''
                    # Very basic: each line might be a product
                    for line in text.split('\n'):
                        line = line.strip()
                        if len(line) > 5:
                            products.append({
                                'name_en': line[:200],
                                'description_en': '',
                                'price': 0.0,
                                'sku': '',
                                'source_url': '',
                            })
            return products[:100]
        except ImportError:
            raise UserError(_('مكتبة pdfplumber غير مثبّتة. نفّذ: pip install pdfplumber'))

    def _fuzzy_match_products(self, raw_products):
        """Match raw products against existing product.template using thefuzz."""
        try:
            from thefuzz import fuzz
        except ImportError:
            _logger.warning('thefuzz not installed, skipping fuzzy match')
            # Return as-is without matching
            return [{
                'name_en': p.get('name_en', ''),
                'name_ar': '',
                'description_en': p.get('description_en', ''),
                'description_ar': '',
                'new_price': p.get('price', 0.0),
                'new_qty': p.get('qty', 0),
                'source_sku': p.get('sku', ''),
                'source_url': p.get('source_url', ''),
                'product_action': 'new',
                'match_score': 0,
                'existing_product_id': False,
                'has_warning': False,
                'ai_enriched': False,
            } for p in raw_products]

        existing = self.env['product.template'].search([('active', '=', True)])
        existing_names = [(p.id, p.name or '') for p in existing]

        lines = []
        for p in raw_products:
            raw_name = p.get('name_en', '')
            best_score = 0
            best_product_id = False

            if raw_name and existing_names:
                for pid, pname in existing_names:
                    score = fuzz.token_sort_ratio(raw_name.lower(), pname.lower())
                    if score > best_score:
                        best_score = score
                        best_product_id = pid

            action = 'update' if best_score >= 80 else 'new'
            has_warning = False
            existing_price = 0.0

            if action == 'update' and best_product_id:
                existing_prod = self.env['product.template'].browse(best_product_id)
                existing_price = existing_prod.list_price
                new_price = p.get('price', 0.0)
                if existing_price > 0 and new_price > 0:
                    change_pct = abs(new_price - existing_price) / existing_price * 100
                    if change_pct > self.price_variance_limit:
                        has_warning = True

            lines.append({
                'name_en': raw_name,
                'name_ar': '',
                'description_en': p.get('description_en', ''),
                'description_ar': '',
                'new_price': p.get('price', 0.0),
                'old_price': existing_price,
                'new_qty': p.get('qty', 0),
                'source_sku': p.get('sku', ''),
                'source_url': p.get('source_url', ''),
                'product_action': action,
                'match_score': best_score,
                'existing_product_id': best_product_id if action == 'update' else False,
                'has_warning': has_warning,
                'ai_enriched': False,
            })
        return lines

    def _ai_enrich(self, lines_data):
        """Translate and generate SEO descriptions using Claude AI."""
        settings = self.env['uellow.connector.settings'].get_settings()
        api_key = settings.get('anthropic_api_key', '')
        if not api_key:
            _logger.warning('No Anthropic API key configured, skipping AI enrichment')
            return lines_data

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            _logger.warning('anthropic package not installed')
            return lines_data

        for line in lines_data:
            if not line.get('name_en'):
                continue
            try:
                prompt = f"""You are a product content specialist for Uellow, a Kuwaiti e-commerce platform.

Product name (English): {line['name_en']}
Description (English): {line.get('description_en', '')}

Tasks:
1. Translate the product name to Arabic (Gulf dialect, natural marketing language)
2. Write an Arabic product description (50-100 words, marketing style, include key features)
3. Write an English SEO description (50-80 words, include keywords)
4. Append this warranty text to both descriptions: "{self.warranty_text}"

Respond in JSON format:
{{
  "name_ar": "...",
  "description_ar": "...",
  "description_en_seo": "..."
}}"""

                msg = client.messages.create(
                    model='claude-sonnet-4-20250514',
                    max_tokens=500,
                    messages=[{'role': 'user', 'content': prompt}],
                )
                text = msg.content[0].text
                # Strip markdown code fences if present
                import re
                text = re.sub(r'^```json\s*', '', text.strip())
                text = re.sub(r'\s*```$', '', text)
                result = json.loads(text)
                line['name_ar'] = result.get('name_ar', '')
                line['description_ar'] = result.get('description_ar', '')
                line['description_en'] = result.get('description_en_seo', line.get('description_en', ''))
                line['ai_enriched'] = True
            except Exception as e:
                _logger.warning('AI enrichment failed for "%s": %s', line.get('name_en'), e)

        return lines_data

    def action_open_review(self):
        """Open review wizard for this job."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'مراجعة — {self.name}',
            'res_model': 'uellow.import.review.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_job_id': self.id},
        }

    def action_rollback(self):
        """Restore products to their pre-import state using rollback_data."""
        self.ensure_one()
        if not self.rollback_data:
            raise UserError(_('لا توجد بيانات استرجاع لهذه العملية.'))
        if self.state != 'done':
            raise UserError(_('يمكن التراجع عن العمليات المكتملة فقط.'))

        try:
            data = json.loads(self.rollback_data)
            for product_id, vals in data.items():
                product = self.env['product.template'].browse(int(product_id))
                if product.exists():
                    product.write(vals)
            self.state = 'rolled_back'
            self.message_post(body=_('تم التراجع عن العملية واستعادة البيانات الأصلية.'))
        except Exception as e:
            raise UserError(_('فشل التراجع: %s') % str(e))
