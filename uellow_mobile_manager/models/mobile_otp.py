# -*- coding: utf-8 -*-
"""
mobile.otp.code — one-time sign-in codes for the mobile app.

Flow: /auth/otp/email/request stores a hashed 6-digit code (10-minute
expiry) and emails it; /auth/otp/email/verify checks it (max 5 attempts)
and issues a bearer token, creating a portal user on the fly when the
email is new. Codes are single-use.
"""
import hashlib

from odoo import api, fields, models


class MobileOtpCode(models.Model):
    _name = 'mobile.otp.code'
    _description = 'Mobile App OTP Code'
    _order = 'id desc'

    target = fields.Char('Email / Phone', required=True, index=True)
    code_hash = fields.Char('Code (sha256)', required=True)
    expires_at = fields.Datetime('Expires', required=True)
    attempts = fields.Integer(default=0)
    used = fields.Boolean(default=False)

    @api.model
    def _hash(self, target, code):
        return hashlib.sha256(
            ('%s|%s' % (target.strip().lower(), code)).encode()).hexdigest()

    @api.model
    def issue(self, target, code, minutes=10):
        """Invalidate older codes for this target, store the new one."""
        old = self.sudo().search([('target', '=', target.strip().lower()),
                                  ('used', '=', False)])
        old.write({'used': True})
        return self.sudo().create({
            'target': target.strip().lower(),
            'code_hash': self._hash(target, code),
            'expires_at': fields.Datetime.add(fields.Datetime.now(),
                                              minutes=minutes),
        })

    @api.model
    def check(self, target, code):
        """Return True and consume the code when valid."""
        rec = self.sudo().search([
            ('target', '=', (target or '').strip().lower()),
            ('used', '=', False),
        ], limit=1)
        if not rec:
            return False
        if rec.expires_at < fields.Datetime.now() or rec.attempts >= 5:
            rec.used = True
            return False
        if rec.code_hash != self._hash(target, code):
            rec.attempts += 1
            return False
        rec.used = True
        return True

    @api.autovacuum
    def _gc_expired(self):
        self.sudo().search([
            ('expires_at', '<', fields.Datetime.subtract(
                fields.Datetime.now(), days=1)),
        ]).unlink()
