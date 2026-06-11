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
        # v2.2.20 — conditional RULES: only badge-safe ones (no personal
        # conditions) whose context matches light the badge — rules with
        # amount/age/customer conditions apply at checkout only, so the
        # card never promises a free shipping the customer might not get.
        try:
            Rule = self.env.get('uellow.freeship.rule')
            if Rule is not None and Rule.sudo().badge_covers(self):
                return True
        except Exception:
            pass
        return False
