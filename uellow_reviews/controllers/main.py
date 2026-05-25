from odoo import http
from odoo.http import request


class ReviewController(http.Controller):

    @http.route('/review/submit', type='json', auth='user')
    def submit_review(self, product_id, rating, body, title='', order_id=False, **kw):
        if not (1 <= int(rating) <= 5):
            return {'error': 'Rating must be 1-5'}
        partner = request.env.user.partner_id
        review = request.env['uellow.product.review'].sudo().create({
            'product_id': int(product_id),
            'partner_id': partner.id,
            'rating': int(rating),
            'title': title,
            'body': body,
            'order_id': int(order_id) if order_id else False,
        })
        return {'ok': True, 'review_id': review.id, 'state': review.state}

    @http.route('/review/helpful/<int:review_id>', type='json', auth='user')
    def mark_helpful(self, review_id):
        review = request.env['uellow.product.review'].sudo().browse(review_id)
        if review.exists():
            review.helpful_count += 1
        return {'ok': True}
