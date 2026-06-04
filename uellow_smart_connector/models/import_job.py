import base64
import io
import json
import logging
import re

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Tunables — kept module-local so they're easy to spot, not in settings.
_AI_TIMEOUT_S = 30           # per-line AI call ceiling
_FUZZY_CANDIDATE_CAP = 200   # max products fuzz-scored per row (perf)
_FUZZY_THRESHOLD = 80        # match score that promotes to 'update'


class ImportJob(models.Model):
    """
    Core record for every import operation.
    Supports: URL scraping, Excel/PDF file upload.
    Lifecycle: draft → processing → review → done | rolled_back
    """
    _name = 'uellow.import.job'
    _description = 'Product Import Job'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'id desc'

    name = fields.Char('Job Reference', readonly=True, default='New', copy=False)
    job_type = fields.Selection([
        ('url',  'URL Import'),
        ('file', 'File Update'),
    ], required=True, default='url', string='Job Type')

    state = fields.Selection([
        ('draft',       'Draft'),
        ('processing',  'In Progress'),
        ('review',      'Review'),
        ('done',        'Done'),
        ('rolled_back', 'Rollback'),
        ('error',       'Error'),
    ], default='draft', string='Status', tracking=True, index=True)

    # Source
    source_url = fields.Char('Source URL')
    attachment_id = fields.Many2one(
        'ir.attachment', string='Uploaded File (Excel/PDF)',
        ondelete='set null',
    )

    # AI options
    enable_translation = fields.Boolean('AR/EN Translation', default=True)
    enable_seo = fields.Boolean('SEO Description Writing', default=True)
    warranty_text = fields.Char(
        'Uellow Warranty Text',
        default='ضمان Uellow سنة كاملة — توصيل خلال 24 ساعة',
    )

    # Safety
    price_variance_limit = fields.Float(
        'Price Variance Limit (%)', default=20.0,
        help='Auto-reject when the price change exceeds this percentage',
    )
    max_products_per_run = fields.Integer('Max Products', default=500)

    # Results
    imported_product_ids = fields.Many2many(
        'product.template', string='Imported Products',
    )
    line_ids = fields.One2many(
        'uellow.import.job.line', 'job_id', string='Lines',
    )

    total_lines = fields.Integer(compute='_compute_stats', string='Total')
    new_count = fields.Integer(compute='_compute_stats', string='New')
    update_count = fields.Integer(compute='_compute_stats', string='Update')
    warning_count = fields.Integer(compute='_compute_stats', string='Warnings')
    approved_count = fields.Integer(compute='_compute_stats', string='Approved')

    # Rollback snapshot — stores original product values as JSON
    rollback_data = fields.Text('Rollback Data (JSON)', readonly=True)
    error_message = fields.Text('Error Message', readonly=True)

    @api.depends('line_ids.line_state', 'line_ids.product_action', 'line_ids.has_warning')
    def _compute_stats(self):
        for job in self:
            lines = job.line_ids
            job.total_lines = len(lines)
            job.new_count = len(lines.filtered(lambda l: l.product_action == 'new'))
            job.update_count = len(lines.filtered(lambda l: l.product_action == 'update'))
            job.warning_count = len(lines.filtered(lambda l: l.has_warning))
            job.approved_count = len(lines.filtered(lambda l: l.line_state == 'approved'))

    @api.constrains('max_products_per_run', 'price_variance_limit')
    def _check_limits(self):
        for j in self:
            if j.max_products_per_run <= 0:
                raise UserError(_('"Max products" must be greater than zero.'))
            if j.price_variance_limit < 0:
                raise UserError(_('"Price variance limit" cannot be negative.'))

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', 'New') == 'New':
                v['name'] = self.env['ir.sequence'].next_by_code('uellow.import.job') or 'New'
        return super().create(vals_list)

    # ── Actions ─────────────────────────────────────────

    def action_run(self):
        """Validate then queue the import job."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only drafts can be run.'))
        if self.job_type == 'url' and not self.source_url:
            raise UserError(_('Enter the source URL.'))
        if self.job_type == 'file' and not self.attachment_id:
            raise UserError(_('Upload a file.'))
        # Clear stale error from previous failed run
        self.write({'error_message': False, 'state': 'processing'})
        self._process_job()

    def _process_job(self):
        """Main processing: scrape/parse → fuzzy match → AI enrich → create lines.

        Uses a savepoint so partial line writes are rolled back on error —
        otherwise re-running a failed job duplicates lines.
        """
        try:
            with self.env.cr.savepoint():
                if self.job_type == 'url':
                    raw_products = self._scrape_url(self.source_url)
                else:
                    raw_products = self._parse_file(self.attachment_id)

                # Safety cap
                if self.max_products_per_run > 0:
                    raw_products = raw_products[:self.max_products_per_run]

                if not raw_products:
                    raise UserError(_('No products found in the source.'))

                # Fuzzy match against existing products
                lines_data = self._fuzzy_match_products(raw_products)

                # AI enrichment
                if self.enable_translation or self.enable_seo:
                    lines_data = self._ai_enrich(lines_data)

                # Batched INSERT — one round-trip instead of N
                self.env['uellow.import.job.line'].create([
                    dict(ld, job_id=self.id) for ld in lines_data
                ])

                self.state = 'review'
                self.message_post(body=_(
                    'Processed. %d products ready for review.') % len(lines_data))
        except UserError as ue:
            # User-facing message — re-raise so it shows in the UI
            self.state = 'error'
            self.error_message = str(ue)
            self.message_post(body=_('Processing failed: %s') % ue.args[0])
            raise
        except Exception as e:
            self.state = 'error'
            self.error_message = str(e)
            _logger.exception('Smart Connector job %s failed', self.name)
            self.message_post(body=_('Processing failed (technical error): %s') % str(e)[:200])
            raise UserError(_('Processing failed. Check the error log for details.'))

    def _scrape_url(self, url):
        """Scrape product data from a URL using JSON-LD parsing."""
        import requests

        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; Uellow/1.0)'}
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            raise UserError(_('Failed to reach the URL: %s') % str(e))

        products = []
        json_ld_matches = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            resp.text, re.DOTALL | re.IGNORECASE)
        for match in json_ld_matches:
            try:
                data = json.loads(match)
                # JSON-LD can be a list or a graph object
                candidates = data if isinstance(data, list) else (
                    data.get('@graph', [data]) if isinstance(data, dict) else []
                )
                for item in candidates:
                    if not isinstance(item, dict):
                        continue
                    if item.get('@type') != 'Product':
                        continue
                    offer = item.get('offers') or {}
                    if isinstance(offer, list):
                        offer = offer[0] if offer else {}
                    img = item.get('image', '')
                    if isinstance(img, list):
                        img = img[0] if img else ''
                    products.append({
                        'name_en': item.get('name', ''),
                        'description_en': item.get('description', ''),
                        'price': float(offer.get('price') or 0),
                        'sku': item.get('sku') or item.get('mpn', ''),
                        'image_url': img if isinstance(img, str) else '',
                        'source_url': url,
                    })
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

        # Fail loudly when nothing found — silent placeholder would waste AI tokens
        if not products:
            raise UserError(_(
                'No product data found at the URL. '
                'The site may not use standard JSON-LD.'))
        return products

    def _parse_file(self, attachment):
        """Parse Excel or PDF attachment into product dicts."""
        if not attachment:
            return []

        content = base64.b64decode(attachment.datas)
        fname = (attachment.name or '').lower()

        if fname.endswith(('.xlsx', '.xls')):
            return self._parse_excel(content)
        elif fname.endswith('.pdf'):
            return self._parse_pdf(content)
        else:
            raise UserError(_('Unsupported file format. Accepted: xlsx, xls, pdf'))

    def _parse_excel(self, content):
        try:
            import openpyxl
        except ImportError:
            raise UserError(_('openpyxl is not installed. Run: pip install openpyxl'))

        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True)
        ws = wb.active

        rows_iter = ws.iter_rows(values_only=True)
        try:
            header_row = next(rows_iter)
        except StopIteration:
            return []
        headers = [str(c or '').lower().strip() for c in header_row]

        products = []
        skipped = 0
        for row in rows_iter:
            if not any(row):
                continue
            d = dict(zip(headers, row))
            name = str(d.get('name', d.get('product', d.get('item', ''))) or '').strip()
            if not name:
                skipped += 1
                continue
            try:
                price = float(d.get('price', d.get('sale_price', 0)) or 0)
                qty = int(d.get('qty', d.get('quantity', d.get('stock', 0))) or 0)
            except (TypeError, ValueError):
                skipped += 1
                continue
            products.append({
                'name_en': name,
                'description_en': str(d.get('description', d.get('desc', '')) or ''),
                'price': price,
                'sku': str(d.get('sku', d.get('barcode', d.get('code', ''))) or ''),
                'qty': qty,
                'image_url': str(d.get('image', d.get('image_url', '')) or ''),
                'source_url': '',
            })
        if skipped:
            _logger.info('Smart Connector: skipped %d malformed rows in %s',
                         skipped, getattr(self, 'name', '?'))
        return products

    def _parse_pdf(self, content):
        """Basic PDF text extraction — each non-trivial line becomes a product."""
        try:
            import pdfplumber
        except ImportError:
            raise UserError(_(
                'pdfplumber is not installed. Run: pip install pdfplumber'))
        products = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ''
                for line in text.split('\n'):
                    line = line.strip()
                    if len(line) > 5:
                        products.append({
                            'name_en': line[:200],
                            'description_en': '',
                            'price': 0.0,
                            'sku': '',
                            'image_url': '',
                            'source_url': '',
                        })
        return products[:100]

    def _fuzzy_match_products(self, raw_products):
        """Match raw products against existing product.template using thefuzz.

        Performance: instead of scoring every active product against every
        raw row (O(N×M)), we narrow candidates by first-token ILIKE first.
        """
        try:
            from thefuzz import process as fuzz_process, fuzz
        except ImportError:
            _logger.warning(
                'thefuzz not installed — every line will be marked as NEW. '
                'Install with: pip install thefuzz')
            return [self._line_from_raw(p, action='new', score=0,
                                        existing_id=False, existing_price=0.0,
                                        has_warning=False)
                    for p in raw_products]

        # Scope to current company so multi-company tenants don't leak.
        company = self.env.company
        company_domain = ['|',
                         ('company_id', '=', False),
                         ('company_id', '=', company.id)]
        all_products = self.env['product.template'].search(
            [('active', '=', True)] + company_domain
        )
        # Build lookup once: id → name
        candidates_by_id = {p.id: (p.name or '') for p in all_products}

        lines = []
        for p in raw_products:
            raw_name = (p.get('name_en') or '').strip()
            best_score, best_pid = 0, False

            if raw_name and candidates_by_id:
                # Narrow by first token if possible — keeps fuzz cheap.
                first_token = raw_name.split()[0].lower() if raw_name.split() else ''
                if first_token:
                    narrow = {pid: nm for pid, nm in candidates_by_id.items()
                              if first_token in nm.lower()}
                    pool = narrow if narrow else candidates_by_id
                else:
                    pool = candidates_by_id
                pool_items = list(pool.items())[:_FUZZY_CANDIDATE_CAP]
                best = fuzz_process.extractOne(
                    raw_name.lower(),
                    {pid: nm.lower() for pid, nm in pool_items},
                    scorer=fuzz.token_sort_ratio,
                    score_cutoff=_FUZZY_THRESHOLD,
                )
                if best:
                    _, best_score, best_pid = best

            action = 'update' if best_pid else 'new'
            existing_price = 0.0
            has_warning = False
            warning_reason = False

            if action == 'update' and best_pid:
                ep = self.env['product.template'].browse(best_pid)
                existing_price = ep.list_price
                new_price = p.get('price') or 0.0
                if existing_price > 0 and new_price > 0:
                    change_pct = abs(new_price - existing_price) / existing_price * 100
                    if change_pct > self.price_variance_limit:
                        has_warning = True
                        warning_reason = _(
                            'Price change %.1f%% exceeds the %.0f%% limit') % (
                            change_pct, self.price_variance_limit)

            lines.append(self._line_from_raw(
                p, action=action, score=best_score,
                existing_id=best_pid if action == 'update' else False,
                existing_price=existing_price,
                has_warning=has_warning, warning_reason=warning_reason,
            ))
        return lines

    @staticmethod
    def _line_from_raw(p, *, action, score, existing_id, existing_price,
                       has_warning, warning_reason=False):
        """Common record-vals builder used by fuzz + fallback paths."""
        return {
            'name_en':           p.get('name_en', ''),
            'name_ar':           '',
            'description_en':    p.get('description_en', ''),
            'description_ar':    '',
            'new_price':         max(0.0, float(p.get('price') or 0)),
            'old_price':         existing_price,
            'new_qty':           max(0, int(p.get('qty') or 0)),
            'source_sku':        p.get('sku', ''),
            'source_url':        p.get('source_url', ''),
            'image_url':         p.get('image_url', ''),
            'product_action':    action,
            'match_score':       score,
            'existing_product_id': existing_id,
            'has_warning':       has_warning,
            'warning_reason':    warning_reason,
            'ai_enriched':       False,
        }

    def _ai_enrich(self, lines_data):
        """Translate and generate SEO descriptions using Claude AI."""
        settings = self.env['uellow.connector.settings'].get_settings()
        api_key = settings.get('anthropic_api_key', '')
        if not api_key:
            _logger.warning('No Anthropic API key configured, skipping AI enrichment')
            return lines_data

        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key, timeout=_AI_TIMEOUT_S)
        except ImportError:
            _logger.warning('anthropic package not installed — skipping AI enrichment')
            return lines_data

        for line in lines_data:
            if not line.get('name_en'):
                continue
            try:
                prompt = (
                    "You are a product content specialist for Uellow, a Kuwaiti "
                    "e-commerce platform.\n\n"
                    f"Product name (English): {line['name_en']}\n"
                    f"Description (English): {line.get('description_en', '')}\n\n"
                    "Tasks:\n"
                    "1. Translate the product name to Arabic (Gulf dialect, natural).\n"
                    "2. Write an Arabic product description (50-100 words, marketing).\n"
                    "3. Write an English SEO description (50-80 words, keywords).\n"
                    f"4. Append this warranty text to both descriptions: "
                    f"\"{self.warranty_text}\"\n\n"
                    'Respond in pure JSON:\n'
                    '{"name_ar": "...", "description_ar": "...", '
                    '"description_en_seo": "..."}'
                )
                msg = client.messages.create(
                    model='claude-sonnet-4-20250514',
                    max_tokens=500,
                    messages=[{'role': 'user', 'content': prompt}],
                )
                text = msg.content[0].text
                # Strip markdown code fences if present
                text = re.sub(r'^```(?:json)?\s*', '', text.strip())
                text = re.sub(r'\s*```$', '', text)
                result = json.loads(text)
                line['name_ar'] = result.get('name_ar', '')
                line['description_ar'] = result.get('description_ar', '')
                line['description_en'] = result.get(
                    'description_en_seo', line.get('description_en', ''))
                line['ai_enriched'] = True
            except Exception as e:
                _logger.warning(
                    'AI enrichment failed for "%s": %s',
                    line.get('name_en'), e)

        return lines_data

    def action_open_review(self):
        """Open review wizard for this job."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Review — {self.name}',
            'res_model': 'uellow.import.review.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_job_id': self.id},
        }

    def action_rollback(self):
        """Restore products to their pre-import state using rollback_data.

        Handles BOTH updated products (restore old vals) and newly-created
        products (archive them, since they didn't exist before).
        """
        self.ensure_one()
        if not self.rollback_data:
            raise UserError(_('No rollback data for this job.'))
        if self.state != 'done':
            raise UserError(_('Only completed jobs can be rolled back.'))

        try:
            data = json.loads(self.rollback_data)
            # data structure: {"updates": {id: old_vals}, "creates": [id, id, ...]}
            # Backward-compat: also accept the old {id: vals} flat dict.
            updates = data.get('updates') if isinstance(data, dict) and 'updates' in data else data
            creates = data.get('creates', []) if isinstance(data, dict) else []

            for product_id, vals in (updates or {}).items():
                product = self.env['product.template'].browse(int(product_id))
                if product.exists():
                    product.write(vals)

            for product_id in creates:
                product = self.env['product.template'].browse(int(product_id))
                if product.exists():
                    product.action_archive()

            self.state = 'rolled_back'
            self.message_post(body=_(
                'Rolled back — %d products restored, %d new products archived.'
            ) % (len(updates or {}), len(creates or [])))
        except UserError:
            raise
        except Exception as e:
            _logger.exception('Rollback failed for job %s', self.name)
            raise UserError(_('Rollback failed: %s') % str(e))
