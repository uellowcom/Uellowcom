# -*- coding: utf-8 -*-
"""Public «Uellow Reviewers» landing page (/reviewers): bilingual pitch
of the specialists program + membership application form."""
from odoo import http
from odoo.http import request


def _icp(key, default):
    return request.env['ir.config_parameter'].sudo().get_param(
        'uellow_reviewers.' + key, default)


class ReviewersWebsiteLanding(http.Controller):

    @http.route('/reviewers', type='http', auth='public', website=True,
                sitemap=True)
    def reviewers_page(self, **kw):
        signed_in = not request.env.user._is_public()
        already = False
        if signed_in:
            partner = request.env.user.partner_id
            Prof = request.env['reviewer.profile'].sudo()
            already = bool(Prof.search_count(
                ['|', ('partner_id', '=', partner.id),
                 ('partner_id', '=',
                  partner.commercial_partner_id.id)]))
        def num(key, d):
            try:
                return float(_icp(key, d) or d)
            except Exception:
                return float(d)
        return request.render('uellow_reviewers.reviewers_landing', {
            'signed_in': signed_in,
            'already': already,
            'msg': kw.get('msg', ''),
            'pts': {
                'written': int(num('points_written', '10')),
                'chat': int(num('points_chat', '15')),
                'photo': int(num('points_photo', '12')),
                'video': int(num('points_video', '20')),
                'tryon': int(num('points_tryon', '8')),
            },
            'rate': int(num('points_per_kd', '100')),
            'profit_pct': num('profit_share_pct', '3'),
        })

    @http.route('/reviewers/apply', type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def reviewers_apply(self, **kw):
        name = (kw.get('name') or '').strip()
        phone = (kw.get('phone') or '').strip()
        email = (kw.get('email') or '').strip()
        specialties = (kw.get('specialties') or '').strip()
        bio = (kw.get('bio') or '').strip()
        if not name or not phone:
            return request.redirect('/reviewers?msg=missing#apply')
        Partner = request.env['res.partner'].sudo()
        Prof = request.env['reviewer.profile'].sudo()
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
        if Prof.search_count([('partner_id', '=', partner.id)]):
            return request.redirect('/reviewers?msg=already#apply')
        try:
            Prof.create({
                'partner_id': partner.id,
                'display_name': name,
                'bio': bio,
                'specialty_text': specialties,
            })
            request.env.cr.commit()
        except Exception:
            return request.redirect('/reviewers?msg=already#apply')
        return request.redirect('/reviewers?msg=ok#apply')
