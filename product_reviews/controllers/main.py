import base64, json, math
from odoo import http
from odoo.http import request

PER_PAGE = 12  # archive page size


class ProductReviewController(http.Controller):

    @http.route('/reviews/write/ajax', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def write_review_ajax(self, **kw):
        try:
            pid = int(kw.get('product_id', 0))
            rv = int(kw.get('rating', 0))
            fb = kw.get('feedback', '').strip()
            if not pid or not rv or not fb:
                return request.make_response(json.dumps({'success': False, 'error': 'Missing fields'}), headers=[('Content-Type', 'application/json')])
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
                    request.env['rating.review.image'].sudo().create({
                        'rating_id': rating.id, 'image': base64.b64encode(f.read()),
                        'image_filename': f.filename, 'mimetype': f.mimetype, 'name': f.filename,
                    })
            product._compute_pr_stats()
            return request.make_response(json.dumps({'success': True}), headers=[('Content-Type', 'application/json')])
        except Exception as e:
            return request.make_response(json.dumps({'success': False, 'error': str(e)}), headers=[('Content-Type', 'application/json')])

    @http.route('/reviews/helpful/<int:review_id>', type='json', auth='public', website=True, methods=['POST'])
    def helpful_vote(self, review_id, **kw):
        r = request.env['rating.rating'].sudo().browse(review_id)
        if r.exists():
            r.helpful_count += 1
            return {'count': r.helpful_count}
        return {'error': 'not found'}

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
