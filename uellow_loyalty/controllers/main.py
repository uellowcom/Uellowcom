from odoo import http
from odoo.http import request


class LoyaltyPortal(http.Controller):

    @http.route('/my/loyalty', type='http', auth='user', website=True)
    def loyalty_page(self, **kw):
        partner = request.env.user.partner_id
        account = request.env['uellow.loyalty.account'].sudo().search([
            ('partner_id', '=', partner.id)
        ], limit=1)
        if not account:
            account = request.env['uellow.loyalty.account'].sudo().create({
                'partner_id': partner.id
            })
        program = request.env['uellow.loyalty.program'].sudo().get_program()
        transactions = request.env['uellow.loyalty.transaction'].sudo().search([
            ('account_id', '=', account.id)
        ], limit=30, order='id desc')
        return request.render('uellow_loyalty.portal_loyalty', {
            'account': account,
            'program': program,
            'transactions': transactions,
        })

    @http.route('/loyalty/redeem', type='json', auth='user')
    def redeem_points(self, points, order_id=False):
        partner = request.env.user.partner_id
        account = request.env['uellow.loyalty.account'].sudo().search([
            ('partner_id', '=', partner.id)], limit=1)
        if not account:
            return {'error': 'No loyalty account'}
        try:
            discount = account.redeem_points(int(points), order_id=order_id)
            return {'ok': True, 'discount': discount, 'balance': account.balance}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/loyalty/birthday/check', type='json', auth='user',
                methods=['POST'], csrf=False)
    def birthday_check(self, **kw):
        """Once-a-year birthday bonus — called by the Beena widget on first
        open. Uses the LIVE uellow.loyalty.account model + the program's
        points_birthday value. Silent no-op when the customer has no
        birthdate set or today is not their birthday. Never 500s."""
        import datetime
        try:
            partner = request.env.user.partner_id
            bday = partner.uellow_birthdate \
                if 'uellow_birthdate' in partner._fields else False
            if not bday:
                return {'birthday': False}
            today = datetime.date.today()
            if not (bday.month == today.month and bday.day == today.day):
                return {'birthday': False}
            Acc = request.env['uellow.loyalty.account'].sudo()
            account = Acc.search([('partner_id', '=', partner.id)], limit=1) \
                or Acc.create({'partner_id': partner.id})
            # dedup: already awarded a birthday bonus this calendar year?
            already = request.env['uellow.loyalty.transaction'].sudo() \
                .search_count([
                    ('account_id', '=', account.id),
                    ('tx_type', '=', 'earn'),
                    ('reason', 'ilike', 'ميلاد'),
                    ('date', '>=', datetime.datetime(today.year, 1, 1)),
                ])
            if already:
                return {'birthday': True, 'already_given': True}
            program = request.env['uellow.loyalty.program'].sudo().get_program()
            points = program.points_birthday or 0
            if points <= 0:
                return {'birthday': False}
            account.earn_points(points, 'عيد ميلاد سعيد! 🎂')
            try:
                request.env.cr.commit()
            except Exception:
                pass
            return {
                'birthday':       True,
                'already_given':  False,
                'points_awarded': points,
                'message':        'عيد ميلاد سعيد! حصلت على %d نقطة 🎂' % points,
            }
        except Exception:
            return {'birthday': False}
