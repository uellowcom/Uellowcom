import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class UellowReturnRequest(models.Model):
    """Vendor request to withdraw / return goods stored at Uellow (FBU /
    Consignment). Admin approves → physical handover (self pickup or Uellow
    courier) → both sides sign → stock is settled (on-hand decremented)."""
    _name = 'uellow.return.request'
    _description = 'Vendor Stock Return / Withdrawal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char('Reference', default='New', copy=False, readonly=True)
    vendor_id = fields.Many2one('uellow.vendor', string='Vendor', required=True,
        ondelete='cascade', index=True, tracking=True)
    line_ids = fields.One2many('uellow.return.request.line', 'request_id', string='Items')
    pickup_mode = fields.Selection([
        ('self',   'Vendor picks up'),
        ('uellow', 'Uellow courier delivers to vendor'),
    ], default='self', string='Handover', tracking=True)
    reason = fields.Text('Reason')
    state = fields.Selection([
        ('submitted', 'Submitted'),
        ('approved',  'Approved'),
        ('delivered', 'Delivered & Signed'),
        ('settled',   'Stock Settled'),
        ('rejected',  'Rejected'),
    ], default='submitted', index=True, tracking=True)
    submitted_date = fields.Datetime(default=fields.Datetime.now)
    approved_date = fields.Datetime(copy=False)
    settled_date = fields.Datetime(copy=False)
    reject_reason = fields.Text(copy=False)
    total_qty = fields.Integer(compute='_compute_totals', store=True)
    total_cost = fields.Float(compute='_compute_totals', store=True)

    @api.depends('line_ids.qty', 'line_ids.cost')
    def _compute_totals(self):
        for r in self:
            r.total_qty = sum(r.line_ids.mapped('qty'))
            r.total_cost = sum(l.qty * l.cost for l in r.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('uellow.return.request') \
                    or ('RET-%05d' % (self.search_count([]) + 1))
        return super().create(vals_list)

    def action_approve(self):
        self.write({'state': 'approved', 'approved_date': fields.Datetime.now()})
        self._notify_vendor('approved')

    def action_mark_delivered(self):
        self.write({'state': 'delivered'})

    def action_settle(self):
        """Decrement on-hand for each returned product (goods left Uellow)."""
        for r in self:
            loc = self.env['stock.location'].sudo().search(
                [('usage', '=', 'internal')], limit=1)
            for line in r.line_ids:
                product = line.product_id
                if product and loc and line.qty:
                    try:
                        self.env['stock.quant'].sudo().with_context(inventory_mode=True)\
                            ._update_available_quantity(product, loc, -abs(line.qty))
                    except Exception:
                        _logger.warning('return settle failed for %s', product.id, exc_info=True)
            r.write({'state': 'settled', 'settled_date': fields.Datetime.now()})
            r.message_post(body=_('Stock settled — %s unit(s) removed from Uellow on-hand.') % r.total_qty)
            r._notify_vendor('settled')

    def action_reject(self):
        self.write({'state': 'rejected'})
        self._notify_vendor('rejected')

    def _notify_vendor(self, kind):
        for r in self:
            partner = (r.vendor_id.user_id.partner_id
                       if r.vendor_id and r.vendor_id.user_id else False)
            if not partner:
                continue
            titles = {
                'approved': ('Return approved', 'تم اعتماد طلب الاسترجاع'),
                'settled':  ('Return completed', 'اكتمل استرجاع البضاعة'),
                'rejected': ('Return rejected', 'تم رفض طلب الاسترجاع'),
            }.get(kind, ('Return update', 'تحديث طلب الاسترجاع'))
            try:
                self.env['mobile.customer.notification'].sudo().push_role(
                    'notify_return_request', partner,
                    title_en=titles[0], title_ar=titles[1],
                    body_en='%s — %s' % (r.name, kind),
                    body_ar='%s' % r.name,
                    data={'type': 'return_request', 'id': r.id})
            except Exception:
                _logger.debug('return push failed', exc_info=True)


class UellowReturnRequestLine(models.Model):
    _name = 'uellow.return.request.line'
    _description = 'Vendor Return Line'

    request_id = fields.Many2one('uellow.return.request', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty = fields.Integer('Qty', default=1)
    cost = fields.Float('Unit Cost')
    available = fields.Float('On-hand at Uellow', related='product_id.qty_available', readonly=True)

    @api.onchange('product_id')
    def _onchange_product(self):
        if self.product_id:
            self.cost = self.product_id.standard_price
