# -*- coding: utf-8 -*-
"""Uellow Brain — AI email campaign generator.

Builds a ready-to-send marketing email: Brain picks the products (by
brain_score / discounts / new / category), respects the profit guard
(skips below-cost), designs a responsive branded HTML body, and creates a
draft `mailing.mailing` for review + send. This is the "Brain makes a
template, fills it with products, designs it and sends it" piece — fully
under Uellow Brain.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

YELLOW = '#F5C320'
DARK = '#412402'


class BrainCampaign(models.TransientModel):
    _name = 'uellow.brain.campaign'
    _description = 'Uellow Brain — AI email campaign'

    subject = fields.Char(required=True, default='Picked for you · مختارة لك ✨')
    headline = fields.Char(default='Handpicked for you', required=True)
    subheadline = fields.Char(default='Top deals our engine recommends')
    strategy = fields.Selection([
        ('best_match', '🧠 Best Match (Brain score)'),
        ('discounts', '🔥 Biggest discounts'),
        ('new', '🆕 New arrivals'),
        ('category', '📦 From a category'),
    ], default='best_match', required=True)
    category_id = fields.Many2one('product.public.category', string='Category')
    product_count = fields.Integer(default=8, required=True)
    columns = fields.Selection([('1', '1'), ('2', '2')], default='2',
                               string='Columns')
    mailing_list_id = fields.Many2one('mailing.list', string='Audience list',
        help='Leave empty to target all customers (res.partner).')
    cta_label = fields.Char(default='Shop now')

    # ── product selection (profit-guarded) ───────────────────────────────
    def _pick_products(self):
        self.ensure_one()
        Tmpl = self.env['product.template'].sudo()
        Cfg = self.env.get('uellow.brain.config')
        cfg = Cfg.get_config() if Cfg is not None else None
        dom = [('is_published', '=', True), ('sale_ok', '=', True),
               ('website_published', '=', True)]
        order = 'brain_score desc' if 'brain_score' in Tmpl._fields else 'website_sequence'
        if self.strategy == 'discounts':
            dom.append(('compare_list_price', '>', 0))
            order = 'write_date desc'
        elif self.strategy == 'new':
            order = 'create_date desc'
        elif self.strategy == 'category' and self.category_id:
            dom.append(('public_categ_ids', 'in', self.category_id.ids))
        pool = Tmpl.search(dom, order=order, limit=max(self.product_count, 1) * 4)
        out = []
        for p in pool:
            # profit guard — never feature a below-cost product in a campaign
            if cfg and cfg.block_below_cost:
                try:
                    cost = cfg._cost_of(p)
                    price = float(p.list_price or 0)
                    if cost > 0 and price > 0 and price < cost:
                        continue
                except Exception:
                    pass
            out.append(p)
            if len(out) >= self.product_count:
                break
        return out

    # ── responsive HTML email ─────────────────────────────────────────────
    def _base_url(self):
        return (self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url') or 'https://www.uellow.com').rstrip('/')

    def _money(self, p):
        cur = p.currency_id or self.env.company.currency_id
        amt = p.list_price or 0.0
        s = '%.3f' % amt
        return ('%s %s' % (s, cur.symbol or 'KD')) if (cur.position != 'before') \
            else ('%s %s' % (cur.symbol or 'KD', s))

    def _card(self, p, base, width_pct):
        url = '%s%s' % (base, p.website_url or '/shop')
        img = '%s/web/image/product.template/%d/image_512' % (base, p.id)
        name = (p.name or '')[:70]
        price = self._money(p)
        compare = ''
        try:
            if p.compare_list_price and p.compare_list_price > p.list_price:
                compare = ('<span style="color:#9b9b9b;text-decoration:'
                           'line-through;font-size:12px;margin-inline-start:6px">'
                           '%.3f</span>' % p.compare_list_price)
        except Exception:
            pass
        return (
            '<td width="%s%%" valign="top" style="padding:8px">'
            '<table width="100%%" cellpadding="0" cellspacing="0" '
            'style="border:1px solid #eee;border-radius:12px;overflow:hidden;'
            'background:#fff">'
            '<tr><td><a href="%s" style="text-decoration:none">'
            '<img src="%s" width="100%%" style="display:block;width:100%%;'
            'height:auto;background:#faf6eb" alt=""/></a></td></tr>'
            '<tr><td style="padding:10px 12px 12px">'
            '<a href="%s" style="text-decoration:none;color:#1f1206;'
            'font-weight:700;font-size:13px;line-height:1.3;display:block;'
            'min-height:34px">%s</a>'
            '<div style="margin-top:6px;color:%s;font-weight:800;font-size:15px">'
            '%s%s</div>'
            '<a href="%s" style="display:block;margin-top:10px;background:%s;'
            'color:%s;text-align:center;padding:9px 0;border-radius:8px;'
            'font-weight:800;font-size:12px;text-decoration:none">%s</a>'
            '</td></tr></table></td>'
        ) % (width_pct, url, img, url, name, DARK, price, compare, url,
             YELLOW, DARK, self.cta_label or 'Shop now')

    def _build_html(self, products):
        base = self._base_url()
        cols = int(self.columns or '2')
        wpct = 100 // cols
        rows = []
        for i in range(0, len(products), cols):
            cells = ''.join(self._card(p, base, wpct)
                            for p in products[i:i + cols])
            rows.append('<tr>%s</tr>' % cells)
        grid = ('<table width="100%%" cellpadding="0" cellspacing="0">%s</table>'
                % ''.join(rows))
        return (
            '<div style="background:#faf6eb;padding:0;margin:0">'
            '<table width="100%%" cellpadding="0" cellspacing="0" '
            'style="max-width:600px;margin:0 auto;font-family:Arial,Helvetica,'
            'sans-serif">'
            '<tr><td style="background:%s;padding:22px 20px;border-radius:0 0 '
            '16px 16px">'
            '<div style="color:%s;font-size:22px;font-weight:900">%s</div>'
            '<div style="color:#fff;opacity:.85;font-size:13px;margin-top:4px">'
            '%s</div></td></tr>'
            '<tr><td style="padding:10px 6px">%s</td></tr>'
            '<tr><td style="text-align:center;padding:18px 20px 28px;color:'
            '#9b9b9b;font-size:11px">Uellow · '
            '<a href="%s" style="color:%s">www.uellow.com</a><br/>'
            '<a href="/unsubscribe_from_list" style="color:#bbb">Unsubscribe</a>'
            '</td></tr>'
            '</table></div>'
        ) % (DARK, YELLOW, self.headline or '', self.subheadline or '',
             grid, base, DARK)

    # ── generate the draft mailing ────────────────────────────────────────
    def action_generate(self):
        self.ensure_one()
        products = self._pick_products()
        if not products:
            raise UserError(_('No products matched this strategy — try another.'))
        html = self._build_html(products)
        vals = {
            'subject': self.subject,
            'body_arch': html,
            'body_html': html,
            'mailing_type': 'mail',
        }
        Mailing = self.env['mailing.mailing'].sudo()
        if self.mailing_list_id:
            vals['mailing_model_id'] = self.env.ref(
                'mass_mailing.model_mailing_list').id
            vals['contact_list_ids'] = [(6, 0, [self.mailing_list_id.id])]
        else:
            vals['mailing_model_id'] = self.env.ref('base.model_res_partner').id
            vals['mailing_domain'] = "[('customer_rank','>',0),('email','!=',False)]"
        mailing = Mailing.create(vals)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Brain campaign — review & send'),
            'res_model': 'mailing.mailing',
            'res_id': mailing.id,
            'view_mode': 'form',
            'target': 'current',
        }
