# -*- coding: utf-8 -*-
"""Big admin dashboard (TransientModel form) + program Settings."""
from datetime import datetime, timedelta

from odoo import api, fields, models


class UellowAffiliateDashboard(models.TransientModel):
    _name = 'uellow.affiliate.dashboard'
    _description = 'Affiliate program dashboard'

    # agents
    agents_total = fields.Integer(readonly=True)
    agents_active = fields.Integer(readonly=True)
    agents_pending = fields.Integer(readonly=True)
    agents_suspended = fields.Integer(readonly=True)
    clicks_total = fields.Integer(readonly=True)
    # commissions
    comm_pending = fields.Monetary(readonly=True, currency_field='currency_id')
    comm_confirmed = fields.Monetary(readonly=True, currency_field='currency_id')
    comm_paid = fields.Monetary(readonly=True, currency_field='currency_id')
    comm_count = fields.Integer(readonly=True)
    # sales
    sales_total = fields.Monetary(readonly=True, currency_field='currency_id')
    sales_month = fields.Monetary(readonly=True, currency_field='currency_id')
    comm_month = fields.Monetary(readonly=True, currency_field='currency_id')
    orders_month = fields.Integer(readonly=True)
    conversion_pct = fields.Float(readonly=True, string='Click → order %')
    # workload
    awaiting_orders = fields.Integer(readonly=True,
                                     string='Orders awaiting review')
    awaiting_payouts = fields.Integer(readonly=True,
                                      string='Payout requests')
    payouts_requested_amount = fields.Monetary(
        readonly=True, currency_field='currency_id')
    payouts_paid_amount = fields.Monetary(
        readonly=True, currency_field='currency_id')
    top_agents_html = fields.Html(readonly=True, sanitize=False)
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        Aff = self.env['uellow.affiliate'].sudo()
        Comm = self.env['uellow.affiliate.commission'].sudo()
        Pay = self.env['uellow.affiliate.payout'].sudo()
        Ord = self.env['uellow.affiliate.order'].sudo()

        agents = Aff.search([])
        res['agents_total'] = len(agents)
        res['agents_active'] = len(agents.filtered(
            lambda a: a.state == 'active'))
        res['agents_pending'] = len(agents.filtered(
            lambda a: a.state == 'pending'))
        res['agents_suspended'] = len(agents.filtered(
            lambda a: a.state == 'suspended'))
        res['clicks_total'] = sum(agents.mapped('click_count'))

        comms = Comm.search([])
        res['comm_pending'] = sum(c.amount for c in comms
                                  if c.state == 'pending')
        res['comm_confirmed'] = sum(c.amount for c in comms
                                    if c.state == 'confirmed')
        res['comm_paid'] = sum(c.amount for c in comms if c.state == 'paid')
        res['comm_count'] = len(comms)
        good = comms.filtered(lambda c: c.state in ('confirmed', 'paid'))
        res['sales_total'] = sum(good.mapped('base_amount'))

        month_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0)
        month = comms.filtered(
            lambda c: c.create_date and c.create_date >= month_start
            and c.state != 'cancelled')
        res['sales_month'] = sum(month.mapped('base_amount'))
        res['comm_month'] = sum(month.mapped('amount'))
        res['orders_month'] = len(month)
        clicks = res['clicks_total'] or 0
        res['conversion_pct'] = round(
            (len(comms) / clicks * 100.0), 2) if clicks else 0.0

        res['awaiting_orders'] = Ord.search_count(
            [('state', '=', 'submitted')])
        pend_pay = Pay.search([('state', '=', 'requested')])
        res['awaiting_payouts'] = len(pend_pay)
        res['payouts_requested_amount'] = sum(pend_pay.mapped('amount'))
        res['payouts_paid_amount'] = sum(
            Pay.search([('state', '=', 'paid')]).mapped('amount'))

        # top 10 agents (30 days, confirmed+paid)
        since = datetime.utcnow() - timedelta(days=30)
        totals = {}
        for c in comms:
            if c.state in ('confirmed', 'paid') and c.create_date \
                    and c.create_date >= since:
                totals[c.affiliate_id] = \
                    totals.get(c.affiliate_id, 0.0) + c.amount
        ranked = sorted(totals.items(), key=lambda kv: -kv[1])[:10]
        rows = ''.join(
            '<tr><td style="padding:4px 10px">%d</td>'
            '<td style="padding:4px 10px">%s <span style="color:#999">'
            '(%s)</span></td>'
            '<td style="padding:4px 10px;text-align:end;font-weight:bold;'
            'color:#1F8A40">%.3f</td></tr>'
            % (i + 1, a.name, a.code, amt)
            for i, (a, amt) in enumerate(ranked))
        res['top_agents_html'] = (
            '<table class="table table-sm" style="max-width:480px">'
            '<thead><tr><th>#</th><th>Agent</th>'
            '<th style="text-align:end">30-day commission</th></tr></thead>'
            '<tbody>%s</tbody></table>' % (rows or
                '<tr><td colspan="3" style="padding:8px;color:#999">'
                'No confirmed commissions in the last 30 days yet.'
                '</td></tr>'))
        return res

    @api.model
    def action_open(self):
        rec = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Affiliate Dashboard',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': rec.id,
            'target': 'current',
        }

    # quick-nav buttons
    def open_agents(self):
        return self._open_list('uellow.affiliate', 'Agents', [])

    def open_awaiting_orders(self):
        return self._open_list('uellow.affiliate.order',
                               'Orders awaiting review',
                               [('state', '=', 'submitted')])

    def open_commissions(self):
        return self._open_list('uellow.affiliate.commission',
                               'Commissions', [])

    def open_payout_requests(self):
        return self._open_list('uellow.affiliate.payout',
                               'Payout requests',
                               [('state', '=', 'requested')])

    def _open_list(self, model, name, domain):
        return {
            'type': 'ir.actions.act_window',
            'name': name, 'res_model': model,
            'view_mode': 'list,form', 'domain': domain,
            'target': 'current',
        }


