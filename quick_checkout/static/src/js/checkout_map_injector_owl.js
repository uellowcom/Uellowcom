/** @odoo-module **/

import { registry } from '@web/core/registry';
import { CheckoutMapComponent } from './checkout_map_component';
import { mount } from '@odoo/owl';

/**
 * Checkout Map Injector
 * Injects the Owl map component into the checkout address form
 */
odoo.define('quick_checkout.checkout_map_injector_owl', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    
    publicWidget.registry.CheckoutMapInjectorOwl = publicWidget.Widget.extend({
        selector: 'form[action*="/shop/"], div.checkout_autoformat',
        
        /**
         * Initialize the widget
         */
        start: function () {
            const def = this._super.apply(this, arguments);
            
            // Check if we're on a checkout page that has an address form
            const isCheckoutPage = window.location.pathname.includes('/shop/checkout') || 
                                  window.location.pathname.includes('/shop/address') ||
                                  window.location.pathname.includes('/shop/confirm_order');
            
            // Only inject the map component if we're on a checkout page and there's no map already
            if (isCheckoutPage && !document.getElementById('checkout-map-container')) {
                console.log('Injecting Owl map component into checkout form');
                this._injectMapComponent();
            }
            
            return def;
        },
        
        /**
         * Inject the map component into the checkout form
         */
        _injectMapComponent: function () {
            // Try different selectors to find a good injection point
            let injectionPoint = null;
            
            // Option 1: Try to find the submit button container
            const submitButtonContainer = this.$el.find('.clearfix:last, .o_website_form_send, button[type="submit"]:last').closest('div');
            if (submitButtonContainer.length) {
                injectionPoint = submitButtonContainer;
                console.log('Found submit button container for map injection');
            }
            
            // Option 2: Try to find the last form-group
            if (!injectionPoint || !injectionPoint.length) {
                const lastFormGroup = this.$el.find('.form-group:last, .mb-3:last');
                if (lastFormGroup.length) {
                    injectionPoint = lastFormGroup;
                    console.log('Found last form group for map injection');
                }
            }
            
            // Option 3: Just use the form itself if nothing else works
            if (!injectionPoint || !injectionPoint.length) {
                injectionPoint = this.$el;
                console.log('Using form itself for map injection');
            }
            
            if (injectionPoint && injectionPoint.length) {
                console.log('Injection point found, adding map component');
                
                // Create map container div
                const mapContainerDiv = document.createElement('div');
                mapContainerDiv.id = 'checkout-map-container';
                mapContainerDiv.className = 'form-group mb-3 mt-4';
                
                // Create label
                const label = document.createElement('label');
                label.textContent = 'Pinpoint Your Location on Map';
                mapContainerDiv.appendChild(label);
                
                // Create component container
                const componentContainer = document.createElement('div');
                componentContainer.id = 'checkout-map-component';
                mapContainerDiv.appendChild(componentContainer);
                
                // Add instructions
                const instructions = document.createElement('small');
                instructions.className = 'text-muted';
                instructions.innerHTML = '<i class="fa fa-info-circle me-1"></i> Drag the marker to pinpoint your exact location or use the button to detect your current location.';
                mapContainerDiv.appendChild(instructions);
                
                // Insert the container into the DOM
                if (injectionPoint.is(this.$el)) {
                    // If it's the form itself, append to it
                    injectionPoint.append(mapContainerDiv);
                } else {
                    // Otherwise insert before the injection point
                    injectionPoint.before(mapContainerDiv);
                }
                
                // Mount the Owl component
                this._mountOwlComponent(componentContainer);
            } else {
                console.error('Could not find a suitable injection point for the map component');
            }
        },
        
        /**
         * Mount the Owl component
         */
        _mountOwlComponent: function (container) {
            // Create the component and mount it
            const component = new CheckoutMapComponent();
            
            // Mount the component
            mount(component, container);
        }
    });
    
    return publicWidget.registry.CheckoutMapInjectorOwl;
});
