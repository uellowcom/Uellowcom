"""Profile update — /api/mobile/v2/profile/*"""
import base64
import binascii

from odoo import http
from odoo.http import request

from ._common import (safe_endpoint, get_payload, ok, fail, current_partner,
                      require_auth, img_url, decode_image_upload)
from .auth import _serialize_user


class MobileProfileAPI(http.Controller):

    @http.route('/api/mobile/v2/profile/update', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def update_profile(self, **kw):
        p = get_payload()
        partner = current_partner()
        vals = {}
        for k in ('name', 'phone', 'mobile', 'email'):
            if k in p and p[k]:
                vals[k] = p[k]
        if p.get('lang'):
            vals['lang'] = p['lang']
        if vals:
            partner.sudo().write(vals)
        return ok({'user': _serialize_user(partner)})

    @http.route('/api/mobile/v2/profile/change-password', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def change_password(self, **kw):
        p = get_payload()
        old = p.get('old_password') or ''
        new = p.get('new_password') or ''
        if not new or len(new) < 6:
            return fail('WEAK_PASSWORD', 'Password must be at least 6 characters')
        partner = current_partner()
        user = partner.user_ids[:1]
        if not user:
            return fail('NO_USER', 'No user account')
        try:
            # Odoo 18: session.authenticate takes a credential dict, so the old
            # 3-arg call raised TypeError (endpoint always said "wrong
            # password"). Verify the old password directly, like login does.
            user.with_user(user.id)._check_credentials(
                {'password': old, 'type': 'password'},
                {'interactive': False})
        except Exception:
            return fail('WRONG_PASSWORD', 'Old password is wrong', 401)
        user.sudo().write({'password': new})
        return ok({'changed': True})

    @http.route('/api/mobile/v2/profile/avatar', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def upload_avatar(self, **kw):
        """Accepts {image_base64: '...'} and writes to res.partner.image_1920.
        Returns the new cache-busted avatar URL so the app refreshes instantly."""
        p = get_payload()
        b64 = (p.get('image_base64') or '').strip()
        if not b64:
            return fail('NO_IMAGE', 'image_base64 is required')
        # Validate: real image bytes within the size cap (previously any
        # base64 was accepted, so a client could store a huge or non-image
        # blob as the avatar).
        raw, err = decode_image_upload(b64)
        if err:
            return fail('BAD_IMAGE', err, 400)
        partner = current_partner()
        # Odoo expects base64-encoded bytes on Binary fields, not raw.
        b64_clean = base64.b64encode(raw)
        partner.sudo().write({'image_1920': b64_clean})
        # Return both the URL (for next session) AND an inline data URI
        # so the client can render the new photo instantly without
        # waiting for Odoo's /web/image to authorize the request.
        avatar_url = img_url('res.partner', partner.id, 'image_512',
                              unique=partner.write_date)
        data_uri = 'data:image/jpeg;base64,' + b64_clean.decode('ascii')
        return ok({
            'avatar_url':      avatar_url,
            'avatar_data_uri': data_uri,
        })

    @http.route('/api/mobile/v2/profile/delete', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def delete_account(self, **kw):
        """Soft-delete: archive the partner + revoke all sessions.
        We don't truly delete because of order references."""
        partner = current_partner()
        request.env['mobile.session'].sudo().search([
            ('partner_id', '=', partner.id),
        ]).write({'is_revoked': True})
        partner.sudo().write({'active': False})
        return ok({'deleted': True})