class UellowAffiliateSettings(models.TransientModel):
    _name = 'uellow.affiliate.settings'
    _description = 'Affiliate program settings'

    PREFIX = 'uellow_affiliate.'

    min_payout = fields.Float('Minimum payout amount', default=5.0)
    default_commission_pct = fields.Float(
        'Default commission % for new agents', default=5.0)
    cookie_days = fields.Integer(
        'Referral attribution window (days)', default=30,
        help='How long the website referral cookie keeps crediting the '
             'agent after the customer opens his link.')
    silver_threshold = fields.Float('Silver — monthly sales', default=500)
    gold_threshold = fields.Float('Gold — monthly sales', default=2000)
    platinum_threshold = fields.Float('Platinum — monthly sales',
                                      default=6000)
    silver_mult = fields.Float('Silver multiplier', default=1.10)
    gold_mult = fields.Float('Gold multiplier', default=1.25)
    platinum_mult = fields.Float('Platinum multiplier', default=1.40)

    _FIELDS = ['min_payout', 'default_commission_pct', 'cookie_days',
               'silver_threshold', 'gold_threshold', 'platinum_threshold',
               'silver_mult', 'gold_mult', 'platinum_mult']

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ICP = self.env['ir.config_parameter'].sudo()
        for f in self._FIELDS:
            raw = ICP.get_param(self.PREFIX + f, '')
            if raw:
                try:
                    res[f] = int(raw) if f == 'cookie_days' else float(raw)
                except Exception:
                    pass
        return res

    def action_save(self):
        ICP = self.env['ir.config_parameter'].sudo()
        for rec in self:
            for f in self._FIELDS:
                ICP.set_param(self.PREFIX + f, str(rec[f] or 0))
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'message': 'Affiliate settings saved ✓',
                           'type': 'success', 'sticky': False}}

    @api.model
    def action_open(self):
        rec = self.create({})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Affiliate Settings',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': rec.id,
            'target': 'current',
        }
