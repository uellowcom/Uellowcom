from collections import defaultdict

from odoo import fields, models
from odoo.tools import format_datetime


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pc_fmt(self, amount):
        """Format an amount with the session currency's decimal places."""
        dp = (self.currency_id.decimal_places
              if self.currency_id else 2)
        return '{:,.{dp}f}'.format(amount or 0.0, dp=dp)

    def get_closing_report_data(self):
        """Build the full cashier-closing dataset for the QWeb reports.

        Cash reconciliation note: the session's cash journal statement holds
        one aggregate line per cash payment batch plus any manual cash-in/out
        moves, so ``expected = opening + sum(statement lines)`` and the manual
        component is ``sum(statement lines) - net cash payments``. This
        reconciles for any session, not just the sample one.
        """
        self.ensure_one()
        cur = self.currency_id
        orders = self.order_ids
        order_cnt = len(orders)

        total = sum(orders.mapped('amount_total'))          # net (refunds -ve)
        tax = sum(orders.mapped('amount_tax'))
        refund_orders = orders.filtered(lambda o: o.amount_total < 0)
        refunds = sum(refund_orders.mapped('amount_total'))  # negative
        gross = total - refunds                              # positive gross
        avg = (total / order_cnt) if order_cnt else 0.0

        disc = 0.0
        for line in orders.mapped('lines'):
            if line.discount:
                disc += (line.price_unit * line.qty) * (line.discount / 100.0)

        # payments grouped by method
        pays = self.env['pos.payment']._read_group(
            [('pos_order_id.session_id', '=', self.id)],
            groupby=['payment_method_id'],
            aggregates=['amount:sum', '__count'])
        payments = []
        cash_net = 0.0
        collected = 0.0
        for method, amt, cnt in pays:
            amt = amt or 0.0
            collected += amt
            payments.append({
                'name': method.name or '—',
                'cnt': cnt,
                'amt': self._pc_fmt(amt),
                'cash': bool(method.is_cash_count),
            })
            if method.is_cash_count:
                cash_net += amt

        # cash reconciliation
        start = self.cash_register_balance_start or 0.0
        counted = self.cash_register_balance_end_real or 0.0
        stmt = self.env['account.bank.statement.line'].search(
            [('pos_session_id', '=', self.id)])
        stmt_sum = sum(stmt.mapped('amount'))
        manual = stmt_sum - cash_net
        expected = start + stmt_sum
        difference = counted - expected
        eps = 10 ** -(cur.decimal_places if cur else 2)
        balanced = abs(difference) < eps

        # top products
        agg = defaultdict(lambda: [0.0, 0.0])
        for line in orders.mapped('lines'):
            a = agg[line.product_id]
            a[0] += line.qty
            a[1] += line.price_subtotal_incl
        top = sorted(agg.items(), key=lambda kv: kv[1][1], reverse=True)[:8]
        top_list = [{
            'name': prod.display_name,
            'qty': ('%g' % qty),
            'total': self._pc_fmt(tot),
        } for prod, (qty, tot) in top]

        def dt(val):
            return format_datetime(
                self.env, val, dt_format='dd MMM yyyy · HH:mm') if val else '—'

        duration = '—'
        if self.start_at and self.stop_at:
            secs = (self.stop_at - self.start_at).total_seconds()
            duration = '%dh %02dm' % (secs // 3600, (secs % 3600) // 60)

        return {
            'company': self.company_id.name or 'Uellow',
            'config': self.config_id.name or '—',
            'session': self.name,
            'cashier': (self.user_id.partner_id.name
                        or self.user_id.name or '—'),
            'currency': cur.name if cur else '',
            'opened': dt(self.start_at),
            'closed': dt(self.stop_at),
            'printed': dt(fields.Datetime.now()),
            'duration': duration,
            'orders': order_cnt,
            'net': self._pc_fmt(total),
            'gross': self._pc_fmt(gross),
            'refunds': self._pc_fmt(refunds),
            'refund_cnt': len(refund_orders),
            'discounts': self._pc_fmt(-disc if disc else 0.0),
            'tax': self._pc_fmt(tax),
            'avg': self._pc_fmt(avg),
            'payments': payments,
            'total_collected': self._pc_fmt(collected),
            'r_opening': self._pc_fmt(start),
            'r_cash_sales': self._pc_fmt(cash_net),
            'r_manual': self._pc_fmt(manual),
            'r_expected': self._pc_fmt(expected),
            'r_counted': self._pc_fmt(counted),
            'r_difference': self._pc_fmt(difference),
            'balanced': balanced,
            'diff_color': '#2E9E6B' if balanced else '#c0392b',
            'top': top_list,
        }
