/** @odoo-module **/

import { Component, mount, App, onMounted, useRef } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { CheckoutMapComponent } from './checkout_map_component';

/**
 * Checkout Map Injector
 * Injects the Owl map component into the checkout address form
 */

// Function to inject the map component when the DOM is ready
function injectMapComponent() {
    // Wait for the DOM to be fully loaded
    document.addEventListener('DOMContentLoaded', () => {
        // Check if we're on a checkout page that has an address form
        const isCheckoutPage = window.location.pathname.includes('/shop/checkout') || 
                              window.location.pathname.includes('/shop/address') ||
                              window.location.pathname.includes('/shop/confirm_order');
        
        // Only inject the map component if we're on a checkout page and there's no map already
        if (isCheckoutPage && !document.getElementById('checkout-map-container')) {
            console.log('Injecting Owl map component into checkout form');
            _injectMapComponent();
        }
    });
}
    
/**
 * Inject the map component into the checkout form
 * @private
 */
function _injectMapComponent() {
    // Check if we're on a page with the shop_checkout div
    const shopCheckout = document.getElementById('shop_checkout');
    let injectionPoint = null;
    
    if (shopCheckout) {
        // We're on the main checkout page with the new structure
        console.log('Found shop_checkout container for map injection');
        injectionPoint = shopCheckout;
    } else {
        // Try different selectors to find a good injection point
        
        // Option 1: Try to find the submit button container
        const submitButtonContainer = document.querySelector('.clearfix:last-child, .o_website_form_send, button[type="submit"]:last-child');
        if (submitButtonContainer) {
            injectionPoint = submitButtonContainer.closest('div');
            console.log('Found submit button container for map injection');
        }
        
        // Option 2: Try to find the last form-group
        if (!injectionPoint) {
            const lastFormGroup = document.querySelector('.form-group:last-child, .mb-3:last-child');
            if (lastFormGroup) {
                injectionPoint = lastFormGroup;
                console.log('Found last form group for map injection');
            }
        }
        
        // Option 3: Just use the form itself if nothing else works
        if (!injectionPoint) {
            injectionPoint = document.querySelector('form[action*="/shop/"]');
            console.log('Using form itself for map injection');
        }
    }
    
    if (injectionPoint) {
        console.log('Injection point found, adding map component');
        
        // Create a card container for the map
        const cardContainer = document.createElement('div');
        cardContainer.id = 'checkout-map-container';
        cardContainer.className = 'row mt-3 mb-3';
        cardContainer.innerHTML = `
            <div class="col-12">
                <div class="card">
                    <div class="card-header bg-light">
                        <h5 class="mb-0">Pinpoint Your Location on Map</h5>
                    </div>
                    <div class="card-body">
                        <!-- Component will be mounted here -->
                        <div id="checkout-map-component"></div>
                        
                        <!-- Hidden fields for location data -->
                        <input type="hidden" id="latitude" name="latitude" />
                        <input type="hidden" id="longitude" name="longitude" />
                        <input type="hidden" id="map_address" name="map_address" />
                    </div>
                </div>
            </div>
        `;
        
        // Insert the container into the DOM
        if (shopCheckout) {
            // If we're on the main checkout page, append to the shop_checkout div
            injectionPoint.appendChild(cardContainer);
        } else {
            // Regular DOM element
            injectionPoint.parentNode.insertBefore(cardContainer, injectionPoint.nextSibling);
        }
        
        // Mount the Owl component
        const componentContainer = document.getElementById('checkout-map-component');
        if (componentContainer) {
            _mountOwlComponent(componentContainer);
        }
    } else {
        console.error('Could not find a suitable injection point for the map component');
    }
}
    
/**
 * Mount the Owl component using Owl's App class for better lifecycle management
 * @private
 * @param {HTMLElement} container - The container element to mount the component in
 */
function _mountOwlComponent(container) {
    // Create an Owl App to properly manage the component lifecycle
    const app = new App(CheckoutMapComponent, {
        env: {
            services: {}
        },
        dev: odoo.debug,
        templates: window.owl.templates,
        translateFn: (str) => str,
    });
    
    // Mount the app on the container
    app.mount(container);
    
    // Store the app instance for cleanup if needed (in case we need to unmount later)
    window.checkoutMapApp = app;
}

// Initialize the map injection when the script loads
injectMapComponent();

export { injectMapComponent };
