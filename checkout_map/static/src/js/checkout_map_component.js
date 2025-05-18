/** @odoo-module **/

import { Component, useState, onMounted, useRef, mount, xml } from '@odoo/owl';
import { registry } from '@web/core/registry';

/**
 * Checkout Map Component
 * An Owl component that provides an interactive map for selecting a location during checkout
 */
class CheckoutMapComponent extends Component {
    setup() {
        this.state = useState({
            isLoading: true,
            error: null,
            location: {
                latitude: null,
                longitude: null,
                address: '',
            },
            mapInitialized: false
        });
        
        this.mapRef = useRef('mapContainer');
        this.map = null;
        this.marker = null;
        
        onMounted(() => this.initializeMap());
    }
    
    /**
     * Initialize the map with Leaflet
     */
    async initializeMap() {
        try {
            console.log('Initializing map component...');
            // Wait for Leaflet to be loaded
            console.log('Loading Leaflet resources...');
            await this._loadLeafletResources();
            console.log('Leaflet resources loaded, window.L:', window.L ? 'available' : 'not available');
            
            // Set default icon paths for Leaflet markers
            if (window.L && window.L.Icon && window.L.Icon.Default) {
                // Always use CDN resources for marker icons to ensure they load properly
                const baseUrl = 'https://unpkg.com/leaflet@1.9.4/dist/images';
                
                console.log('Setting default icon paths to CDN:', baseUrl);
                
                // Delete the default icon first to prevent issues with prototype inheritance
                delete L.Icon.Default.prototype._getIconUrl;
                
                // Set default icon paths using the proper method
                L.Icon.Default.mergeOptions({
                    iconUrl: `${baseUrl}/marker-icon.png`,
                    iconRetinaUrl: `${baseUrl}/marker-icon-2x.png`,
                    shadowUrl: `${baseUrl}/marker-shadow.png`,
                    iconSize: [25, 41],
                    iconAnchor: [12, 41],
                    popupAnchor: [1, -34],
                    shadowSize: [41, 41]
                });
                
                // Create a test image to verify the icon path works
                const testImage = new Image();
                testImage.onload = () => console.log('Marker icon path verified successfully');
                testImage.onerror = () => console.warn('Marker icon path may be incorrect');
                testImage.src = `${baseUrl}/marker-icon.png`;
            }
            
            // Initialize map
            const mapContainer = this.mapRef.el;
            console.log('Map container reference:', mapContainer);
            
            if (!mapContainer || this.state.mapInitialized) {
                console.log('Map already initialized or container not found');
                return;
            }
            
            console.log('Creating map instance...');
            
            // Create map centered on a default location (can be updated)
            this.map = L.map(mapContainer).setView([24.7136, 46.6753], 13); // Default to Riyadh
            
            // Add OpenStreetMap tiles
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(this.map);
            
            // Add a marker that can be dragged with explicit icon configuration
            this.marker = L.marker([24.7136, 46.6753], {
                draggable: true,
                icon: new L.Icon.Default() // Explicitly create a new default icon instance
            }).addTo(this.map);
            
            // Update location when marker is dragged
            this.marker.on('dragend', this._onMarkerDragEnd.bind(this));
            
            // Try to get user's current location
            this._getCurrentLocation();
            
            this.state.mapInitialized = true;
            this.state.isLoading = false;
        } catch (error) {
            this.state.error = "Failed to initialize map: " + error.message;
            this.state.isLoading = false;
            console.error("Map initialization error:", error);
        }
    }
    
