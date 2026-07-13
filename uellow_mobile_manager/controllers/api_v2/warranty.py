# -*- coding: utf-8 -*-
"""Warranty — /api/mobile/v2/warranty/*

Customer-facing warranty cards (read from uellow.warranty.card). Bilingual
envelope like the rest of the mobile API. Certificate is streamed as a PDF
behind the bearer token so the app can open it without a web session.
"""
from datetime import date

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, ok, fail, current_partner, require_auth, img_url, base_url,
    _hash_token,
)

_STATE_EN = {'active': 'Active', 'expired': 'Expired',
             'void': 'Void', 'claimed': 'Claimed'}
_STATE_AR = {'active': 'ساري', 'expired': 'منتهٍ',
             'void': 'ملغى', 'claimed': 'تمت المطالبة'}


def _card_json(c):
    today = date.today()
    pol = c.policy_id
    prod = c.product_id
    return {
        'id': c.id,
        'number': c.name,
        'product': {
            'en': prod.with_context(lang='en_US').display_name,
            'ar': prod.with_context(lang='ar_001').display_name,
        },
        'product_id': prod.id,
        'image': img_url('product.product', prod.id, 'image_256'),
        'serial': c.lot_serial or '',
        'policy': {'en': pol.name or '', 'ar': pol.name_ar or pol.name or ''},
        'icon': pol.icon or '🛡️',
        'months': c.duration_months,
        'date_start': c.date_start.isoformat() if c.date_start else '',
        'date_end': c.date_end.isoformat() if c.date_end else '',
        'days_left': (c.date_end - today).days if c.date_end else 0,
        'state': c.state,
        'state_label': {'en': _STATE_EN.get(c.state, c.state),
                        'ar': _STATE_AR.get(c.state, c.state)},
        'coverage': {'en': pol.coverage_en or '', 'ar': pol.coverage_ar or ''},
        'terms': {'en': pol.terms_en or '', 'ar': pol.terms_ar or ''},
        'source': c.source_label or '',
        'certificate': base_url() + '/api/mobile/v2/warranty/%s/certificate' % c.id,
    }


class MobileWarrantyAPI(http.Controller):

    @http.route('/api/mobile/v2/warranty', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def my_warranties(self, **kw):
        partner = current_partner()
        Card = request.env.get('uellow.warranty.card')
        if Card is None:
            return ok({'count': 0, 'active': 0, 'warranties': []})
        cards = Card.sudo().search(
            [('partner_id', 'child_of', partner.commercial_partner_id.id)],
            order='date_end desc')
        items = [_card_json(c) for c in cards]
        active = sum(1 for c in cards if c.state == 'active')
        return ok({'count': len(cards), 'active': active, 'warranties': items})

    @http.route('/api/mobile/v2/warranty/verify', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def verify(self, **kw):
        number = (kw.get('number') or '').strip()
        Card = request.env.get('uellow.warranty.card')
        card = (Card.sudo().search([('name', '=', number)], limit=1)
                if (Card is not None and number) else None)
        if not card:
            return ok({'found': False})
        return ok({
            'found': True,
            'number': card.name,
            'state': card.state,
            'months': card.duration_months,
            'product': card.product_id.display_name,
            'date_end': card.date_end.isoformat() if card.date_end else '',
        })

    @http.route('/api/mobile/v2/warranty/<int:card_id>/certificate',
                type='http', auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def certificate(self, card_id, **kw):
        # Auth via bearer header OR ?token= (so the app can open the PDF
        # directly in a webview/browser without setting headers).
        partner = current_partner()
        if not partner:
            tok = (kw.get('token') or '').strip()
            if tok:
                sess = request.env['mobile.session'].sudo().search(
                    [('token_hash', '=', _hash_token(tok)),
                     ('is_active', '=', True)], limit=1)
                partner = sess.partner_id if sess else False
        if not partner:
            return fail('AUTH_REQUIRED', 'Authentication required', 401)
        Card = request.env.get('uellow.warranty.card')
        card = Card.sudo().browse(card_id) if Card is not None else None
        if (not card or not card.exists() or
                card.partner_id.commercial_partner_id.id !=
                partner.commercial_partner_id.id):
            return fail('NOT_FOUND', 'Warranty not found', 404)
        pdf, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'uellow_warranty.warranty_certificate', card.ids)
        fname = (card.name or 'warranty').replace('/', '-')
        return request.make_response(pdf, headers=[
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'inline; filename=%s.pdf' % fname),
        ])
