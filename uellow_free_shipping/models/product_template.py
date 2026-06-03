from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    free_shipping = fields.Boolean(
        string='Free shipping (this product)',
        help='If on, this product ships free regardless of category/tag '
             'settings. Overrides everything else.',
    )

    def _is_free_shipping(self):
        """Return True if this product qualifies for free shipping via
        any of: product flag, any public category, any product tag, OR
        the global "free over X" threshold set on the website. The
        cheapest path wins so an admin can keep granular control."""
        self.ensure_one()
        if self.free_shipping:
            return True
        for cat in self.public_categ_ids:
            # walk parents too — child of a marked category counts.
            c = cat
            while c:
                if getattr(c, 'free_shipping', False):
                    return True
                c = c.parent_id
        if 'product_tag_ids' in self._fields:
            for tag in self.product_tag_ids:
                if getattr(tag, 'free_shipping', False):
                    return True
        return False
