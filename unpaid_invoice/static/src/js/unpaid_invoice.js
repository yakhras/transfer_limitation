odoo.define('owl_pos.call_button', function (require) {
    "use strict";
    var ListController = require('web.LoistController');
    ListController.include({
        events: _.extend({}, ListController.prototype.events, {
            "click .call_custom": console.log("Hi Yaser"),
        }),
        
    });
});
    