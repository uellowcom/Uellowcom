from odoo import models, fields, api


class PersonalizationRule(models.Model):
    _name = 'uellow.personalization.rule'
    _description = 'Homepage Personalization Rule'
    _rec_name = 'name'
    _order = 'priority desc'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    priority = fields.Integer(default=10)

    segment = fields.Selection([
        ('all',       'All Visitors'),
        ('new',       'New Visitors'),
        ('returning', 'Returning Customers'),
        ('vip',       'VIP / High LTV'),
        ('at_risk',   'At Risk Customers'),
        ('country',   'Specific Country'),
    ], default='all', required=True)

    country_ids = fields.Many2many('res.country', string='Target Countries')

    show_type = fields.Selection([
        ('recently_viewed', 'Recently Viewed'),
        ('recommended',     'AI Recommended'),
        ('top_sellers',     'Top Sellers'),
        ('flash_sales',     'Active Flash Sales'),
        ('new_arrivals',    'New Arrivals'),
        ('category',        'Specific Category'),
        ('vendor',          'Specific Vendor'),
    ], required=True, default='top_sellers')

    category_id = fields.Many2one('product.category')
    max_products = fields.Integer('Max Products', default=8)
    section_title_en = fields.Char('Section Title (EN)', default='Recommended for You')
    section_title_ar = fields.Char('Section Title (AR)', default='مقترح لك')

    @api.model
    def get_for_visitor(self, partner_id=False, country_code=False, limit=8):
        rules = self.search([('active', '=', True)], order='priority desc')
        for rule in rules:
            if rule.segment == 'country' and country_code:
                if country_code not in rule.country_ids.mapped('code'):
                    continue
            elif rule.segment in ('new', 'returning') and partner_id:
                cnt = self.env['sale.order'].search_count([
                    ('partner_id', '=', partner_id),
                    ('state', 'in', ('sale', 'done')),
                ])
                if rule.segment == 'new' and cnt > 1:
                    continue
                if rule.segment == 'returning' and cnt <= 1:
                    continue
            products = rule._fetch_products(partner_id, limit)
            if products:
                return {
                    'products': products,
                    'title_en': rule.section_title_en,
                    'title_ar': rule.section_title_ar,
                    'show_type': rule.show_type,
                }
        return {}

    _RF = ['id', 'name', 'list_price', 'website_url']

    def _fetch_products(self, partner_id, limit):
        Tmpl = self.env['product.template']
        domain = [('website_published', '=', True)]
        if self.category_id:
            domain.append(('categ_id', 'child_of', self.category_id.id))
        if self.show_type == 'flash_sales':
            domain.append(('is_flash_sale', '=', True))

        # recently_viewed: the visitor's own recently-bought products
        if self.show_type == 'recently_viewed' and partner_id:
            orders = self.env['sale.order'].search([
                ('partner_id', '=', partner_id),
                ('state', 'in', ('sale', 'done')),
            ], order='date_order desc', limit=3)
            ids = orders.mapped('order_line.product_id.product_tmpl_id').ids[:limit]
            if ids:
                return Tmpl.browse(ids).read(self._RF)

        # top_sellers: rank by REAL sold quantity (sales_count is a non-stored
        # compute and cannot be a SQL order).
        if self.show_type == 'top_sellers':
            ids = self._top_selling_ids(domain, limit)
            if ids:
                return Tmpl.browse(ids).read(self._RF)

        # recommended: products from the categories the visitor engaged with
        # (their bought products' categories); fall back to top sellers.
        if self.show_type == 'recommended':
            categ_ids = []
            if partner_id:
                bought = self.env['sale.order'].search([
                    ('partner_id', '=', partner_id),
                    ('state', 'in', ('sale', 'done')),
                ], order='date_order desc', limit=5)
                categ_ids = bought.mapped(
                    'order_line.product_id.product_tmpl_id.categ_id').ids
            if categ_ids:
                recs = Tmpl.search(domain + [('categ_id', 'in', categ_ids)],
                                   order='website_sequence, id desc', limit=limit)
                if recs:
                    return recs.read(self._RF)
            ids = self._top_selling_ids(domain, limit)
            if ids:
                return Tmpl.browse(ids).read(self._RF)

        order = 'create_date desc' if self.show_type == 'new_arrivals' \
            else 'website_sequence, id desc'
        return Tmpl.search(domain, order=order, limit=limit).read(self._RF)

    def _top_selling_ids(self, domain, limit):
        """Template ids ranked by real sold qty (sale.report), filtered to
        `domain`, with unsold catalogue as filler."""
        Tmpl = self.env['product.template']
        base_ids = Tmpl.search(domain, limit=1000).ids
        if not base_ids:
            return []
        groups = self.env['sale.report'].read_group(
            [('product_tmpl_id', 'in', base_ids), ('state', 'in', ('sale', 'done'))],
            ['product_tmpl_id', 'product_uom_qty:sum'], ['product_tmpl_id'])
        ranked = sorted(
            [(g['product_tmpl_id'][0], g.get('product_uom_qty') or 0)
             for g in groups if g.get('product_tmpl_id')],
            key=lambda x: x[1], reverse=True)
        ids = [i for i, _ in ranked]
        seen = set(ids)
        ids += [i for i in base_ids if i not in seen]
        return ids[:limit]
