from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import logging

_logger = logging.getLogger(__name__)


class BeenaChatPortal(CustomerPortal):
    """Portal pages for Beena conversation history."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'chat_count' in counters:
            values['chat_count'] = request.env['beena.conversation'].sudo().search_count([
                ('partner_id', '=', partner.id),
            ])
        return values

    @http.route(['/my/chat-history'], type='http', auth='user', website=True)
    def my_chat_history(self, **kw):
        partner = request.env.user.partner_id
        conversations = request.env['beena.conversation'].sudo().search(
            [('partner_id', '=', partner.id)],
            order='create_date desc',
            limit=50,
        )
        return request.render('uellow_ai_engine.portal_my_chat_history', {
            'conversations': conversations,
            'partner': partner,
            'page_name': 'chat_history',
        })

    @http.route(['/my/chat-history/<int:conv_id>'], type='http', auth='user', website=True)
    def my_chat_history_detail(self, conv_id, **kw):
        partner = request.env.user.partner_id
        conv = request.env['beena.conversation'].sudo().browse(conv_id)
        if not conv.exists() or conv.partner_id.id != partner.id:
            return request.redirect('/my/chat-history')
        messages = conv.message_ids.sorted('create_date')
        return request.render('uellow_ai_engine.portal_chat_conversation', {
            'conversation': conv,
            'messages': messages,
            'partner': partner,
            'page_name': 'chat_history',
        })
