odoo.define('owl_pos.call_button', function (require) {
    "use strict";

    var ListController = require('web.ListController');

    ListController.include({
        events: _.extend({}, ListController.prototype.events, {
            "click .call_custom": "get_call_window",
        }),
        get_call_window: function(){
            console.log("Hello Yaser");
        },
    });
});
    