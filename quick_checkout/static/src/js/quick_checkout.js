/** @odoo-module **/

import { Component, useState, onMounted, useRef } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';

/**
 * Quick Checkout Form Component
 * Handles the quick checkout form submission
 */
class QuickCheckoutForm extends Component {
    setup() {
        this.state = useState({
            isSubmitting: false
        });
        this.formRef = useRef('checkoutForm');
        this.translateService = useService('translation');
    }
    
    /**
     * Handle form submission
     * @param {Event} ev - Form submission event
     */
    onSubmitForm(ev) {
        // Update state to show loading
        this.state.isSubmitting = true;
        // Form will handle submission naturally
    }
}

QuickCheckoutForm.template = 'quick_checkout.QuickCheckoutFormTemplate';
QuickCheckoutForm.props = {};

/**
 * Product Quick Checkout Button Component
 * Handles the quick checkout button on product pages
 */
class ProductQuickCheckoutButton extends Component {
    setup() {
        this.state = useState({
            isLoading: false
        });
        this.translateService = useService('translation');
    }
    
    /**
     * Handle quick checkout button click
     * @param {Event} ev - Click event
     */
    onClickQuickCheckout(ev) {
        this.state.isLoading = true;
        // Let the link navigate naturally
    }
}

ProductQuickCheckoutButton.template = 'quick_checkout.ProductQuickCheckoutButtonTemplate';
ProductQuickCheckoutButton.props = {};

/**
 * Theme Prime Compatibility Component
 * Ensures DOM elements are fully loaded before accessing properties
 */
class ThemePrimeQuickCheckoutFix extends Component {
    setup() {
        onMounted(() => this.fixThemePrimeLayout());
    }
    
    /**
     * Fix theme_prime layout issues
     */
    fixThemePrimeLayout() {
        if (window.themePrimeComponents) {
            // Add a small delay to ensure DOM is fully rendered
            setTimeout(() => {
                // Trigger window resize to force recalculation of layouts
                window.dispatchEvent(new Event('resize'));
            }, 100);
        }
    }
}

ThemePrimeQuickCheckoutFix.template = 'quick_checkout.ThemePrimeQuickCheckoutFixTemplate';
ThemePrimeQuickCheckoutFix.props = {};

// Register components in the frontend registry
const frontendComponents = registry.category('frontend_components');
frontendComponents.add('quick_checkout_form', QuickCheckoutForm);
frontendComponents.add('product_quick_checkout_button', ProductQuickCheckoutButton);
frontendComponents.add('theme_prime_quick_checkout_fix', ThemePrimeQuickCheckoutFix);

// Export components for potential reuse
export {
    QuickCheckoutForm,
    ProductQuickCheckoutButton,
    ThemePrimeQuickCheckoutFix
};

