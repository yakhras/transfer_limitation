odoo.define('geolocation.device_geolocation', function (require) {
    "use strict";

    var rpc = require('web.rpc');

    // Function to get the geolocation of the user's device
    function getDeviceLocation(callback) {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(function (position) {
                var latitude = position.coords.latitude;
                var longitude = position.coords.longitude;
                callback(latitude, longitude);
            }, function (error) {
                console.log("Geolocation error: ", error.message);
                callback(null, null);
            });
        } else {
            console.log("Geolocation is not supported by this browser.");
            callback(null, null);
        }
    }

    // Function to save the location to the contact
    function saveLocationToContact(contactId, latitude, longitude) {
        rpc.query({
            model: 'res.partner',
            method: 'write',
            args: [[contactId], { 'latitude': latitude, 'longitude': longitude }],
        }).then(function (response) {
            console.log("Geolocation saved successfully");
        }).catch(function (error) {
            console.error("Error saving geolocation: ", error);
        });
    }

    // Example function to fetch and save the geolocation
    function updateContactWithLocation(contactId) {
        getDeviceLocation(function (latitude, longitude) {
            if (latitude && longitude) {
                saveLocationToContact(contactId, latitude, longitude);
            } else {
                console.log("Could not get device location");
            }
        });
    }

    return {
        updateContactWithLocation: updateContactWithLocation,
    };
});
