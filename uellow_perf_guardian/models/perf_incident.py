"""Incident tracking — opens when a critical alert fires; closes when
synthetic probes return OK consecutively for 3 minutes. MTTR = close - open.
"""
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PerfIncident(models.Model):
    _name = 'uellow.perf.incident'
    _description = 'Uellow Performance — incident'
    _order = 'opened_at desc'

    name = fields.Char(required=True)
    category = fields.Selection([
        ('synthetic', 'Synthetic'),
        ('cache', 'Cache'),
        ('system', 'System'),
        ('error', '5xx errors'),
        ('ssl', 'SSL/Domain'),
        ('manual', 'Manual'),
    ], required=True, index=True)
    opened_at = fields.Datetime(required=True, default=fields.Datetime.now,
        index=True)
    closed_at = fields.Datetime(index=True)
    mttr_minutes = fields.Float(string='Duration (min)',
        compute='_compute_mttr', store=True)
    status = fields.Selection([
        ('open', 'Open'),
        ('closed', 'Closed'),
    ], default='open', index=True)
    sample_alert_id = fields.Many2one('uellow.perf.alert', ondelete='set null')
    note = fields.Text()

    @api.depends('opened_at', 'closed_at')
    def _compute_mttr(self):
        for r in self:
            if r.opened_at and r.closed_at:
                r.mttr_minutes = (r.closed_at - r.opened_at).total_seconds() / 60
            else:
                r.mttr_minutes = 0

    @api.model
    def open_incident(self, category, name, alert=None):
        """Open a new incident unless one is already open for this category."""
        existing = self.search([
            ('status', '=', 'open'), ('category', '=', category)], limit=1)
        if existing:
            return existing
        return self.create({
            'name': name[:255], 'category': category,
            'sample_alert_id': alert.id if alert else False,
        })

    @api.model
    def close_open(self, category):
        """Close all open incidents in this category."""
        for r in self.search([('status', '=', 'open'),
                              ('category', '=', category)]):
            r.write({'status': 'closed',
                     'closed_at': fields.Datetime.now()})

    @api.model
    def cron_auto_close(self):
        """Auto-close incidents whose category has had healthy synthetic
        probes for the last 3 minutes."""
        cutoff = fields.Datetime.now() - timedelta(minutes=3)
        Synth = self.env['uellow.perf.synthetic'].sudo()
        for inc in self.search([('status', '=', 'open'),
                                ('category', '=', 'synthetic')]):
            recent = Synth.search([
                ('create_date', '>=', cutoff)])
            if recent and all(r.ok and (r.total_ms or 0) < 4000 for r in recent):
                inc.write({'status': 'closed',
                           'closed_at': fields.Datetime.now()})
        return True
