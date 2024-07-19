odoo.define('owl_pos.call_button', function (require) {
    "use strict";

    var ListController = require('web.ListController');

    /*ListController.include({
        events: _.extend({}, ListController.prototype.events, {
            "click .call_custom": "get_call_window",
        }),
        get_call_window: function(){
            console.log("Hello Yaser");
        },
    });*/

    var CustomButton = ListController.extend({}, {
        buttons_template: 'unpaid.button',
    })

    var buttonRegistry = require('web.view_registry');

    buttonRegistry.add('unpaid.button', CustomButton);
});
    