from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ── Vendor ───────────────────────────────────────────────────
    vendor_id = fields.Many2one(
        'uellow.vendor', string='Vendor',
        index=True, ondelete='set null',
    )

    # ── Sponsored listing (paid boost) ───────────────────────────
    is_sponsored = fields.Boolean('Sponsored', default=False, index=True, copy=False,
        help='Boosted via a paid vendor.ad.campaign. Storefront/app may rank or badge it.')
    sponsor_until = fields.Date('Sponsored Until', copy=False)

    # ── Print-report thumbnail ───────────────────────────────────
    # A JPEG thumbnail used ONLY by the Update-Prices PDF, for products whose
    # main image is WebP (wkhtmltopdf cannot render WebP). Populated out-of-band
    # (host-side conversion); the storefront images are never touched.
    uc_report_thumb = fields.Binary('Report Thumbnail (JPEG)', attachment=True, copy=False)

    # ── Approval Workflow ────────────────────────────────────────
    vendor_approval_state = fields.Selection([
        ('pending',  'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='pending', index=True, copy=False)

    vendor_rejection_reason = fields.Text('Rejection Reason', copy=False)

    # ── Edit-approval (vendor edits to a live product) ───────────
    pending_change_id = fields.Many2one('uellow.product.change',
        string='Pending Edit', copy=False)
    under_review = fields.Boolean('Under Review', compute='_compute_under_review')

    @api.depends('pending_change_id', 'pending_change_id.state')
    def _compute_under_review(self):
        for p in self:
            p.under_review = bool(p.pending_change_id and p.pending_change_id.state == 'pending')
    vendor_submitted_by = fields.Many2one('res.users', string='Submitted By',
        ondelete='set null', copy=False)
    vendor_submitted_date = fields.Datetime('Submitted On', copy=False)
    vendor_reviewed_by = fields.Many2one('res.users', string='Reviewed By',
        ondelete='set null', copy=False)
    vendor_reviewed_date = fields.Datetime('Reviewed On', copy=False)

    # ── Flash Sale ───────────────────────────────────────────────
    flash_sale_id = fields.Many2one('uellow.flash.sale', string='Active Flash Sale',
        ondelete='set null')
    flash_sale_price = fields.Float('Flash Sale Price', default=0.0)
    is_flash_sale = fields.Boolean(compute='_compute_is_flash_sale', store=True)

    @api.depends('flash_sale_id')
    def _compute_is_flash_sale(self):
        for p in self:
            p.is_flash_sale = bool(p.flash_sale_id)

    def get_display_price(self):
        self.ensure_one()
        if self.flash_sale_id and self.flash_sale_price > 0:
            return self.flash_sale_price
        return self.list_price

    # ── Approval Actions ─────────────────────────────────────────
    def action_vendor_approve(self):
        for product in self:
            product.write({
                'vendor_approval_state': 'approved',
                'website_published': True,
                'vendor_reviewed_by': self.env.user.id,
                'vendor_reviewed_date': fields.Datetime.now(),
            })
            if product.vendor_id and product.vendor_id.user_id:
                product.message_post(
                    body=_('✅ Product <b>%s</b> approved and is now live.') % product.name,
                    partner_ids=[product.vendor_id.user_id.partner_id.id],
                    message_type='notification',
                )

    def action_vendor_approve_all(self):
        """Approve every pending vendor product at once (ignores selection).
        Wired to the 'Approve All' header button on the Product Approvals view."""
        pending = self.search([
            ('vendor_id', '!=', False),
            ('vendor_approval_state', '=', 'pending'),
        ])
        count = len(pending)
        if pending:
            pending.action_vendor_approve()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Approve All'),
                'message': (_('%d vendor product(s) approved and published.') % count)
                           if count else _('No pending products to approve.'),
                'type': 'success' if count else 'warning',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'} if count
                        else {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_vendor_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'uellow.product.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_ids': self.ids},
        }

    def action_vendor_set_pending(self):
        for product in self:
            product.write({
                'vendor_approval_state': 'pending',
                'website_published': False,
                'vendor_rejection_reason': False,
            })
