"""Multi-market pricing (idea #13).

17 websites resolve to ~12 pricelists (Kuwait, Saudia, Qatar, UAE, Oman, US,
Egypt…). This lets you set a per-market price MULTIPLIER and get a suggested
price per market for a product — reviewed in a wizard and applied to that
market's pricelist ONLY on a deliberate click. Nothing touches live prices
automatically; suggestion-only, gated by the feat_multimarket switch.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MarketFactor(models.Model):
    """Per-pricelist price multiplier — the detailed per-market control."""
    _name = 'uellow.sc.market.factor'
    _description = 'Market Price Factor'
    _order = 'pricelist_id'

    pricelist_id = fields.Many2one(
        'product.pricelist', required=True, ondelete='cascade', string='Market (Pricelist)')
    factor = fields.Float('Price Multiplier', default=1.0,
                          help='Suggested price = base price × this factor.')
    note = fields.Char('Note')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('uniq_pricelist', 'unique(pricelist_id)',
         'A factor already exists for this market.'),
    ]

    @api.constrains('factor')
    def _check_factor(self):
        for r in self:
            if r.factor <= 0:
                raise ValidationError(_('Price multiplier must be greater than zero.'))

    @api.model
    def action_seed_factors(self):
        """Create a 1.0 factor row for every pricelist that doesn't have one."""
        existing = set(self.search([]).mapped('pricelist_id').ids)
        new = self.env['product.pricelist'].search([('id', 'not in', list(existing))])
        self.create([{'pricelist_id': pl.id, 'factor': 1.0} for pl in new])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Market Factors'),
            'res_model': 'uellow.sc.market.factor',
            'view_mode': 'list',
        }


class MarketPricer(models.TransientModel):
    """Wizard: pick a product → preview per-market suggestions → apply."""
    _name = 'uellow.sc.market.pricer'
    _description = 'Multi-Market Pricer'

    product_id = fields.Many2one('product.template', string='Product', required=True)
    base_price = fields.Float('Base Price (KD)', readonly=True)
    line_ids = fields.One2many('uellow.sc.market.pricer.line', 'pricer_id', string='Markets')

    def action_generate(self):
        """Build a suggestion line per active market factor."""
        self.ensure_one()
        if not self.env['uellow.connector.settings'].get_settings().get('feat_multimarket'):
            raise UserError(_('Multi-Market Pricing is disabled in Settings.'))
        base = self.product_id.list_price or 0.0
        factors = self.env['uellow.sc.market.factor'].search([('active', '=', True)])
        if not factors:
            raise UserError(_(
                'No market factors yet. Open Market Factors and click "Seed Factors".'))
        self.line_ids.unlink()
        self.base_price = base
        vals = []
        for f in factors:
            current = self._current_pricelist_price(f.pricelist_id, self.product_id)
            vals.append((0, 0, {
                'pricelist_id': f.pricelist_id.id,
                'factor': f.factor,
                'suggested_price': round(base * f.factor, 3),
                'current_price': current,
                'apply': True,
            }))
        self.line_ids = vals
        return self._reopen()

    def action_apply(self):
        """Write the selected suggestions to each market's pricelist."""
        self.ensure_one()
        if not self.env['uellow.connector.settings'].get_settings().get('feat_multimarket'):
            raise UserError(_('Multi-Market Pricing is disabled in Settings.'))
        applied = 0
        for line in self.line_ids.filtered('apply'):
            if line.suggested_price <= 0:
                continue
            self._set_pricelist_price(line.pricelist_id, self.product_id, line.suggested_price)
            applied += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Applied'),
                'message': _('Updated %d market price(s) for %s.') % (
                    applied, self.product_id.display_name),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    @staticmethod
    def _current_pricelist_price(pricelist, product):
        item = pricelist.item_ids.filtered(
            lambda i: i.applied_on == '1_product'
            and i.product_tmpl_id.id == product.id
            and i.compute_price == 'fixed')
        return item[:1].fixed_price if item else 0.0

    def _set_pricelist_price(self, pricelist, product, price):
        """Create or update a fixed-price rule on this pricelist (reversible)."""
        Item = self.env['product.pricelist.item']
        item = pricelist.item_ids.filtered(
            lambda i: i.applied_on == '1_product'
            and i.product_tmpl_id.id == product.id
            and i.compute_price == 'fixed')
        if item:
            item[:1].fixed_price = price
        else:
            Item.create({
                'pricelist_id': pricelist.id,
                'applied_on': '1_product',
                'product_tmpl_id': product.id,
                'compute_price': 'fixed',
                'fixed_price': price,
            })

    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'uellow.sc.market.pricer',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class MarketPricerLine(models.TransientModel):
    _name = 'uellow.sc.market.pricer.line'
    _description = 'Multi-Market Pricer Line'

    pricer_id = fields.Many2one('uellow.sc.market.pricer', ondelete='cascade')
    pricelist_id = fields.Many2one('product.pricelist', string='Market', readonly=True)
    factor = fields.Float('Multiplier', readonly=True)
    current_price = fields.Float('Current (KD)', readonly=True)
    suggested_price = fields.Float('Suggested (KD)')
    apply = fields.Boolean('Apply', default=True)
