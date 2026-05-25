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
            products = rule._fetch_products(partner_id, limit)
            if products:
                return {
                    'products': products,
                    'title_en': rule.section_title_en,
                    'title_ar': rule.section_title_ar,
                    'show_type': rule.show_type,
                }
        return {}

    def _fetch_products(self, partner_id, limit):
        domain = [('website_published', '=', True)]
        if self.category_id:
            domain.append(('categ_id', 'child_of', self.category_id.id))
        if self.show_type == 'flash_sales':
            domain.append(('is_flash_sale', '=', True))
        order = 'create_date desc' if self.show_type == 'new_arrivals' else 'id desc'
        if self.show_type == 'recently_viewed' and partner_id:
            orders = self.env['sale.order'].search([
                ('partner_id', '=', partner_id),
                ('state', 'in', ('sale', 'done')),
            ], order='date_order desc', limit=3)
            ids = orders.mapped('order_line.product_id.product_tmpl_id').ids[:limit]
            if ids:
                return self.env['product.template'].browse(ids).read(['id', 'name', 'list_price', 'website_url'])
        return self.env['product.template'].search(domain, order=order, limit=limit).read(
            ['id', 'name', 'list_price', 'website_url'])
