from odoo import models, fields, api, _


class VendorStore(models.Model):
    """
    Store page settings — which tabs to show, featured products, layout.
    Each vendor has one store record (auto-created on approval).
    """
    _name = 'uellow.vendor.store'
    _description = 'Vendor Store Page'
    _rec_name = 'vendor_id'

    vendor_id = fields.Many2one(
        'uellow.vendor', required=True, ondelete='cascade', index=True,
    )

    # Visibility
    store_page_enabled = fields.Boolean('Store Page Enabled', default=True)
    show_products_tab = fields.Boolean('Show Products Tab', default=True)
    show_about_tab = fields.Boolean('Show About Tab', default=True)
    show_reviews_tab = fields.Boolean('Show Reviews Tab', default=True)
    show_follow_button = fields.Boolean('Show Follow Button', default=True)
    hidden_temporarily = fields.Boolean('Hidden Temporarily', default=False)

    # Layout
    layout = fields.Selection([
        ('grid',     'Grid'),
        ('list',     'List'),
        ('featured', 'Featured Product'),
    ], default='grid', string='Product Layout')

    # Featured products (up to 6)
    featured_product_ids = fields.Many2many(
        'product.template', string='Featured Products',
        relation='uellow_store_featured_products',
        domain="[('vendor_id', '=', vendor_id)]",
    )

    # SEO
    meta_title = fields.Char('Meta Title')
    meta_description = fields.Text('Meta Description')

    # Stats
    visit_count = fields.Integer('Total Visits', default=0)
    last_visit = fields.Datetime('Last Visit')

    def action_visit(self):
        """Increment visit counter."""
        self.ensure_one()
        self.visit_count += 1
        self.last_visit = fields.Datetime.now()