    /**
     * Load Leaflet CSS and JS resources from local files
     * with fallback to CDN if local files fail to load
     */
    async _loadLeafletResources() {
        return new Promise((resolve, reject) => {
            // Check if Leaflet is already loaded
            if (window.L) {
                console.log('Leaflet already loaded, using existing instance');
                resolve();
                return;
            }
            
            // Load directly from CDN instead of trying local files first
            console.log('Loading Leaflet resources directly from CDN');
            
            // Track loading status
            let cssLoaded = false;
            let jsLoaded = false;
            
            // Function to check if both resources are loaded
            const checkAllLoaded = () => {
                if (cssLoaded && jsLoaded && window.L) {
                    console.log('All Leaflet resources loaded successfully');
                    resolve();
                }
            };
            
            // Load CSS from CDN
            const linkElement = document.createElement('link');
            linkElement.rel = 'stylesheet';
            linkElement.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
            linkElement.onload = () => {
                console.log('Leaflet CSS loaded from CDN');
                cssLoaded = true;
                checkAllLoaded();
            };
            document.head.appendChild(linkElement);
            
            // Load JS from CDN
            const scriptElement = document.createElement('script');
            scriptElement.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
            scriptElement.onload = () => {
                console.log('Leaflet JS loaded from CDN');
                jsLoaded = true;
                checkAllLoaded();
            };
            scriptElement.onerror = (error) => {
                console.error('Failed to load Leaflet JS from CDN:', error);
                reject(error);
            };
            document.head.appendChild(scriptElement);
            
            // Set a timeout to ensure we don't wait forever
            setTimeout(() => {
                if (!cssLoaded || !jsLoaded) {
                    console.warn('Timeout loading Leaflet resources, trying CDN');
                }
            }, 5000);
        });
    }
    
    /**
     * Get user's current location using browser geolocation
     */
    _getCurrentLocation() {
        if (!navigator.geolocation) {
            this.state.error = "Geolocation is not supported by your browser";
            return;
        }
        
        navigator.geolocation.getCurrentPosition(
            this._onLocationSuccess.bind(this),
            this._onLocationError.bind(this),
            { enableHighAccuracy: true }
        );
    }
    
    /**
     * Handle successful geolocation
     */
    _onLocationSuccess(position) {
        const { latitude, longitude } = position.coords;
        
        // Update state
        this.state.location.latitude = latitude;
        this.state.location.longitude = longitude;
        
        // Update map and marker
        if (this.map && this.marker) {
            this.map.setView([latitude, longitude], 15);
            this.marker.setLatLng([latitude, longitude]);
            
            // Get address from coordinates
            this._reverseGeocode(latitude, longitude);
        }
    }
    
    /**
     * Handle geolocation error
     */
    _onLocationError(error) {
        let errorMessage = "Failed to get your location";
        
        switch (error.code) {
            case error.PERMISSION_DENIED:
                errorMessage = "You denied the request for geolocation";
                break;
            case error.POSITION_UNAVAILABLE:
                errorMessage = "Location information is unavailable";
                break;
            case error.TIMEOUT:
                errorMessage = "The request to get your location timed out";
                break;
            case error.UNKNOWN_ERROR:
                errorMessage = "An unknown error occurred";
                break;
        }
        
        this.state.error = errorMessage;
        console.error("Geolocation error:", errorMessage);
    }
    
    /**
     * Handle marker drag end event
     */
    _onMarkerDragEnd(event) {
        const marker = event.target;
        const position = marker.getLatLng();
        
        // Update state with new coordinates
        this.state.location.latitude = position.lat;
        this.state.location.longitude = position.lng;
        
        // Get address from coordinates
        this._reverseGeocode(position.lat, position.lng);
    }
    
