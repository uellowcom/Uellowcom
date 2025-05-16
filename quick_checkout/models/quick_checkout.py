from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class QuickCheckout(models.Model):
    _name = 'quick.checkout'
    _description = 'Quick Checkout'
    
    name = fields.Char(string='Name', required=True)
    phone = fields.Char(string='Phone', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale Order')
    partner_id = fields.Many2one('res.partner', string='Customer')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    
    @api.model
    def create_quick_checkout(self, name, phone, sale_order_id):
        """Create a quick checkout record and associated contact and sale order"""
        # Create or find the partner
        partner = self.env['res.partner'].search([('phone', '=', phone)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': name,
                'phone': phone,
                'is_quick_checkout': True,
            })
        
        # Get the sale order
        sale_order = self.env['sale.order'].browse(int(sale_order_id))
        if not sale_order.exists():
            raise ValidationError(_('Sale order not found'))
        
        # Update the sale order with the partner
        sale_order.write({
            'partner_id': partner.id,
            'is_quick_checkout': True,
        })
        
        # Confirm the sale order
        sale_order.action_confirm()
        
        # Create quick checkout record
        quick_checkout = self.create({
            'name': name,
            'phone': phone,
            'sale_order_id': sale_order.id,
            'partner_id': partner.id,
        })
        
        return {
            'success': True,
            'quick_checkout_id': quick_checkout.id,
            'sale_order_id': sale_order.id,
        }
