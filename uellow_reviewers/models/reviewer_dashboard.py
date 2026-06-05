# -*- coding: utf-8 -*-
"""Reviewers 2.0 — big admin dashboard (all program statistics)."""
from datetime import datetime, timedelta

from odoo import api, fields, models


class ReviewerDashboard(models.TransientModel):
    _name = 'reviewer.dashboard'
    _description = 'Reviewers program dashboard'

    reviewers_total = fields.Integer(readonly=True)
    reviewers_approved = fields.Integer(readonly=True)
    reviewers_pending = fields.Integer(readonly=True)
    reviewers_online = fields.Integer(readonly=True)
    reviewers_suspended = fields.Integer(readonly=True)

    requests_total = fields.Integer(readonly=True)
    requests_pending = fields.Integer(readonly=True)
    requests_active = fields.Integer(readonly=True)
    requests_completed = fields.Integer(readonly=True)
    requests_month = fields.Integer(readonly=True,
                                    string='Completed this month')
    avg_response_minutes = fields.Float(readonly=True,
                                        string='Avg accept time (min)')

    points_issued = fields.Integer(readonly=True)
    points_redeemed = fields.Integer(readonly=True)
    points_outstanding = fields.Integer(readonly=True)
    profit_share_paid = fields.Float(readonly=True,
                                     string='Profit share credited (KD)')
    wallets_total = fields.Float(readonly=True,
                                 string='Wallet balances owed (KD)')
    payouts_pending = fields.Integer(readonly=True)
    payouts_pending_amount = fields.Float(readonly=True)
    payouts_paid_amount = fields.Float(readonly=True)

    top_reviewers_html = fields.Html(readonly=True, sanitize=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        Prof = self.env['reviewer.profile'].sudo()
        Req = self.env['review.request'].sudo()
        Pt = self.env['reviewer.point'].sudo()
        Pay = self.env['reviewer.commission'].sudo()

        profs = Prof.search([])
        res['reviewers_total'] = len(profs)
        res['reviewers_approved'] = len(profs.filtered(
            lambda r: r.state == 'approved'))
        res['reviewers_pending'] = len(profs.filtered(
            lambda r: r.state == 'pending'))
        res['reviewers_online'] = len(profs.filtered('is_online'))
        res['reviewers_suspended'] = len(profs.filtered(
            lambda r: r.state == 'suspended'))

        res['requests_total'] = Req.search_count([])
        res['requests_pending'] = Req.search_count(
            [('state', '=', 'pending')])
        res['requests_active'] = Req.search_count(
            [('state', 'in', ('accepted', 'active'))])
        res['requests_completed'] = Req.search_count(
            [('state', '=', 'completed')])
        month_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0)
        res['requests_month'] = Req.search_count([
            ('state', '=', 'completed'),
            ('completed_at', '>=', month_start)])
        accepted = Req.search([('accepted_at', '!=', False)], limit=300,
                              order='id desc')
        deltas = [(r.accepted_at - r.create_date).total_seconds() / 60.0
                  for r in accepted if r.create_date and r.accepted_at
                  and r.accepted_at >= r.create_date]
        res['avg_response_minutes'] = round(
            sum(deltas) / len(deltas), 1) if deltas else 0.0

        pts = Pt.search([])
        res['points_issued'] = sum(p.points for p in pts if p.points > 0)
        res['points_redeemed'] = -sum(p.points for p in pts
                                      if p.points < 0)
        res['points_outstanding'] = sum(pts.mapped('points'))
        res['profit_share_paid'] = sum(p.kd_amount for p in pts
                                       if p.source == 'profit_share')
        res['wallets_total'] = sum(profs.mapped('wallet_balance'))
        pend = Pay.search([('state', '=', 'pending')])
        res['payouts_pending'] = len(pend)
        res['payouts_pending_amount'] = sum(pend.mapped('amount'))
        res['payouts_paid_amount'] = sum(
            Pay.search([('state', '=', 'paid')]).mapped('amount'))

        # top reviewers (30 days: completed sessions + earnings)
        since = datetime.utcnow() - timedelta(days=30)
        rows = []
        for p in profs.filtered(lambda r: r.state == 'approved'):
            done = len(p.request_ids.filtered(
                lambda r: r.state == 'completed' and r.completed_at
                and r.completed_at >= since))
            earned = sum(x.kd_amount for x in p.point_ids
                         if x.kd_amount > 0 and x.create_date
                         and x.create_date >= since)
            pts30 = sum(x.points for x in p.point_ids
                        if x.points > 0 and x.create_date
                        and x.create_date >= since)
            if done or earned or pts30:
                rows.append((p, done, pts30, earned))
        rows.sort(key=lambda t: (-t[1], -t[3]))
        body = ''.join(
            '<tr><td style="padding:4px 10px">%d</td>'
            '<td style="padding:4px 10px">%s</td>'
            '<td style="padding:4px 10px;text-align:center">%d</td>'
            '<td style="padding:4px 10px;text-align:center">%d</td>'
            '<td style="padding:4px 10px;text-align:end;font-weight:bold;'
            'color:#1F8A40">%.3f</td></tr>'
            % (i + 1, p.display_name, done, pts30, earned)
            for i, (p, done, pts30, earned) in enumerate(rows[:10]))
        res['top_reviewers_html'] = (
            '<table class="table table-sm" style="max-width:560px">'
            '<thead><tr><th>#</th><th>Reviewer</th><th>Sessions 30d</th>'
            '<th>Points 30d</th><th style="text-align:end">KD 30d</th>'
            '</tr></thead><tbody>%s</tbody></table>'
            % (body or '<tr><td colspan="5" style="padding:8px;'
               'color:#999">No completed sessions in the last 30 days.'
               '</td></tr>'))
        return res

    @api.model
    def action_open(self):
        rec = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reviewers Dashboard',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': rec.id,
            'target': 'current',
        }

    def open_pending_reviewers(self):
        return self._lst('reviewer.profile', 'Pending reviewers',
                         [('state', '=', 'pending')])

    def open_pending_payouts(self):
        return self._lst('reviewer.commission', 'Pending payouts',
                         [('state', '=', 'pending')])

    def open_points(self):
        return self._lst('reviewer.point', 'Points ledger', [])

    def open_requests(self):
        return self._lst('review.request', 'Requests', [])

    def _lst(self, model, name, dom):
        return {'type': 'ir.actions.act_window', 'name': name,
                'res_model': model, 'view_mode': 'list,form',
                'domain': dom, 'target': 'current'}
