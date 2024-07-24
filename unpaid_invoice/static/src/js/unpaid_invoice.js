odoo.define('owl.call_button', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    const ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    const UnpaidListController = ListController.extend({
        buttons_template: "unpaid_button.buttons",
        events: _.extend({}, ListController.prototype.events, {
            "click .call_unpaid": "get_call_unpaid",
        }),
        get_call_unpaid() {
            this._rpc({
                model: 'ir.ui.view',
                method: 'get_view_id',
                args: ['account.view_account_invoice_filter'],
            })
        }
    })

    var UnpaidListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: UnpaidListController,
        }),
    });

    viewRegistry.add('unpaid_list', UnpaidListView);

});