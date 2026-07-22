import base64, json, math
from odoo import http
from odoo.http import request

PER_PAGE = 12  # archive page size

# Uploaded review photos are stored raw in a Binary field and shown publicly
# on the product page. Cap the size and require REAL image magic-bytes so a
# malicious/buggy client cannot bloat the DB or smuggle a non-image (e.g. an
# SVG carrying script) into the gallery. Mirrors the mobile-api image guard.
MAX_REVIEW_IMAGE_BYTES = 10 * 1024 * 1024


def _sniff_image(raw):
    """True when `raw` starts with a known raster-image magic-number
    (JPEG / PNG / GIF / WebP / HEIC-HEIF-AVIF / BMP). SVG is intentionally
    excluded — it can carry executable script."""
    if not raw or len(raw) < 12:
        return False
    if raw[:3] == b'\xff\xd8\xff':                    # JPEG
        return True
    if raw[:8] == b'\x89PNG\r\n\x1a\n':               # PNG
        return True
    if raw[:4] in (b'GIF8',):                         # GIF
        return True
    if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':   # WebP
        return True
    if raw[4:8] == b'ftyp':                           # HEIC / HEIF / AVIF
        return True
    if raw[:2] == b'BM':                              # BMP
        return True
    return False


class ProductReviewController(http.Controller):

    @http.route('/reviews/write/ajax', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def write_review_ajax(self, **kw):
        try:
            pid = int(kw.get('product_id', 0))
            rv = int(kw.get('rating', 0))
            fb = kw.get('feedback', '').strip()
            if not pid or not rv or not fb:
                return request.make_response(json.dumps({'success': False, 'error': 'Missing fields'}), headers=[('Content-Type', 'application/json')])
            # Clamp to the 1..5 star scale — an out-of-range value fed straight
            # into rating.rating would poison the product's average (pr_avg).
            rv = max(1, min(5, rv))
            product = request.env['product.template'].sudo().browse(pid)
            if not product.exists():
                return request.make_response(json.dumps({'success': False, 'error': 'Not found'}), headers=[('Content-Type', 'application/json')])
            rating = request.env['rating.rating'].sudo().create({
                'res_model_id': request.env['ir.model'].sudo().search([('model', '=', 'product.template')], limit=1).id,
                'res_id': pid, 'res_model': 'product.template',
                'partner_id': request.env.user.partner_id.id,
                'rating': rv, 'feedback': fb,
                'review_title': kw.get('review_title', '').strip(),
                'consumed': False,
            })
            for f in request.httprequest.files.getlist('images'):
                if f and f.filename:
                    raw = f.read(MAX_REVIEW_IMAGE_BYTES + 1)
                    # Reject oversized blobs and anything that isn't real image
                    # bytes instead of storing it verbatim.
                    if not raw or len(raw) > MAX_REVIEW_IMAGE_BYTES or not _sniff_image(raw):
                        continue
                    request.env['rating.review.image'].sudo().create({
                        'rating_id': rating.id, 'image': base64.b64encode(raw),
                        'image_filename': f.filename, 'mimetype': f.mimetype, 'name': f.filename,
                    })
            product._compute_pr_stats()
            return request.make_response(json.dumps({'success': True}), headers=[('Content-Type', 'application/json')])
        except Exception as e:
            return request.make_response(json.dumps({'success': False, 'error': str(e)}), headers=[('Content-Type', 'application/json')])

    @http.route('/reviews/helpful/<int:review_id>', type='json', auth='public', website=True, methods=['POST'])
    def helpful_vote(self, review_id, **kw):
        r = request.env['rating.rating'].sudo().browse(review_id)
        # Only a real, PUBLISHED product review is votable. Without this any id
        # (incl. unrelated rating.rating rows or unmoderated/rejected reviews)
        # could be bumped.
        if not r.exists() or r.res_model != 'product.template' or not r.consumed:
            return {'error': 'not found'}
        # One vote per browser session. helpful_count drives the "most helpful"
        # sort on the archive page + product widget, so an unbounded public
        # counter let a single client push ANY review to the top by spamming
        # (or even double-clicking) this endpoint. Session dedup is the standard
        # Odoo pattern for anonymous votes and needs no schema change.
        voted = request.session.get('prw_helpful_voted') or []
        if review_id in voted:
            return {'count': r.helpful_count, 'already': True}
        r.helpful_count += 1
        request.session['prw_helpful_voted'] = voted + [review_id]
        return {'count': r.helpful_count}

    # ──────────────────────────────────────────────────────────────────
    # Archive page: full list of reviews for a product with pagination.
    # Slug-style URL kept consistent with website_sale (/shop/<slug>/...).
    # The view template renders the same hero + .prw-card markup as the
    # product-page widget so visual identity stays consistent.
    # ──────────────────────────────────────────────────────────────────
    @http.route([
        '/shop/<model("product.template"):product>/reviews',
        '/shop/<model("product.template"):product>/reviews/page/<int:page>',
    ], type='http', auth='public', website=True, sitemap=True)
    def reviews_archive(self, product, page=1, sort='helpful', filter='all', **kw):
        sp = product.sudo()
        # Page param can come via query-string too
        try:
            page = int(kw.get('page', page) or 1)
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)

        reviews = sp.rating_ids.filtered(lambda r: r.consumed and r.rating > 0)

        # Filtering — kept simple; UI builds these via query-string
        if filter == 'photo':
            reviews = reviews.filtered(lambda r: r.review_image_ids)
        elif filter == 'verified':
            reviews = reviews.filtered(lambda r: r.is_verified_purchase)
        elif filter in ('1', '2', '3', '4', '5'):
            target = int(filter)
            reviews = reviews.filtered(lambda r: int(r.rating or 0) == target)
        elif filter == 'critical':
            reviews = reviews.filtered(lambda r: int(r.rating or 0) <= 3)

        # Sorting
        if sort == 'recent':
            reviews = reviews.sorted(key=lambda r: r.write_date, reverse=True)
        elif sort == 'high':
            reviews = reviews.sorted(key=lambda r: (r.rating or 0, r.write_date), reverse=True)
        elif sort == 'low':
            reviews = reviews.sorted(key=lambda r: (r.rating or 0, r.write_date))
        else:  # helpful (default)
            reviews = reviews.sorted(key=lambda r: (r.helpful_count or 0, r.write_date), reverse=True)

        total = len(reviews)
        total_pages = max(1, math.ceil(total / PER_PAGE))
        page = min(page, total_pages)
        start = (page - 1) * PER_PAGE
        reviews_page = reviews[start:start + PER_PAGE]

        return request.render('product_reviews.reviews_archive_page', {
            'product': sp,
            'reviews_page': reviews_page,
            'pager': {'page': page, 'total_pages': total_pages, 'total': total},
            'current_sort': sort,
            'current_filter': filter,
        })
