odoo.define('owl_pos.call_button', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    const ListView = require('web.ListView');

    const UnpaidListController = ListController.extend({
        events: _.extend({}, ListController.prototype.events, {
            "click .call_unpaid": "get_call_unpaid",
        }),
        get_call_unpaid() {
            console.log("Hello Yaser");
        },
    });

    var UnpaidListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: UnpaidListController,
        }),
    });

    viewRegistry.add('unpaid_list', UnpaidListView);

});