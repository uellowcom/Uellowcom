/** @odoo-module **/

import { Component, useState, onMounted, useRef } from '@odoo/owl';
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
            // Wait for Leaflet to be loaded
            await this._loadLeafletResources();
            
            // Initialize map
            const mapContainer = this.mapRef.el;
            if (!mapContainer || this.state.mapInitialized) return;
            
            // Create map centered on a default location (can be updated)
            this.map = L.map(mapContainer).setView([24.7136, 46.6753], 13); // Default to Riyadh
            
            // Add OpenStreetMap tiles
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(this.map);
            
            // Add a marker that can be dragged
            this.marker = L.marker([24.7136, 46.6753], {
                draggable: true
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
     * Load Leaflet CSS and JS resources
     */
    async _loadLeafletResources() {
        return new Promise((resolve, reject) => {
            // Check if Leaflet is already loaded
            if (window.L) {
                resolve();
                return;
            }
            
            // Load CSS
            const linkElement = document.createElement('link');
            linkElement.rel = 'stylesheet';
            linkElement.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
            document.head.appendChild(linkElement);
            
            // Load JS
            const scriptElement = document.createElement('script');
            scriptElement.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
            scriptElement.onload = resolve;
            scriptElement.onerror = reject;
            document.head.appendChild(scriptElement);
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
        let errorMessage;
        switch(error.code) {
            case error.PERMISSION_DENIED:
                errorMessage = "User denied the request for geolocation";
                break;
            case error.POSITION_UNAVAILABLE:
                errorMessage = "Location information is unavailable";
                break;
            case error.TIMEOUT:
                errorMessage = "The request to get user location timed out";
                break;
            default:
                errorMessage = "An unknown error occurred";
                break;
        }
        
        this.state.error = errorMessage;
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
        const form = this.el.closest('form');
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

CheckoutMapComponent.template = 'quick_checkout.CheckoutMapComponentTemplate';
CheckoutMapComponent.props = {};

// Register component in the frontend registry
const frontendComponents = registry.category('frontend_components');
frontendComponents.add('checkout_map', CheckoutMapComponent);

export { CheckoutMapComponent };
