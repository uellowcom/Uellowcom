# -*- coding: utf-8 -*-
"""Image Backfill — enrich already-imported products that have only one (or a
low-resolution) image with extra high-resolution photos from the configured
image-search provider.

SAFE BY DESIGN:
  • ADD-only for the gallery — never deletes an existing image.
  • Touches the MAIN image only when it is empty, or (opt-in) clearly
    low-resolution, and only if a larger replacement is actually found.
  • Runs in batches with a commit per product so a timeout loses only the tail.
  • Admin-triggered from a button (never a silent cron).
"""
import base64
import io
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ImageBackfill(models.TransientModel):
    _name = 'uellow.image.backfill'
    _description = 'Product Image Backfill'

    # ── targeting ─────────────────────────────────────────────────────
    scope_categ_id = fields.Many2one(
        'product.public.category', string='Category',
        help="Limit to products in this eCommerce category (and children). "
             "Empty = all categories.")
    scope_brand_id = fields.Many2one(
        'product.brand', string='Brand', help="Limit to this brand. Empty = all.")
    only_few_images = fields.Boolean(
        'Only products with few images', default=True)
    max_existing = fields.Integer(
        'Having at most N gallery images', default=1,
        help="Only enrich products whose gallery already has this many images "
             "or fewer (1 = the main image only).")
    published_only = fields.Boolean('Published products only', default=True)

    # ── what to do ────────────────────────────────────────────────────
    images_to_add = fields.Integer('High-res images to add', default=4)
    set_main_if_empty = fields.Boolean(
        'Set main image if missing', default=True)
    promote_best_main = fields.Boolean(
        'Promote largest gallery image to main', default=True,
        help="After enriching, make the main image the highest-resolution one "
             "available (fixes tiny/low-res mains even when a gallery exists).")
    replace_lowres_main = fields.Boolean(
        'Replace low-resolution main image (web search)', default=False,
        help="Off by default. When on, replaces the main image ONLY if the "
             "current one is below the width threshold AND a larger one is "
             "found. (Web images are matched by name — review afterwards.)")
    lowres_threshold = fields.Integer('Low-res width threshold (px)', default=500)
    limit = fields.Integer('Max products per run', default=30)
    dry_run = fields.Boolean(
        'Dry run (count only, no changes)', default=False)

    result_html = fields.Html('Result', readonly=True)

    # ── helpers ───────────────────────────────────────────────────────
    def _target_products(self):
        Tmpl = self.env['product.template']
        domain = [('sale_ok', '=', True)]
        if self.published_only:
            domain.append(('is_published', '=', True))
        if self.scope_categ_id:
            domain.append(('public_categ_ids', 'child_of', self.scope_categ_id.id))
        if self.scope_brand_id and 'brand_id' in Tmpl._fields:
            domain.append(('brand_id', '=', self.scope_brand_id.id))
        recs = Tmpl.search(domain, order='create_date desc')
        if self.only_few_images:
            recs = recs.filtered(
                lambda p: len(p.product_template_image_ids) <= max(0, self.max_existing))
        return recs[:max(1, self.limit)]

    @staticmethod
    def _img_width(b64):
        try:
            im = io.BytesIO(base64.b64decode(b64))
            from PIL import Image
            return Image.open(im).size[0]
        except Exception:
            return 0

    def _query_for(self, product):
        parts = []
        if self.scope_brand_id:
            parts.append(self.scope_brand_id.name or '')
        elif 'brand_id' in product._fields and product.brand_id:
            parts.append(product.brand_id.name or '')
        parts.append(product.with_context(lang='en_US').name or product.name or '')
        return ' '.join(p for p in parts if p).strip()

    # ── run ───────────────────────────────────────────────────────────
    def action_run(self):
        self.ensure_one()
        Line = self.env['uellow.import.job.line']
        Cand = self.env['uellow.import.image.candidate']
        ProductImage = self.env['product.image']

        # provider preflight
        s = Line._settings() if hasattr(Line, '_settings') else {}
        if (s.get('image_search_provider') or 'none') == 'none' \
                or not (s.get('image_search_api_key') or '').strip():
            self.result_html = (
                "<p style='color:#b00'>No image-search provider configured. "
                "Set it in <b>Smart Connector ▸ Settings ▸ Image Search</b> first.</p>")
            return self._reopen()

        targets = self._target_products()
        if self.dry_run:
            self.result_html = (
                "<p><b>Dry run:</b> %d product(s) would be enriched "
                "(at most %d images each).</p>" % (len(targets), self.images_to_add))
            return self._reopen()

        n_main, n_gallery, n_fail, n_done = 0, 0, 0, 0
        for product in targets:
            try:
                q = self._query_for(product)
                if not q:
                    continue
                want = max(self.images_to_add, 1) + 2  # over-fetch for failures
                urls = Line._image_search_urls(q, want) or []
                added_here = 0
                # main image
                main_b64 = product.image_1920
                if not main_b64 and self.set_main_if_empty:
                    for u in list(urls):
                        b = Cand._fetch_to_b64(u)
                        if b:
                            product.image_1920 = b
                            main_b64 = b
                            urls.remove(u)
                            n_main += 1
                            break
                elif main_b64 and self.replace_lowres_main \
                        and self._img_width(main_b64) < self.lowres_threshold:
                    for u in list(urls):
                        b = Cand._fetch_to_b64(u)
                        if b and self._img_width(b) >= self.lowres_threshold:
                            product.image_1920 = b
                            urls.remove(u)
                            n_main += 1
                            break
                # gallery (add-only, up to images_to_add)
                for u in urls:
                    if added_here >= self.images_to_add:
                        break
                    b = Cand._fetch_to_b64(u)
                    if not b:
                        continue
                    ProductImage.create({
                        'product_tmpl_id': product.id,
                        'name': (product.with_context(lang='en_US').name
                                 or product.name or 'image')[:60],
                        'image_1920': b,
                    })
                    added_here += 1
                    n_gallery += 1
                # promote the largest available image to MAIN (fixes tiny/low-res
                # mains even when a gallery already exists) — uses the product's
                # own images, so it's safe and always the right product.
                if self.promote_best_main:
                    cur_w = self._img_width(product.image_1920) if product.image_1920 else 0
                    best = None
                    best_w = cur_w
                    for g in product.product_template_image_ids:
                        gw = self._img_width(g.image_1920)
                        if gw > best_w:
                            best_w = gw
                            best = g
                    if best is not None and best_w > cur_w:
                        product.image_1920 = best.image_1920
                        best.unlink()
                        n_main += 1
                n_done += 1
                self.env.cr.commit()      # keep the lock short; survive timeouts
            except Exception as e:        # noqa: BLE001
                n_fail += 1
                _logger.warning('Image backfill failed for product %s: %s',
                                product.id, e)
                self.env.cr.rollback()

        self.result_html = (
            "<p>✅ Enriched <b>%d</b> product(s): "
            "%d main image(s) set/upgraded, %d gallery image(s) added"
            "%s.</p>" % (
                n_done, n_main, n_gallery,
                (", <span style='color:#b00'>%d failed</span>" % n_fail) if n_fail else ''))
        return self._reopen()

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
