# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


def _card_json(c):
    return {
        'id': c.id,
        'number': c.name,
        'product': c.product_id.display_name,
        'product_id': c.product_id.id,
        'image': '/web/image/product.product/%s/image_256' % c.product_id.id,
        'serial': c.lot_serial or '',
        'policy': c.policy_id.name,
        'policy_ar': c.policy_id.name_ar or '',
        'icon': c.policy_id.icon or '🛡️',
        'months': c.duration_months,
        'date_start': c.date_start and c.date_start.isoformat() or '',
        'date_end': c.date_end and c.date_end.isoformat() or '',
        'days_left': c.days_left,
        'state': c.state,
        'coverage_en': c.policy_id.coverage_en or '',
        'coverage_ar': c.policy_id.coverage_ar or '',
        'source': c.source_label,
        'certificate_url': '/report/pdf/uellow_warranty.warranty_certificate/%s' % c.id,
    }


class WarrantyController(http.Controller):

    # ---- Public verify (QR scan) -------------------------------------------
    @http.route(['/warranty/verify/<string:number>'], type='http',
                auth='public', methods=['GET'], csrf=False, sitemap=False)
    def verify(self, number, **kw):
        card = request.env['uellow.warranty.card'].sudo().search(
            [('name', '=', number)], limit=1)
        if not card:
            return request.make_json_response({'found': False})
        return request.make_json_response({
            'found': True,
            'number': card.name,
            'product': card.product_id.display_name,
            'state': card.state,
            'months': card.duration_months,
            'date_end': card.date_end and card.date_end.isoformat() or '',
            'policy': card.policy_id.name,
        })

    # ---- Customer app: my warranties ---------------------------------------
    @http.route(['/uellow/warranty/my'], type='json', auth='user', methods=['POST'])
    def my_warranties(self, **kw):
        partner = request.env.user.partner_id
        cards = request.env['uellow.warranty.card'].sudo().search(
            [('partner_id', 'child_of', partner.commercial_partner_id.id)],
            order='date_end desc')
        return {'count': len(cards), 'warranties': [_card_json(c) for c in cards]}

    # ---- Vendor/merchant app: register a warranty --------------------------
    @http.route(['/uellow/warranty/register'], type='json', auth='user', methods=['POST'])
    def register(self, partner_id=None, product_id=None, months=None,
                 policy_id=None, serial=None, date_start=None, **kw):
        env = request.env
        partner = env['res.partner'].sudo().browse(int(partner_id)) if partner_id else None
        product = env['product.product'].sudo().browse(int(product_id)) if product_id else None
        if not partner or not partner.exists() or not product or not product.exists():
            return {'ok': False, 'error': 'partner_id and product_id are required'}
        Policy = env['uellow.warranty.policy'].sudo()
        if policy_id:
            policy = Policy.browse(int(policy_id))
        elif months:
            # find or create a policy matching the requested months
            policy = Policy.search([('duration_months', '=', int(months))], limit=1)
            if not policy:
                policy = Policy.create({
                    'name': '%s months' % int(months),
                    'name_ar': '%s شهر' % int(months),
                    'duration_months': int(months),
                })
        else:
            policy = Policy._get_for_product(product)
        if not policy:
            return {'ok': False, 'error': 'no policy resolved'}
        card = env['uellow.warranty.card'].sudo().create({
            'partner_id': partner.id,
            'product_id': product.id,
            'policy_id': policy.id,
            'lot_serial': serial or False,
            'date_start': date_start or False,
        })
        return {'ok': True, 'warranty': _card_json(card)}

    # ---- Per-product warranty info (for product pages / app) ---------------
    @http.route(['/uellow/warranty/for_product/<int:product_id>'], type='json',
                auth='public', methods=['POST'])
    def for_product(self, product_id, **kw):
        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            return {'has_warranty': False}
        policy = request.env['uellow.warranty.policy'].sudo()._get_for_product(product)
        if not policy or policy.no_warranty:
            return {'has_warranty': False}
        return {
            'has_warranty': True,
            'months': policy.duration_months,
            'policy': policy.name,
            'policy_ar': policy.name_ar or '',
            'icon': policy.icon or '🛡️',
            'coverage_en': policy.coverage_en or '',
            'coverage_ar': policy.coverage_ar or '',
        }
