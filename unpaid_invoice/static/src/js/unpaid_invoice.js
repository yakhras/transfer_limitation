odoo.define('button_near_create.tree_button', function (require) {
    "use strict";
    var rpc = require('web.rpc');
    var ListController = require('web.LoistController');
    ListController.include({
        events: _.extend({}, ListController.prototype.events, {
            "click .call_custom": "get_call_window",
        }),
        get_call_window: function(e){
            console.log("Hello Yaser");
        },
    });
});
    