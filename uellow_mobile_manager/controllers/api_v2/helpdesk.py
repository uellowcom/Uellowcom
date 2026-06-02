"""Helpdesk — /api/mobile/v2/helpdesk/*

Create support tickets straight from the mobile app. Uses Odoo's
`helpdesk.ticket` model (helpdesk is installed in this DB). When the
mobile user is identified, we link the ticket to their res.partner
so the agent has full context.

Endpoints:
  GET  /api/mobile/v2/helpdesk/form   → team picker + ticket categories
  POST /api/mobile/v2/helpdesk/create → create a new ticket
"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, current_partner, require_auth,
)


class MobileHelpdeskAPI(http.Controller):

    @http.route('/api/mobile/v2/helpdesk/form', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def form_meta(self, **kw):
        Team = request.env.get('helpdesk.team')
        if Team is None:
            return fail('NO_HELPDESK', 'Helpdesk not installed', 503)
        teams = Team.sudo().search([('active', '=', True)])
        return ok({
            'teams': [{
                'id':   t.id,
                'name': t.name,
                'description': t.description or '',
            } for t in teams],
            'categories': [
                {'key': 'order',     'en': 'Order / Delivery',  'ar': 'الطلب / التوصيل'},
                {'key': 'payment',   'en': 'Payment / Refund',  'ar': 'الدفع / الاسترداد'},
                {'key': 'product',   'en': 'Product issue',     'ar': 'مشكلة في المنتج'},
                {'key': 'account',   'en': 'Account / Login',   'ar': 'الحساب / تسجيل الدخول'},
                {'key': 'other',     'en': 'Other',             'ar': 'أخرى'},
            ],
        })

    @http.route('/api/mobile/v2/helpdesk/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_ticket(self, **kw):
        Ticket = request.env.get('helpdesk.ticket')
        Team   = request.env.get('helpdesk.team')
        if Ticket is None or Team is None:
            return fail('NO_HELPDESK', 'Helpdesk not installed', 503)
        p = get_payload()
        subject     = (p.get('subject') or '').strip()
        description = (p.get('description') or '').strip()
        category    = (p.get('category') or 'other').strip()
        order_ref   = (p.get('order_ref') or '').strip()
        team_id     = p.get('team_id')
        if not subject or not description:
            return fail('MISSING', 'subject and description are required')
        partner = current_partner()
        team = (Team.sudo().browse(int(team_id))
                if team_id else Team.sudo().search([], limit=1))
        # Compose a rich description so agents have context immediately
        lines = [description, '']
        if order_ref:
            lines += [f'— Order reference: {order_ref}']
        lines += [
            f'— Category: {category}',
            f'— Sent from mobile app',
            f'— Customer: {partner.name} ({partner.email or partner.phone or "n/a"})',
        ]
        vals = {
            'name':        subject,
            'description': '\n'.join(lines),
            'partner_id':  partner.id,
            'partner_email': partner.email or '',
            'partner_name':  partner.name or '',
        }
        if team:
            vals['team_id'] = team.id
        # Hook in the matching order if we found one
        if order_ref:
            order = request.env['sale.order'].sudo().search([
                ('name', '=', order_ref),
                ('partner_id', '=', partner.id),
            ], limit=1)
            if order and 'sale_order_id' in Ticket._fields:
                vals['sale_order_id'] = order.id
        ticket = Ticket.sudo().create(vals)
        # Attach uploaded photos (base64). Caps at 5 — anything more and
        # the chatter gets noisy.
        photos = p.get('photos') or p.get('images') or []
        if isinstance(photos, str):
            try:
                import json as _json
                photos = _json.loads(photos)
            except Exception:
                photos = []
        if isinstance(photos, list) and photos:
            for idx, b64 in enumerate(photos[:5]):
                if not b64:
                    continue
                if isinstance(b64, str) and b64.startswith('data:') and ',' in b64:
                    b64 = b64.split(',', 1)[1]
                try:
                    request.env['ir.attachment'].sudo().create({
                        'name': f'ticket-{ticket.id}-photo-{idx+1}.jpg',
                        'type': 'binary',
                        'datas': b64,
                        'res_model': 'helpdesk.ticket',
                        'res_id': ticket.id,
                        'mimetype': 'image/jpeg',
                    })
                except Exception:
                    pass
            try:
                ticket.message_post(body=f'Customer uploaded {min(len(photos),5)} photo(s) via mobile app.')
            except Exception:
                pass
        return ok({
            'ticket_id':   ticket.id,
            'ticket_name': ticket.name,
            'number':      getattr(ticket, 'ticket_ref', '') or str(ticket.id),
            'team':        team.name if team else '',
        })
