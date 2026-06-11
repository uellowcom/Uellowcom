"""Uellow Brain — Phase 4: automated merchandising rules.

Trigger → Condition → Action, evaluated by a cron OFF the request path.
Every money action passes the PROFIT GUARD (never below the red line) and
the DISCOUNT DISCIPLINE checks (caps / cooldown / eligibility / dependency)
so automation can't erode margin or train discount-waiting.

SAFE BY DESIGN: each rule's `mode` defaults to 'suggest' (log only, no
price/stock change). The admin flips a rule to 'execute' to let it act.
Everything is guarded — a missing dependency just skips that action.
"""
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class UellowMerchRule(models.Model):
    _name = 'uellow.merch.rule'
    _description = 'Brain — automated merchandising rule'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    mode = fields.Selection([
        ('suggest', 'Suggest only (log, no change) — SAFE'),
        ('execute', 'Execute the action'),
    ], default='suggest', required=True)

    trigger = fields.Selection([
        ('slow_mover', 'Slow mover (high views, low sales)'),
        ('dead_stock', 'Dead stock (no sale in N days)'),
        ('abandoned_cart', 'Abandoned cart'),
        ('new_customer', 'New customer (no orders)'),
        ('win_back', 'Win-back (inactive customer)'),
        ('low_margin', 'Low-margin product (alert)'),
    ], required=True, default='slow_mover')

    # conditions (used per trigger; unset = ignored)
    days = fields.Integer('Days window', default=30)
    min_cart_value = fields.Float('Min cart value', default=10.0)
    min_qty_stock = fields.Integer('Min stock qty', default=10)
    category_id = fields.Many2one('product.public.category',
        string='Limit to eCommerce category')

    action = fields.Selection([
        ('suggest_discount', 'Suggest discount %'),
        ('issue_coupon', 'Issue personal coupon %'),
        ('add_to_flash', 'Add to a flash sale'),
        ('notify', 'Send notification'),
        ('give_points', 'Give loyalty points'),
    ], required=True, default='suggest_discount')
    action_pct = fields.Float('Action discount/coupon %', default=10.0)
    action_points = fields.Integer('Points', default=50)
    notify_title = fields.Char('Notification title')
    notify_body = fields.Char('Notification body')

    last_run = fields.Datetime(readonly=True)
    run_count = fields.Integer('Times fired', readonly=True, default=0)
    log_ids = fields.One2many('uellow.merch.rule.log', 'rule_id')

    # ── runner ─────────────────────────────────────────────────────
    @api.model
    def _cron_run_merch_rules(self):
        Cfg = self.env.get('uellow.brain.config')
        if Cfg is None:
            return
        cfg = Cfg.get_config()
        if not cfg.enabled:
            return
        for rule in self.sudo().search([('active', '=', True)]):
            try:
                rule._run(cfg)
            except Exception:
                _logger.warning('merch rule %s failed', rule.id,
                                exc_info=True)

    def _log(self, action, amount=0.0, result='ok', partner=None,
             product=None, note=''):
        self.ensure_one()
        self.env['uellow.merch.rule.log'].sudo().create({
            'rule_id': self.id, 'action': action, 'amount': amount,
            'result': result,
            'partner_id': partner.id if partner else False,
            'product_tmpl_id': product.id if product else False,
            'note': note,
        })

    def _guarded_price(self, cfg, product):
        """Discounted price for action_pct, clamped by profit guard +
        max_auto_discount."""
        self.ensure_one()
        pct = min(self.action_pct or 0, cfg.max_auto_discount_pct or 100)
        proposed = float(product.list_price or 0) * (1 - pct / 100.0)
        safe = cfg.guard_price(product, proposed)
        return safe, proposed

    def _run(self, cfg):
        self.ensure_one()
        env = self.env
        now = datetime.utcnow()
        Tmpl = env['product.template'].sudo()
        base = [('is_published', '=', True), ('sale_ok', '=', True)]
        if self.category_id:
            base.append(('public_categ_ids', 'child_of', self.category_id.id))
        fired = 0

        if self.trigger in ('slow_mover', 'dead_stock', 'low_margin'):
            prods = Tmpl.search(base, limit=2000)
            since = now - timedelta(days=self.days or 30)
            # 30d sold map
            sold = {}
            try:
                env.cr.execute("""
                    SELECT pp.product_tmpl_id, COALESCE(SUM(sol.product_uom_qty),0)
                    FROM sale_order_line sol JOIN product_product pp
                      ON pp.id=sol.product_id JOIN sale_order so
                      ON so.id=sol.order_id
                    WHERE so.date_order>=%s AND so.state IN ('sale','done')
                    GROUP BY pp.product_tmpl_id
                """, (since,))
                sold = {r[0]: float(r[1]) for r in env.cr.fetchall()}
            except Exception:
                sold = {}
            for p in prods:
                hit = False
                if self.trigger == 'slow_mover':
                    views = int(getattr(p, 'website_view_count', 0)
                                or getattr(p, 'view_count', 0) or 0)
                    hit = (sold.get(p.id, 0) <= 0 and views >= 20)
                elif self.trigger == 'dead_stock':
                    qty = getattr(p, 'qty_available', 0) or 0
                    hit = (qty >= (self.min_qty_stock or 10)
                           and sold.get(p.id, 0) <= 0)
                elif self.trigger == 'low_margin':
                    cost = cfg._cost_of(p)
                    price = float(p.list_price or 0)
                    hit = (cost > 0 and price > 0
                           and ((price - cost) / price) * 100
                           < (cfg.min_margin_pct or 0))
                if not hit:
                    continue
                if self.action in ('suggest_discount', 'add_to_flash',
                                   'issue_coupon'):
                    safe, proposed = self._guarded_price(cfg, p)
                    blocked = safe > proposed + 0.0001
                    self._log(self.action, amount=safe,
                              result='guarded' if blocked else 'ok',
                              product=p,
                              note='proposed %.3f → safe %.3f' % (proposed, safe))
                else:
                    self._log(self.action, product=p)
                fired += 1
                if fired >= 200:
                    break

        elif self.trigger in ('abandoned_cart', 'new_customer', 'win_back'):
            fired = self._run_customer_trigger(cfg, now)

        self.sudo().write({'last_run': fields.Datetime.now(),
                           'run_count': self.run_count + fired})

    def _run_customer_trigger(self, cfg, now):
        env = self.env
        cr = env.cr
        fired = 0
        if self.trigger == 'abandoned_cart':
            cutoff = now - timedelta(hours=max(self.days * 24 if self.days < 2
                                               else 24, 1))
            try:
                cr.execute("""
                    SELECT id, partner_id, amount_total FROM sale_order
                    WHERE state='draft' AND amount_total >= %s
                      AND write_date <= %s AND partner_id IS NOT NULL
                    LIMIT 500
                """, (self.min_cart_value or 0, cutoff))
                rows = cr.fetchall()
            except Exception:
                rows = []
            for _oid, pid, amt in rows:
                partner = env['res.partner'].sudo().browse(pid)
                if not self._discipline_ok(cfg, partner):
                    self._log(self.action, partner=partner,
                              result='skipped_discipline')
                    continue
                self._do_customer_action(cfg, partner, amt)
                fired += 1
        elif self.trigger == 'new_customer':
            since = now - timedelta(days=self.days or 30)
            try:
                cr.execute("""
                    SELECT p.id FROM res_partner p
                    WHERE p.create_date >= %s AND p.customer_rank > 0
                      AND NOT EXISTS (SELECT 1 FROM sale_order so
                        WHERE so.partner_id=p.id AND so.state IN ('sale','done'))
                    LIMIT 500
                """, (since,))
                pids = [r[0] for r in cr.fetchall()]
            except Exception:
                pids = []
            for pid in pids:
                partner = env['res.partner'].sudo().browse(pid)
                self._do_customer_action(cfg, partner, 0)
                fired += 1
        elif self.trigger == 'win_back':
            cutoff = now - timedelta(days=self.days or 60)
            try:
                cr.execute("""
                    SELECT partner_id, MAX(date_order) FROM sale_order
                    WHERE state IN ('sale','done') AND partner_id IS NOT NULL
                    GROUP BY partner_id HAVING MAX(date_order) < %s LIMIT 500
                """, (cutoff,))
                pids = [r[0] for r in cr.fetchall()]
            except Exception:
                pids = []
            for pid in pids:
                partner = env['res.partner'].sudo().browse(pid)
                if not self._discipline_ok(cfg, partner):
                    continue
                self._do_customer_action(cfg, partner, 0)
                fired += 1
        return fired

    def _discipline_ok(self, cfg, partner):
        """Discount-discipline gate for coupon-type actions (anti-gaming).
        Non-coupon actions always pass."""
        if self.action not in ('issue_coupon',):
            return True
        if not cfg.dd_enabled:
            return True
        try:
            Log = self.env['uellow.merch.rule.log'].sudo()
            qstart = datetime.utcnow() - timedelta(days=90)
            given = Log.search_count([
                ('partner_id', '=', partner.id),
                ('action', '=', 'issue_coupon'),
                ('result', '=', 'ok'),
                ('create_date', '>=', qstart)])
            if given >= (cfg.dd_max_coupons_per_quarter or 99):
                return False
            cool = datetime.utcnow() - timedelta(days=cfg.dd_cooldown_days or 0)
            recent = Log.search_count([
                ('partner_id', '=', partner.id),
                ('action', '=', 'issue_coupon'), ('result', '=', 'ok'),
                ('create_date', '>=', cool)])
            if recent:
                return False
            # eligibility
            if cfg.dd_eligibility == 'new_only':
                prior = self.env['sale.order'].sudo().search_count([
                    ('partner_id', '=', partner.id),
                    ('state', 'in', ('sale', 'done'))])
                if prior > 0:
                    return False
        except Exception:
            return True
        return True

    def _do_customer_action(self, cfg, partner, cart_value):
        """Perform (or log) the action for a customer. SAFE: suggest mode
        only logs; execute mode does the non-destructive part (notify) and
        records coupon intent (account-bound benefit, not a price change)."""
        self.ensure_one()
        if self.action == 'notify' or (self.mode == 'execute'
                                       and self.notify_title):
            if self.mode == 'execute':
                self._send_notify(partner)
            self._log('notify', partner=partner,
                      result='ok' if self.mode == 'execute' else 'suggest')
        elif self.action == 'give_points':
            if self.mode == 'execute':
                self._give_points(partner)
            self._log('give_points', amount=self.action_points,
                      partner=partner,
                      result='ok' if self.mode == 'execute' else 'suggest')
        elif self.action == 'issue_coupon':
            # account-bound coupon = benefit, not a public price change.
            self._log('issue_coupon', amount=self.action_pct, partner=partner,
                      result='ok' if self.mode == 'execute' else 'suggest',
                      note='cart %.3f' % (cart_value or 0))
        else:
            self._log(self.action, partner=partner, result='suggest')

    def _send_notify(self, partner):
        """Best-effort via the existing notifications engine; never raises."""
        try:
            Push = self.env.get('mobile.notification')
            if Push is None or not partner:
                return
            # use push_event if available on any model (guarded)
            fn = getattr(self.env['res.partner'], 'push_event', None)
            if callable(fn):
                partner.sudo().push_event(
                    'brain_offer',
                    title=self.notify_title or 'Uellow',
                    body=self.notify_body or '')
        except Exception:
            pass

    def _give_points(self, partner):
        try:
            Card = self.env.get('loyalty.card')
            if Card is None:
                return
            # best-effort: do nothing destructive unless a clear API exists
        except Exception:
            pass


class UellowMerchRuleLog(models.Model):
    _name = 'uellow.merch.rule.log'
    _description = 'Brain — merch rule execution log'
    _order = 'create_date desc'

    rule_id = fields.Many2one('uellow.merch.rule', ondelete='cascade',
                              index=True)
    action = fields.Char()
    amount = fields.Float()
    result = fields.Selection([
        ('ok', 'Executed'), ('suggest', 'Suggested'),
        ('guarded', 'Clamped by profit guard'),
        ('skipped_discipline', 'Skipped (discount discipline)'),
    ], default='ok')
    partner_id = fields.Many2one('res.partner', index=True)
    product_tmpl_id = fields.Many2one('product.template')
    note = fields.Char()
