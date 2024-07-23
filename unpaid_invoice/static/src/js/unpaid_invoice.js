odoo.define('owl_pos.call_button', function (require) {
    "use strict";

    var ListController = require('web.ListController');

    ListController.extend({
        events: _.extend({}, ListController.prototype.events, {
            "click .call_unpaid": "get_call_unpaid",
        }),
        get_call_unpaid() {
            console.log("Hello Yaser");
        },
    });

});