    /**
     * Get address from coordinates using OpenStreetMap Nominatim
     */
    async _reverseGeocode(latitude, longitude) {
        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1`);
            const data = await response.json();
            
            if (data && data.display_name) {
                this.state.location.address = data.display_name;
                
                // Update hidden form fields
                this._updateFormFields();
            }
        } catch (error) {
            console.error("Reverse geocoding error:", error);
        }
    }
    
    /**
     * Update hidden form fields with location data
     */
    _updateFormFields() {
        const { latitude, longitude, address } = this.state.location;
        
        // Update hidden form fields
        // Use mapRef.el instead of this.el which might be undefined
        const mapElement = this.mapRef.el;
        if (!mapElement) return;
        
        const form = mapElement.closest('form');
        if (!form) return;
        
        // Create or update hidden fields
        this._createOrUpdateHiddenField(form, 'latitude', latitude);
        this._createOrUpdateHiddenField(form, 'longitude', longitude);
        this._createOrUpdateHiddenField(form, 'map_address', address);
    }
    
    /**
     * Create or update a hidden field in the form
     */
    _createOrUpdateHiddenField(form, name, value) {
        let field = form.querySelector(`input[name="${name}"]`);
        
        if (!field) {
            field = document.createElement('input');
            field.type = 'hidden';
            field.name = name;
            form.appendChild(field);
        }
        
        field.value = value;
    }
    
    /**
     * Handle refresh location button click
     */
    onRefreshLocation() {
        this._getCurrentLocation();
    }
}

// Define the template using xml tagged template literal
CheckoutMapComponent.template = xml`
    <div class="checkout-map-container">
        <div t-if="state.isLoading" class="alert alert-info">
            <i class="fa fa-spinner fa-spin"></i> Loading map...
        </div>
        <div t-if="state.error" class="alert alert-danger">
            <i class="fa fa-exclamation-triangle"></i> <t t-esc="state.error"/>
        </div>
        <div t-ref="mapContainer" class="checkout-map" style="height: 300px; width: 100%; border-radius: 8px;"></div>
        <div class="mt-2 d-flex justify-content-between align-items-center">
            <div t-if="state.location.address" class="text-muted">
                <small><i class="fa fa-map-marker"></i> <t t-esc="state.location.address"/></small>
            </div>
            <button t-on-click="onRefreshLocation" class="btn btn-sm btn-secondary">
                <i class="fa fa-refresh"></i> Use My Location
            </button>
        </div>
    </div>
`;
CheckoutMapComponent.props = {};

// Register component in the frontend registry
const frontendComponents = registry.category('frontend_components');
frontendComponents.add('checkout_map', CheckoutMapComponent);

// Create a function to manually initialize the component on specific pages
function initCheckoutMapOnAddressPage() {
    console.log('Checking if we need to initialize map on address page...');
    
    // Check if we're on the checkout or address page
    if (window.location.pathname.includes('/shop/address') || 
        window.location.pathname.includes('/shop/checkout')) {
        console.log('We are on the checkout/address page, looking for map container...');
        
        // Look for the container where we want to mount the component
        let container = document.getElementById('checkout-map-component');
        
        // If container doesn't exist, create it
        if (!container) {
            console.log('Map container not found, creating one...');
            container = document.createElement('div');
            container.id = 'checkout-map-component';
            container.className = 'mt-3 mb-4';
            
            // Find a good place to insert the container
            const addressForm = document.querySelector('form[action*="/shop/address"]') || 
                               document.querySelector('form[action*="/shop/checkout"]');
            
            if (addressForm) {
                console.log('Found address form, inserting map container...');
                // Insert before the submit button or at the end of the form
                const submitButton = addressForm.querySelector('button[type="submit"]');
                if (submitButton && submitButton.parentElement) {
                    const buttonContainer = submitButton.closest('.row') || submitButton.parentElement;
                    addressForm.insertBefore(container, buttonContainer);
                } else {
                    addressForm.appendChild(container);
                }
            } else {
                console.log('Address form not found');
                return; // Exit if we can't find a form to attach to
            }
        }
        
        if (!container.hasAttribute('data-map-initialized')) {
            console.log('Initializing map component...');
            
            // Mark as initialized to prevent multiple initializations
            container.setAttribute('data-map-initialized', 'true');
            
            // Create and mount the component using the Owl mount function
            mount(CheckoutMapComponent, container, {});
            
            console.log('Map component mounted successfully');
        } else {
            console.log('Map component already initialized');
        }
    } else {
        console.log('Not on checkout/address page, current path:', window.location.pathname);
    }
}

// Initialize on DOM ready and page load
document.addEventListener('DOMContentLoaded', initCheckoutMapOnAddressPage);
window.addEventListener('load', initCheckoutMapOnAddressPage);

// Initialize immediately if the DOM is already loaded
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(initCheckoutMapOnAddressPage, 100);
}

export { CheckoutMapComponent };
