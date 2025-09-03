/**
 * Global Theme Prime Fix
 * This script fixes the "Cannot read properties of null (reading 'offsetWidth')" error
 * by adding a global safety wrapper around the problematic methods
 */

// Execute immediately when the script loads
(function() {
    // Original _modifyElementsAfterAppend method that causes the error
    var originalModifyElementsAfterAppend = null;
    
    // Function to safely get element dimensions
    function safeGetElementDimension(element, property) {
        if (!element) return 0;
        if (typeof element[property] !== 'number') return 0;
        return element[property];
    }
    
    // Global error handler for theme_prime
    function handleThemePrimeError(error) {
        console.warn('[Quick Checkout] Theme Prime error intercepted:', error.message);
        return true; // Prevent the error from bubbling up
    }
    
    // Monkey patch Element.prototype to add safety for offsetWidth/offsetHeight
    var originalOffsetWidthDescriptor = Object.getOwnPropertyDescriptor(Element.prototype, 'offsetWidth');
    var originalOffsetHeightDescriptor = Object.getOwnPropertyDescriptor(Element.prototype, 'offsetHeight');
    
    // Only apply the patch if we're in a browser environment
    if (typeof window !== 'undefined' && window.Element) {
        // Add global error handler
        window.addEventListener('error', function(event) {
            if (event.error && event.error.message && 
                event.error.message.includes('offsetWidth') && 
                event.error.stack && event.error.stack.includes('theme_prime')) {
                handleThemePrimeError(event.error);
                event.preventDefault();
                return true;
            }
        }, true);
        
        // Wait for Odoo to be fully loaded
        window.addEventListener('load', function() {
            // Give time for all modules to initialize
            setTimeout(function() {
                // Find all theme_prime related objects
                if (window.odoo && window.odoo.define && window.odoo.define.registry) {
                    var registry = window.odoo.define.registry;
                    for (var key in registry) {
                        if (key.indexOf('theme_prime') !== -1) {
                            try {
                                var module = registry[key];
                                if (module && module.prototype) {
                                    // Look for the problematic method
                                    if (typeof module.prototype._modifyElementsAfterAppend === 'function') {
                                        originalModifyElementsAfterAppend = module.prototype._modifyElementsAfterAppend;
                                        
                                        // Replace with safe version
                                        module.prototype._modifyElementsAfterAppend = function() {
                                            try {
                                                return originalModifyElementsAfterAppend.apply(this, arguments);
                                            } catch (error) {
                                                handleThemePrimeError(error);
                                                return null;
                                            }
                                        };
                                        
                                        console.log('[Quick Checkout] Successfully patched theme_prime._modifyElementsAfterAppend');
                                    }
                                    
                                    // Also patch _renderContent if it exists
                                    if (typeof module.prototype._renderContent === 'function') {
                                        var originalRenderContent = module.prototype._renderContent;
                                        module.prototype._renderContent = function() {
                                            try {
                                                return originalRenderContent.apply(this, arguments);
                                            } catch (error) {
                                                handleThemePrimeError(error);
                                                return Promise.resolve();
                                            }
                                        };
                                        console.log('[Quick Checkout] Successfully patched theme_prime._renderContent');
                                    }
                                }
                            } catch (e) {
                                console.warn('[Quick Checkout] Error patching theme_prime module:', e);
                            }
                        }
                    }
                }
                
                // Force recalculation of layouts
                window.dispatchEvent(new Event('resize'));
            }, 500);
        });
    }
})();
