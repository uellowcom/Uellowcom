/** @odoo-module **/

import { Component, onMounted } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { CheckoutMapComponent } from './checkout_map_component';

/**
 * Checkout Map Injector Component
 * Injects the map component into the checkout page
 */
class CheckoutMapInjector extends Component {
    setup() {
        onMounted(() => this.injectMapComponent());
    }
    
    /**
     * Inject the map component into the checkout page
     */
    injectMapComponent() {
        // Check if we're on the checkout page
        if (window.location.pathname.includes('/shop/checkout') || 
            window.location.pathname.includes('/shop/address')) {
            
            console.log('Injecting map component into checkout page...');
            
            // Find the target container or create one if it doesn't exist
            let container = document.getElementById('checkout-map-component');
            
            if (!container) {
                // Create a container for the map component
                container = document.createElement('div');
                container.id = 'checkout-map-component';
                
                // Find the appropriate place to inject the container
                const checkoutForm = document.querySelector('form[action="/shop/checkout"]');
                if (checkoutForm) {
                    // Insert before the first button
                    const button = checkoutForm.querySelector('button[type="submit"]');
                    if (button) {
                        const parentElement = button.parentElement;
                        parentElement.parentElement.insertBefore(container, parentElement);
                    } else {
                        // Fallback: append to the form
                        checkoutForm.appendChild(container);
                    }
                }
            }
            
            // Mount the component if the container exists and isn't already initialized
            if (container && !container.hasAttribute('data-map-initialized')) {
                container.setAttribute('data-map-initialized', 'true');
                
                // Create and mount the component
                const app = owl.App.createApp(CheckoutMapComponent, {});
                app.mount(container);
                
                console.log('Map component mounted successfully');
            }
        }
    }
}

CheckoutMapInjector.template = 'checkout_map.CheckoutMapInjectorTemplate';
CheckoutMapInjector.props = {};

// Register component in the frontend registry
const frontendComponents = registry.category('frontend_components');
frontendComponents.add('checkout_map_injector', CheckoutMapInjector);

export { CheckoutMapInjector };
