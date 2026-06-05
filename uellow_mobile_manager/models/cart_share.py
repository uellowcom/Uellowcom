# -*- coding: utf-8 -*-
"""Shareable cart links — recipient can adopt items into their own cart."""
import secrets

from odoo import api, fields, models


def _gen_token():
    return secrets.token_urlsafe(16)


class MobileCartShare(models.Model):
    _name = 'mobile.cart.share'
    _description = 'Mobile cart share link'
    _order = 'create_date desc'

    token = fields.Char(required=True, index=True,
                        default=lambda self: _gen_token(), copy=False)
    order_id = fields.Many2one('sale.order', ondelete='set null',
                               string='Source cart')
    partner_id = fields.Many2one('res.partner', string='Shared by')
    lines_json = fields.Text(string='Lines snapshot')
    adopted_count = fields.Integer(default=0,
        help='How many times this share was opened and items adopted')
    expires_at = fields.Datetime()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('token_uniq', 'unique(token)', 'Share token must be unique'),
    ]
