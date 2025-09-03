/** @odoo-module **/

// Using standard JavaScript for translations since we're not using OWL components directly here
const _t = (str) => {
    // Try to use Odoo's translation if available
    if (window.odoo && odoo._t) {
        return odoo._t(str);
    }
    // Fallback to the original string
    return str;
};

/**
 * Map Location Helper
 * 
 * This module provides utilities for handling map locations in the checkout process.
 * It includes functions for geocoding, reverse geocoding, and handling location data.
 */

// Map location helper
const MapLocationHelper = {
    /**
     * Reverse geocode a location (get address from coordinates)
     * 
     * @param {Object} coords - Coordinates object with lat and lng properties
     * @returns {Promise} - Promise that resolves with the address data
     */
    reverseGeocode(coords) {
        return new Promise((resolve, reject) => {
            const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${coords.lat}&lon=${coords.lng}&zoom=18&addressdetails=1`;
            
            fetch(url, {
                method: 'GET',
                headers: {
                    'Accept-Language': odoo.lang_parameters?.code || 'en-US'
                },
            })
            .then(response => response.json())
            .then(data => resolve(data))
            .catch(error => {
                console.error('Reverse geocoding error:', error);
                reject(error);
            });
        });
    },

    /**
     * Geocode an address (get coordinates from address)
     * 
     * @param {String} address - Address to geocode
     * @returns {Promise} - Promise that resolves with the coordinates
     */
    geocode(address) {
        return new Promise((resolve, reject) => {
            const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(address)}&limit=1`;
            
            fetch(url, {
                method: 'GET',
                headers: {
                    'Accept-Language': odoo.lang_parameters?.code || 'en-US'
                },
            })
            .then(response => response.json())
            .then(data => {
                if (data && data.length > 0) {
                    resolve({
                        lat: parseFloat(data[0].lat),
                        lng: parseFloat(data[0].lon)
                    });
                } else {
                    reject(new Error('No results found'));
                }
            })
            .catch(error => {
                console.error('Geocoding error:', error);
                reject(error);
            });
        });
    },

    /**
     * Format address from Nominatim response
     * 
     * @param {Object} addressData - Address data from Nominatim
     * @returns {String} - Formatted address string
     */
    formatAddress(addressData) {
        if (!addressData || !addressData.address) {
            return '';
        }
        
        const address = addressData.address;
        const parts = [];
        
        // Add road and house number if available
        if (address.road) {
            let roadPart = address.road;
            if (address.house_number) {
                roadPart += ' ' + address.house_number;
            }
            parts.push(roadPart);
        }
        
        // Add suburb/neighborhood if available
        if (address.suburb) {
            parts.push(address.suburb);
        } else if (address.neighbourhood) {
            parts.push(address.neighbourhood);
        }
        
        // Add city
        if (address.city) {
            parts.push(address.city);
        } else if (address.town) {
            parts.push(address.town);
        } else if (address.village) {
            parts.push(address.village);
        }
        
        // Add state/province
        if (address.state) {
            parts.push(address.state);
        }
        
        // Add country
        if (address.country) {
            parts.push(address.country);
        }
        
        return parts.join(', ');
    },

    /**
     * Get the user's current location
     * 
     * @returns {Promise} - Promise that resolves with the coordinates
     */
    getCurrentLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error(_t('Geolocation is not supported by your browser')));
                return;
            }
            
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    });
                },
                (error) => {
                    console.error('Geolocation error:', error);
                    let errorMessage;
                    
                    switch (error.code) {
                        case error.PERMISSION_DENIED:
                            errorMessage = _t('User denied the request for geolocation');
                            break;
                        case error.POSITION_UNAVAILABLE:
                            errorMessage = _t('Location information is unavailable');
                            break;
                        case error.TIMEOUT:
                            errorMessage = _t('The request to get user location timed out');
                            break;
                        default:
                            errorMessage = _t('An unknown error occurred');
                    }
                    
                    reject(new Error(errorMessage));
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }
            );
        });
    },

    /**
     * Map address fields from Nominatim to checkout form fields
     * 
     * @param {Object} addressData - Address data from Nominatim
     * @returns {Object} - Mapped address fields for the checkout form
     */
    mapAddressToFormFields(addressData) {
        if (!addressData || !addressData.address) {
            return {};
        }
        
        const address = addressData.address;
        const mappedFields = {};
        
        // Map common fields
        if (address.road) {
            mappedFields.street = address.road;
            if (address.house_number) {
                mappedFields.street += ' ' + address.house_number;
            }
        }
        
        if (address.city) {
            mappedFields.city = address.city;
        } else if (address.town) {
            mappedFields.city = address.town;
        } else if (address.village) {
            mappedFields.city = address.village;
        }
        
        if (address.postcode) {
            mappedFields.zip = address.postcode;
        }
        
        if (address.state) {
            mappedFields.state = address.state;
        }
        
        if (address.country_code) {
            mappedFields.country_code = address.country_code.toUpperCase();
        }
        
        if (address.country) {
            mappedFields.country = address.country;
        }
        
        return mappedFields;
    }
};

export default MapLocationHelper;
