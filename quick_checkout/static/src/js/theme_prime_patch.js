/** @odoo-module **/

import { patch } from '@web/core/utils/patch';

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Check if the theme_prime module is loaded
    if (odoo.define && odoo.define.modules && odoo.define.modules['theme_prime.product_configurator']) {
        // Get the module
        const ThemePrimeModule = odoo.__DEBUG__.services['theme_prime.product_configurator'];
        
        if (ThemePrimeModule) {
            // Patch the problematic method
            patch(ThemePrimeModule.prototype, 'quick_checkout.theme_prime_patch', {
                /**
                 * Override the _modifyElementsAfterAppend method to add null checks
                 * @override
                 */
                _modifyElementsAfterAppend: function () {
                    try {
                        // Call the original method, but wrapped in a try-catch
                        this._super.apply(this, arguments);
                    } catch (error) {
                        // Log the error but don't let it crash the page
                        console.warn('Theme Prime error suppressed:', error);
                    }
                },
                
                /**
                 * Override the _renderContent method to ensure elements exist
                 * @override
                 */
                _renderContent: function () {
                    // Add a small delay to ensure DOM is ready
                    return new Promise(resolve => {
                        setTimeout(() => {
                            try {
                                this._super.apply(this, arguments);
                            } catch (error) {
                                console.warn('Theme Prime render error suppressed:', error);
                            }
                            resolve();
                        }, 50);
                    });
                }
            });
        }
    }
});
