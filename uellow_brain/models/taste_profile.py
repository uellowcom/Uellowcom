"""Uellow Brain — Phase 2: Taste Profile (per-customer affinity).

A COMPACT precomputed row per active customer holding category weights +
a price band. Built by a cron from real signals (orders strongest, cart,
recently-viewed) with INTEREST DECAY and PURCHASE-CYCLE awareness:
 - `one_off` categories already PURCHASED are suppressed (post-purchase
   pivot — don't flood with watches after buying one).
 - `repeat` categories stay/boost (consumables).
At request time we read ONE small row (members) or parse the X-Taste
header (guests) → light re-rank of the top brain_score candidates.
Everything is guarded; disabled engine = inert.
"""
import json
import logging
from datetime import datetime, timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductPublicCategoryBrain(models.Model):
    _inherit = 'product.public.category'

    brain_repeat = fields.Selection([
        ('one_off', 'One-off (durable — rarely repurchased)'),
        ('repeat', 'Repeat (consumable — replenished)'),
        ('browse', 'Browse (fashion/impulse)'),
    ], default='browse', string='Purchase behavior',
        help='Used by Uellow Brain interest lifecycle: one-off categories '
             'are suppressed after purchase; repeat categories schedule '
             'replenishment.')


class UellowTasteProfile(models.Model):
    _name = 'uellow.taste.profile'
    _description = 'Brain — customer taste profile'
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', required=True, index=True,
                                 ondelete='cascade')
    data = fields.Text('Affinity JSON', default='{}')
    price_band_lo = fields.Float()
    price_band_hi = fields.Float()
    top_categories = fields.Char('Top categories (debug)')
    updated_at = fields.Datetime()

    _sql_constraints = [
        ('uniq_partner', 'unique(partner_id)', 'One profile per partner.'),
    ]

    # ── read side (request time, cheap) ────────────────────────────
    @api.model
    def get_dict(self, partner_id):
        """Return the affinity dict for a partner, or {} (one indexed read)."""
        if not partner_id:
            return {}
        rec = self.sudo().search([('partner_id', '=', partner_id)], limit=1)
        if not rec or not rec.data:
            return {}
        try:
            return json.loads(rec.data)
        except Exception:
            return {}

    @api.model
    def affinity(self, prof, product):
        """Multiplier in ~[0.6 .. 1.8] for a product given a profile dict.
        prof = {'cats': {id: weight}, 'lo': x, 'hi': y}. Neutral 1.0 when
        no profile."""
        if not prof:
            return 1.0
        try:
            cats = prof.get('cats') or {}
            m = 1.0
            if cats:
                hit = 0.0
                for c in product.public_categ_ids:
                    w = cats.get(str(c.id)) or cats.get(c.id)
                    if w:
                        hit = max(hit, float(w))
                m += min(hit, 1.0) * 0.8   # up to +0.8 for strong category
            lo, hi = prof.get('lo'), prof.get('hi')
            if lo and hi and lo <= (product.list_price or 0) <= hi:
                m += 0.1
            return max(0.6, min(1.8, m))
        except Exception:
            return 1.0

    # ── build side (cron, off request path) ────────────────────────
    @api.model
    def _cron_build_profiles(self, limit_partners=4000):
        Cfg = self.env.get('uellow.brain.config')
        if Cfg is None:
            return
        cfg = Cfg.get_config()
        if not cfg.enabled or cfg.personalization_mode in ('off',):
            return
        self.sudo()._build_profiles(cfg, limit_partners)

    @api.model
    def _build_profiles(self, cfg, limit_partners=4000):
        cr = self.env.cr
        since = datetime.utcnow() - timedelta(days=120)
        # active partners: ordered or have a draft cart recently
        cr.execute("""
            SELECT DISTINCT partner_id FROM sale_order
            WHERE partner_id IS NOT NULL AND (
                  (state IN ('sale','done') AND date_order >= %s)
                  OR state = 'draft')
            LIMIT %s
        """, (since, limit_partners))
        pids = [r[0] for r in cr.fetchall()]
        Cat = self.env['product.public.category'].sudo()
        # repeat-behavior map
        repeat = {c.id: c.brain_repeat for c in Cat.search([])}
        half = max(int(cfg.il_decay_halflife_days or 3), 1)
        topn = max(int(cfg.il_balanced_interests or 4), 1)
        pivot = bool(cfg.il_post_purchase_pivot)
        now = datetime.utcnow()
        built = 0
        for pid in pids:
            try:
                cat_w = {}
                prices = []
                # template-level signals (no fragile m2m join): one row per
                # template the partner bought/carted, with the strongest
                # state + most recent date.
                cr.execute("""
                    SELECT pt.id,
                           bool_or(so.state='draft') AS in_cart,
                           bool_or(so.state IN ('sale','done')) AS purchased,
                           max(so.date_order) AS last_dt,
                           max(pt.list_price) AS price
                    FROM sale_order so
                    JOIN sale_order_line sol ON sol.order_id = so.id
                    JOIN product_product pp ON pp.id = sol.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE so.partner_id = %s
                      AND (so.state IN ('sale','done') OR so.state='draft')
                    GROUP BY pt.id
                """, (pid,))
                rows = cr.fetchall()
                tids = [r[0] for r in rows]
                Tmpl = self.env['product.template'].sudo()
                catmap = {t.id: t.public_categ_ids.ids
                          for t in Tmpl.browse(tids)}
                for _tid, in_cart, purchased, dt, price in rows:
                    if price:
                        prices.append(float(price))
                    base = 1.0 if in_cart else 0.9
                    if purchased and not in_cart and dt:
                        days = max((now - dt.replace(tzinfo=None)).days, 0)
                        base *= 0.5 ** (days / half)
                    for cid in catmap.get(_tid, []):
                        beh = repeat.get(cid, 'browse')
                        w = base
                        if purchased and not in_cart and beh == 'one_off' \
                                and pivot:
                            w = -0.5            # post-purchase pivot
                        elif purchased and beh == 'repeat':
                            w = base * 1.3      # consumables stay hot
                        cat_w[cid] = cat_w.get(cid, 0.0) + w
                if not cat_w:
                    # clear stale profile if any
                    old = self.sudo().search([('partner_id', '=', pid)])
                    if old:
                        old.write({'data': '{}', 'updated_at': now})
                    continue
                # normalize to [0..1], keep top N positive
                mx = max(cat_w.values()) or 1.0
                norm = {str(k): round(max(v, 0) / mx, 3)
                        for k, v in cat_w.items() if v > 0}
                top = dict(sorted(norm.items(), key=lambda kv: -kv[1])[:topn])
                prices.sort()
                lo = hi = 0.0
                if prices:
                    lo = prices[max(0, int(len(prices) * 0.1))]
                    hi = prices[min(len(prices) - 1, int(len(prices) * 0.9))]
                data = json.dumps({'cats': top, 'lo': lo, 'hi': hi})
                rec = self.sudo().search([('partner_id', '=', pid)], limit=1)
                vals = {'data': data, 'price_band_lo': lo,
                        'price_band_hi': hi,
                        'top_categories': ','.join(top.keys()),
                        'updated_at': now}
                if rec:
                    rec.write(vals)
                else:
                    self.sudo().create(dict(vals, partner_id=pid))
                built += 1
            except Exception:
                _logger.debug('profile build failed for %s', pid,
                              exc_info=True)
            if built % 300 == 0:
                cr.commit()
        cr.commit()
        _logger.info('Uellow Brain: built %s taste profiles', built)
        return built

    # ── guest header parsing (no DB) ───────────────────────────────
    @api.model
    def parse_header(self, header):
        """Parse X-Taste header → profile dict. Format:
        'cat:12,45;price:10-30'. Returns {} on anything odd."""
        if not header:
            return {}
        try:
            out = {'cats': {}}
            for part in str(header).split(';'):
                if ':' not in part:
                    continue
                k, v = part.split(':', 1)
                k = k.strip().lower()
                if k in ('cat', 'cats'):
                    for cid in v.split(','):
                        cid = cid.strip()
                        if cid.isdigit():
                            out['cats'][cid] = 1.0
                elif k == 'price' and '-' in v:
                    a, b = v.split('-', 1)
                    out['lo'] = float(a or 0)
                    out['hi'] = float(b or 0)
            return out if out.get('cats') or out.get('lo') else {}
        except Exception:
            return {}
