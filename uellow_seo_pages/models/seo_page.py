from odoo import models, fields, api


class SEOLandingPage(models.Model):
    _name = 'uellow.seo.page'
    _description = 'SEO Landing Page'
    _rec_name = 'title_en'

    title_en = fields.Char('Title (EN)', required=True)
    title_ar = fields.Char('Title (AR)')
    slug = fields.Char('URL Slug', required=True, index=True)
    meta_desc_en = fields.Text('Meta Description (EN)')
    meta_desc_ar = fields.Text('Meta Description (AR)')
    h1_en = fields.Char('H1 (EN)')
    h1_ar = fields.Char('H1 (AR)')
    intro_en = fields.Text('Intro Paragraph (EN)')
    intro_ar = fields.Text('Intro Paragraph (AR)')

    # What to show
    product_source = fields.Selection([
        ('category', 'Category'),
        ('tag',      'Product Tag'),
        ('manual',   'Manual Selection'),
        ('top_sellers', 'Top Sellers'),
    ], default='category')
    category_id = fields.Many2one('product.category')
    manual_product_ids = fields.Many2many('product.template', string='Products')
    max_products = fields.Integer('Max Products', default=12)

    active = fields.Boolean(default=True)
    visit_count = fields.Integer('Visit Count', default=0, readonly=True)
    last_visited = fields.Datetime('Last Visited', readonly=True)
    created_by_ai = fields.Boolean('AI Generated', default=False)

    _sql_constraints = [
        ('unique_slug', 'UNIQUE(slug)', 'Page slug must be unique.'),
    ]

    def get_products(self, limit=12):
        domain = [('website_published', '=', True)]
        if self.product_source == 'category' and self.category_id:
            domain.append(('categ_id', 'child_of', self.category_id.id))
        elif self.product_source == 'manual':
            return self.manual_product_ids[:limit]
        elif self.product_source == 'top_sellers':
            pass  # Use default domain
        return self.env['product.template'].search(domain, limit=limit)
