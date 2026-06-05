# -*- coding: utf-8 -*-
"""Shareable cart links — recipient can adopt items into their own cart."""
import secrets

from odoo import api, fields, models


def _gen_token():
    return secrets.token_urlsafe(16)


# Unambiguous alphabet — no 0/O, 1/I/L so customers can read the code
# aloud or type it without confusion.
_SERIAL_ALPHABET = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'


def _gen_serial():
    return ''.join(secrets.choice(_SERIAL_ALPHABET) for _ in range(8))


class MobileCartShare(models.Model):
    _name = 'mobile.cart.share'
    _description = 'Mobile cart share link'
    _order = 'create_date desc'

    token = fields.Char(required=True, index=True,
                        default=lambda self: _gen_token(), copy=False)
    # v2.1.66 — human-friendly serial (shown grouped: K7F2-9Q4D). The
    # recipient can type it in the app instead of scanning the QR.
    serial = fields.Char(index=True, copy=False,
                         default=lambda self: _gen_serial())
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

    @api.model
    def find_by_code(self, code):
        """Resolve a share from anything the user can paste/scan/type:
        the full share URL, the raw token, or the human serial (with or
        without dashes/spaces, case-insensitive)."""
        code = (code or '').strip()
        if not code:
            return self.browse()
        if '/cart/share/' in code:
            code = code.split('/cart/share/')[-1].split('?')[0].strip('/')
        share = self.search([('token', '=', code),
                             ('active', '=', True)], limit=1)
        if share:
            return share
        serial = code.replace('-', '').replace(' ', '').upper()
        return self.search([('serial', '=', serial),
                            ('active', '=', True)], limit=1)
