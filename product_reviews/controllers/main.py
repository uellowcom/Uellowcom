import base64, json
from odoo import http
from odoo.http import request

class ProductReviewController(http.Controller):

    @http.route('/reviews/write/ajax', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def write_review_ajax(self, **kw):
        try:
            pid = int(kw.get('product_id', 0))
            rv  = int(kw.get('rating', 0))
            fb  = kw.get('feedback', '').strip()
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
