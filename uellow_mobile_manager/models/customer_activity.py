# -*- coding: utf-8 -*-
"""Customer journey tracking — every screen the app shows, app open/close,
and key actions land here so the team can see exactly what a customer is
doing. Fed by POST /api/mobile/v2/track (batched from the app); read back
in the admin console (per-customer timeline + global recent feed)."""
from odoo import api, fields, models


class CustomerActivity(models.Model):
    _name = 'uellow.customer.activity'
    _description = 'Customer App Activity'
    _order = 'id desc'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', index=True, ondelete='cascade')
    # Groups events of one anonymous/guest run before login.
    session_token = fields.Char(string='Session', index=True)
    mobile_session_id = fields.Many2one('mobile.session', index=True)
    # app_open | app_close | screen_view | screen_leave | tap | search |
    # add_to_cart | remove_from_cart | checkout_start | order_placed | ...
    event = fields.Char(string='Event', index=True, required=True)
    screen = fields.Char(string='Screen / Route', index=True)
    label = fields.Char(string='Label')        # product name, query, etc.
    ref_model = fields.Char(string='Ref Model')  # e.g. product.template
    ref_id = fields.Integer(string='Ref Id')
    duration_ms = fields.Integer(string='Time on screen (ms)')
    platform = fields.Char(string='Platform')   # android / ios
    app_version = fields.Char(string='App Version')
    device = fields.Char(string='Device')
    website_id = fields.Many2one('website', index=True)
    meta = fields.Text(string='Extra (JSON)')
    # event time as reported by the device (falls back to create_date).
    event_time = fields.Datetime(string='Event Time', index=True)

    @api.model
    def record_batch(self, events, partner=None, session=None,
                     platform=None, app_version=None, device=None,
                     website=None):
        """Bulk-insert a batch of event dicts from the app. Defensive: skips
        malformed rows, caps the batch, never raises to the caller."""
        if not events:
            return 0
        vals = []
        pid = partner.id if partner else False
        sid = session.id if session else False
        wid = website.id if website else False
        for e in events[:200]:          # hard cap per call
            if not isinstance(e, dict):
                continue
            evt = (e.get('event') or '').strip()[:64]
            if not evt:
                continue
            ts = e.get('event_time') or e.get('ts')
            vals.append({
                'partner_id': pid,
                'session_token': (e.get('session_token')
                                  or (session.token_hash[:16]
                                      if session else False)),
                'mobile_session_id': sid,
                'event': evt,
                'screen': (e.get('screen') or '')[:128] or False,
                'label': (e.get('label') or '')[:256] or False,
                'ref_model': (e.get('ref_model') or '')[:64] or False,
                'ref_id': int(e['ref_id']) if str(
                    e.get('ref_id') or '').lstrip('-').isdigit() else False,
                'duration_ms': int(e['duration_ms']) if str(
                    e.get('duration_ms') or '').isdigit() else False,
                'platform': (platform or e.get('platform') or '')[:32] or False,
                'app_version': (app_version or e.get('app_version')
                                or '')[:32] or False,
                'device': (device or e.get('device') or '')[:128] or False,
                'website_id': wid,
                'meta': (e.get('meta') or False),
                'event_time': self._parse_ts(ts),
            })
        if not vals:
            return 0
        self.sudo().create(vals)
        return len(vals)

    @api.model
    def _parse_ts(self, ts):
        if not ts:
            return False
        try:
            # accept epoch millis, epoch secs, or 'YYYY-MM-DD HH:MM:SS'
            if isinstance(ts, (int, float)) or str(ts).isdigit():
                v = int(ts)
                if v > 1e12:        # millis
                    v = v // 1000
                return fields.Datetime.to_datetime(
                    __import__('datetime').datetime.utcfromtimestamp(v))
            return fields.Datetime.to_datetime(str(ts)[:19].replace('T', ' '))
        except Exception:
            return False
