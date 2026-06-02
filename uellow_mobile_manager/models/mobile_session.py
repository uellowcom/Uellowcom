# -*- coding: utf-8 -*-
"""
mobile.session — One row per (device, user) authenticated app session.

History note: the original model used `device_id` as the only key and
`is_active` as a *computed* heartbeat flag (active = last_activity in
the last 30 min). The new v2 API uses this same model as the auth
token store, so we added:

  • partner_id   — relation to res.partner (was odoo_user_id int only)
  • token_hash   — sha256 of the bearer token (raw is never stored)
  • push_token   — alias of fcm_token kept for clarity
  • last_seen    — alias of last_activity kept for clarity
  • is_revoked   — real boolean for logout / admin kill-switch

`is_active` is now a STORED computed = (last_seen within 30min) AND (not
is_revoked). Legacy callers that wrote True/False directly are migrated
to is_revoked via the create()/write() overrides.
"""
from datetime import datetime, timedelta

from odoo import api, fields, models


class MobileSession(models.Model):
    _name = 'mobile.session'
    _description = 'Mobile App Active Sessions'
    _order = 'last_activity desc'

    # ─── Identity ────────────────────────────────────────────────────
    device_id = fields.Char(string='Device ID', index=True)
    device_name = fields.Char(string='Device Name')
    platform = fields.Selection([
        ('android', 'Android'),
        ('ios', 'iOS'),
    ], string='Platform')
    app_version = fields.Char(string='App Version')
    os_version = fields.Char(string='OS Version')

    # ─── User ────────────────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner', string='Customer', ondelete='cascade', index=True,
    )
    odoo_user_id = fields.Integer(
        string='Odoo User ID', default=0, index=True,
        help='Kept for backward compat with older clients.',
    )
    customer_name = fields.Char(string='Customer Name')
    customer_email = fields.Char(string='Customer Email')
    is_guest = fields.Boolean(string='Guest Session', default=True)

    # ─── Tokens ──────────────────────────────────────────────────────
    token_hash = fields.Char(
        string='Token (sha256)', index=True,
        help='SHA-256 of the bearer token issued at login. Raw token is '
             'never stored — only the hash, so a DB leak can\'t impersonate '
             'users.',
    )
    session_token = fields.Char(string='Legacy Session Token', index=True)
    fcm_token = fields.Char(string='FCM Push Token')
    push_token = fields.Char(string='Push Token (alias)')

    # ─── Context ─────────────────────────────────────────────────────
    ip_address = fields.Char(string='IP Address')
    country_code = fields.Char(
        string='Country Code', size=3,
        help='User\'s chosen country (ISO 3166-1 alpha-2). When set, '
             'the geo endpoint stops auto-suggesting a different country.',
    )
    chosen_lang = fields.Char(
        string='Chosen Language',
        help='User\'s manual language pick (e.g. "ar_001"). Sticks across '
             'sessions until the user changes it from account settings.',
    )
    website_id = fields.Many2one(
        'website', string='Website',
        default=lambda self: self.env['website'].search([], limit=1),
    )

    # ─── Activity ────────────────────────────────────────────────────
    first_seen = fields.Datetime(string='First Seen', default=fields.Datetime.now)
    last_activity = fields.Datetime(string='Last Seen', default=fields.Datetime.now)
    last_seen = fields.Datetime(
        string='Last Seen (alias)',
        compute='_compute_last_seen', inverse='_inverse_last_seen', store=False,
        help='Read/write alias of last_activity, used by v2 API.',
    )

    is_revoked = fields.Boolean(string='Revoked', default=False,
                                help='Set on logout — invalidates the token.')
    is_active = fields.Boolean(
        string='Currently Active', default=True,
        compute='_compute_is_active', store=True,
        help='True iff last_seen ≤ 30min AND not revoked.',
    )

    # ─── Compute / inverse ───────────────────────────────────────────
    @api.depends('last_activity', 'is_revoked')
    def _compute_is_active(self):
        threshold = datetime.now() - timedelta(minutes=30)
        for rec in self:
            rec.is_active = bool(
                rec.last_activity
                and rec.last_activity > threshold
                and not rec.is_revoked
            )

    @api.depends('last_activity')
    def _compute_last_seen(self):
        for rec in self:
            rec.last_seen = rec.last_activity

    def _inverse_last_seen(self):
        for rec in self:
            if rec.last_seen:
                rec.last_activity = rec.last_seen

    # ─── Legacy-friendly overrides ───────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Map v2 names to internal storage
            if 'push_token' in vals and 'fcm_token' not in vals:
                vals['fcm_token'] = vals['push_token']
            if 'last_seen' in vals:
                vals['last_activity'] = vals.pop('last_seen')
            if vals.get('partner_id') and not vals.get('odoo_user_id'):
                user = self.env['res.users'].sudo().search(
                    [('partner_id', '=', vals['partner_id'])], limit=1)
                if user:
                    vals['odoo_user_id'] = user.id
                    vals['customer_email'] = user.email or ''
            if vals.get('partner_id') and not vals.get('customer_name'):
                p = self.env['res.partner'].sudo().browse(vals['partner_id'])
                vals['customer_name'] = p.name or ''
            if vals.get('partner_id'):
                vals.setdefault('is_guest', False)
            # Older callers used is_active=False to mean "revoked".
            if vals.get('is_active') is False:
                vals['is_revoked'] = True
                vals.pop('is_active', None)
        return super().create(vals_list)

    def write(self, vals):
        if 'push_token' in vals and 'fcm_token' not in vals:
            vals['fcm_token'] = vals['push_token']
        if 'last_seen' in vals:
            vals['last_activity'] = vals.pop('last_seen')
        if vals.get('is_active') is False:
            vals['is_revoked'] = True
            vals.pop('is_active', None)
        return super().write(vals)

    # ─── Heartbeat / utilities ───────────────────────────────────────
    @api.model
    def get_active_count(self):
        threshold = datetime.now() - timedelta(minutes=30)
        return self.search_count([
            ('last_activity', '>=', threshold),
            ('is_revoked', '=', False),
        ])

    @api.model
    def register_session(self, device_id, platform, app_version, fcm_token=None,
                         user_id=None, device_name=None, os_version=None, ip=None):
        """Legacy V1 helper kept for older clients. Returns the session ID.

        v2 clients should call /api/mobile/v2/auth/login which returns a
        bearer token and creates the session row itself."""
        existing = self.search([('device_id', '=', device_id)], limit=1) if device_id else self.browse()
        vals = {
            'last_activity': datetime.now(),
            'app_version': app_version,
            'is_guest': not user_id,
        }
        if fcm_token:
            vals['fcm_token'] = fcm_token
        if user_id:
            try:
                user = self.env['res.users'].sudo().browse(int(user_id))
                vals['odoo_user_id'] = user.id
                vals['partner_id'] = user.partner_id.id
                vals['customer_name'] = user.partner_id.name or ''
                vals['customer_email'] = user.email or ''
            except Exception:
                pass
        if existing:
            existing.write(vals)
            return existing.id
        vals.update({
            'device_id': device_id or '',
            'platform': platform or 'android',
            'device_name': device_name or '',
            'os_version': os_version or '',
            'ip_address': ip or '',
            'first_seen': datetime.now(),
        })
        return self.create(vals).id
