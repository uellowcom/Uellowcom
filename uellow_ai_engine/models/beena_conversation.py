# -*- coding: utf-8 -*-
"""Beena conversation archive: persistent storage of chat sessions and messages."""

from odoo import models, fields, api, _


class BeenaConversation(models.Model):
    _name = 'beena.conversation'
    _description = 'Beena Conversation'
    _order = 'create_date desc'
    _rec_name = 'display_title'

    session_id = fields.Char(string='Session ID', index=True, required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', index=True, ondelete='set null')
    is_guest = fields.Boolean(string='Guest', default=True)
    product_id = fields.Many2one('product.template', string='Product Context', ondelete='set null')
    lang = fields.Char(string='Language', default='ar')

    message_ids = fields.One2many('beena.message', 'conversation_id', string='Messages')
    message_count = fields.Integer(string='Messages', compute='_compute_stats', store=True)

    total_input_tokens = fields.Integer(string='Input Tokens', compute='_compute_stats', store=True)
    total_output_tokens = fields.Integer(string='Output Tokens', compute='_compute_stats', store=True)
    total_cost = fields.Float(string='Total Cost (USD)', compute='_compute_stats', store=True, digits=(12, 6))

    claude_calls = fields.Integer(string='Claude Calls', compute='_compute_stats', store=True)
    cache_hits = fields.Integer(string='Cache Hits', compute='_compute_stats', store=True)

    state = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived'),
    ], string='Status', default='active', index=True)

    display_title = fields.Char(string='Title', compute='_compute_title', store=True)

    @api.depends('partner_id', 'product_id', 'create_date')
    def _compute_title(self):
        for rec in self:
            who = rec.partner_id.name if rec.partner_id else _('Guest')
            when = fields.Datetime.to_string(rec.create_date)[:16] if rec.create_date else ''
            rec.display_title = '%s · %s' % (who, when)

    @api.depends('message_ids', 'message_ids.cost', 'message_ids.source',
                 'message_ids.input_tokens', 'message_ids.output_tokens')
    def _compute_stats(self):
        for rec in self:
            msgs = rec.message_ids
            rec.message_count = len(msgs)
            rec.total_input_tokens = sum(msgs.mapped('input_tokens'))
            rec.total_output_tokens = sum(msgs.mapped('output_tokens'))
            rec.total_cost = sum(msgs.mapped('cost'))
            rec.claude_calls = len(msgs.filtered(lambda m: m.source == 'claude'))
            rec.cache_hits = len(msgs.filtered(lambda m: m.source == 'cache'))


class BeenaMessage(models.Model):
    _name = 'beena.message'
    _description = 'Beena Message'
    _order = 'create_date asc, id asc'

    conversation_id = fields.Many2one('beena.conversation', string='Conversation',
                                      required=True, ondelete='cascade', index=True)
    role = fields.Selection([
        ('user', 'Customer'),
        ('assistant', 'Beena'),
    ], string='Sender', required=True)
    body = fields.Text(string='Message')

    source = fields.Selection([
        ('claude', 'Claude API'),
        ('cache', 'Answer Cache'),
        ('db_routing', 'Database Routing'),
        ('system', 'System'),
    ], string='Source', default='claude', index=True,
        help='Where the assistant reply came from.')

    input_tokens = fields.Integer(string='Input Tokens', default=0)
    output_tokens = fields.Integer(string='Output Tokens', default=0)
    cost = fields.Float(string='Cost (USD)', default=0.0, digits=(12, 6))

    product_id = fields.Many2one('product.template', string='Product Context', ondelete='set null')

    # Serialized payload of any rich cards (cart, fit_check, tryon, etc.)
    # dispatched alongside the AI reply — used to rehydrate the full chat
    # state after page reload / re-login.
    extra_json = fields.Text(string='Card payload (JSON)')
