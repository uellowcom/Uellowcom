from odoo import models, fields, api
import json


class AiChatSession(models.Model):
    _name = 'ai.chat.session'
    _description = 'Beena AI Chat Session'
    _order = 'write_date desc'
    _rec_name = 'session_id'

    session_id = fields.Char(string='Session ID', required=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', ondelete='cascade')
    product_id = fields.Many2one('product.template', string='Product Context')
    messages_json = fields.Text(string='Messages (JSON)', default='[]')
    last_state = fields.Selection([
        ('idle',     'Idle'),
        ('talking',  'Talking'),
        ('thinking', 'Thinking'),
        ('happy',    'Happy'),
        ('excited',  'Excited'),
        ('sad',      'Sad'),
    ], default='idle')
    active = fields.Boolean(default=True)

    @api.model
    def get_or_create(self, session_id, partner_id=None, product_id=None):
        session = self.search([('session_id', '=', session_id)], limit=1)
        if not session:
            session = self.create({
                'session_id': session_id,
                'partner_id': partner_id,
                'product_id': product_id,
            })
        return session

    def get_messages(self):
        try:
            return json.loads(self.messages_json or '[]')
        except Exception:
            return []

    def add_message(self, role, content):
        msgs = self.get_messages()
        msgs.append({'role': role, 'content': content})
        # Keep last 20 messages only (10 turns) to save tokens
        if len(msgs) > 20:
            msgs = msgs[-20:]
        self.messages_json = json.dumps(msgs, ensure_ascii=False)

    def clear_messages(self):
        self.messages_json = '[]'


class AiMessageLog(models.Model):
    _name = 'ai.message.log'
    _description = 'Beena Message Log'
    _order = 'create_date desc'

    session_id = fields.Many2one('ai.chat.session', ondelete='cascade')
    role = fields.Selection([('user', 'User'), ('assistant', 'Assistant')])
    content = fields.Text()
    state = fields.Char()
    tokens_used = fields.Integer()
    function_called = fields.Char()
