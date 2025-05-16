from odoo import http
from odoo.http import request
import logging


class QuickCheckout(http.Controller):

    @http.route(['/shop/quick_checkout'], type='http', auth="public", website=True)
    def quick_checkout(self, **post):
        """Render the quick checkout form"""
        return request.render('quick_checkout.quick_checkout_form')

    @http.route(['/shop/quick_checkout/submit'], type='http', auth="public", website=True)
    def quick_checkout_submit(self, **post):
        """Process the quick checkout form submission"""
        # Get current order
        order = request.website.sale_get_order()
        
        if not order or not order.order_line:
            return request.redirect('/shop')
        
        # Create or find a partner based on phone number
        partner_obj = request.env['res.partner'].sudo()
        existing_partner = partner_obj.search([('phone', '=', post.get('phone'))], limit=1)
        
        if existing_partner:
            partner = existing_partner
        else:
            partner_values = {
                'name': post.get('name'),
                'phone': post.get('phone'),
                'customer_rank': 1,
            }
            partner = partner_obj.create(partner_values)
        
        # Update the order with partner information
        order.write({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'is_quick_checkout': True,
        })
        
        # Confirm the order
        order.action_confirm()
        
        # Clear the cart
        request.website.sale_reset()
        
        # Render success page
        return request.render('quick_checkout.quick_checkout_success', {
            'phone': post.get('phone'),
        })
        
    @http.route(['/shop/product/quick_checkout/<int:product_id>'], type='http', auth="public", website=True)
    def product_quick_checkout(self, product_id, **post):
        """Add product to cart and redirect to quick checkout"""
        # Clear current cart
        request.website.sale_reset()
        
        # Verify product exists before adding to cart
        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            # Product doesn't exist, redirect to shop with warning
            return request.redirect('/shop?warning=Product not found')
        
        try:
            # Add product to cart with error handling
            order = request.website.sale_get_order(force_create=1)
            order._cart_update(
                product_id=product_id,
                add_qty=1
            )
            # Redirect to quick checkout form
            return request.redirect('/shop/quick_checkout')
        except Exception as e:
            # Log the error and redirect with message
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error in quick checkout: {str(e)}")
            return request.redirect('/shop?error=Could not add product to cart')
