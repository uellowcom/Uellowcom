from odoo import http
from odoo.http import request
import logging
from odoo.addons.website_sale.controllers.main import WebsiteSale

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
        
        # Get location data from form
        latitude = post.get('latitude')
        longitude = post.get('longitude')
        address = post.get('address')
        
        if existing_partner:
            partner = existing_partner
            # Update partner's location if provided
            if latitude and longitude:
                partner.write({
                    'contact_address': address,
                    'partner_latitude': latitude,
                    'partner_longitude': longitude,
                })
        else:
            partner_values = {
                'name': post.get('name'),
                'phone': post.get('phone'),
                'customer_rank': 1,
            }
            
            # Add location data if provided
            if latitude and longitude:
                partner_values.update({
                    'contact_address': address,
                    'partner_latitude': latitude,
                    'partner_longitude': longitude,
                })
                
            partner = partner_obj.create(partner_values)
        
        # Update the order with partner information
        order_values = {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'is_quick_checkout': True,
        }
        
        # Add location data to order note if provided
        if address:
            order_values['note'] = f"Delivery Address: {address}\nCoordinates: {latitude}, {longitude}"
            
        order.write(order_values)
        
        # Confirm the order
        order.action_confirm()
        
        # Clear the cart
        request.website.sale_reset()
        
        # Render success page
        return request.render('quick_checkout.quick_checkout_success', {
            'phone': post.get('phone'),
            'address': address,
        })
        
    @http.route(['/shop/product/quick_checkout/<int:product_id>'], type='http', auth="public", website=True)
    def product_quick_checkout(self, product_id, **post):
        """Add product to cart and redirect to quick checkout"""
        # Clear current cart
        request.website.sale_reset()
        
        # Add product to cart with better error handling
        product = request.env['product.product'].sudo().browse(product_id)
        if not product.exists():
            return request.redirect('/shop?error=product_not_found')
            
        if not product.active:
            return request.redirect('/shop?error=product_not_active')
            
        try:
            order = request.website.sale_get_order(force_create=1)
            order._cart_update(
                product_id=product_id,
                add_qty=1
            )
            # Redirect to quick checkout form
            return request.redirect('/shop/quick_checkout')
        except Exception as e:
            # Log the error for debugging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Quick checkout error: {str(e)}")
            return request.redirect('/shop?error=cart_update_failed')
