# -*- coding: utf-8 -*-
"""Public «Partners Program» landing page (/partners): bilingual pitch,
how-it-works, tiers, FAQ + membership application form. Linked from the
website footer."""
from odoo import http
from odoo.http import request

from ..models.affiliate import tier_rules


class AffiliateWebsitePage(http.Controller):

    @http.route('/partners', type='http', auth='public', website=True,
                sitemap=True)
    def partners_page(self, **kw):
        rules = tier_rules(request.env)
        signed_in = not request.env.user._is_public()
        already = False
        if signed_in:
            partner = request.env.user.partner_id
            Aff = request.env['uellow.affiliate'].sudo()
            already = bool(Aff.search_count(
                ['|', ('partner_id', '=', partner.id),
                 ('partner_id', '=', partner.commercial_partner_id.id)]))
        return request.render('uellow_affiliate.partners_landing', {
            'rules': rules,
            'signed_in': signed_in,
            'already': already,
            'msg': kw.get('msg', ''),
        })

    @http.route('/partners/apply', type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def partners_apply(self, **kw):
        name = (kw.get('name') or '').strip()
        phone = (kw.get('phone') or '').strip()
        email = (kw.get('email') or '').strip()
        note = (kw.get('note') or '').strip()
        if not name or not phone:
            return request.redirect('/partners?msg=missing#apply')
        Partner = request.env['res.partner'].sudo()
        Aff = request.env['uellow.affiliate'].sudo()
        if not request.env.user._is_public():
            partner = request.env.user.partner_id
        else:
            partner = Partner.search(
                ['|', ('phone', '=', phone), ('mobile', '=', phone)],
                limit=1)
            if not partner and email:
                partner = Partner.search([('email', '=ilike', email)],
                                         limit=1)
            if not partner:
                partner = Partner.create({
                    'name': name, 'phone': phone, 'email': email,
                    'company_type': 'person',
                })
        if Aff.search_count([('partner_id', '=', partner.id)]):
            return request.redirect('/partners?msg=already#apply')
        try:
            Aff.create({
                'name': name or partner.name,
                'partner_id': partner.id,
                'phone': phone,
                'email': email or partner.email or '',
                'note': note,
            })
            request.env.cr.commit()
        except Exception:
            return request.redirect('/partners?msg=already#apply')
        return request.redirect('/partners?msg=ok#apply')
