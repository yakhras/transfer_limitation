odoo.define('owl.call_button', function (require) {
    "use strict";

    const ListController = require('web.ListController');
    //const ListRenderer = require('web.ListRenderer')
    const ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    // ListController Inherites,
    // Add Button Template,
    // Add click Event.
    const UnpaidListController = ListController.extend({
        buttons_template: "unpaid_button.buttons",
        events: _.extend({}, ListController.prototype.events, {
            "click .call_unpaid": "get_call_unpaid",
        }),
        get_call_unpaid () {
            console.log('Hi Yassor');
            this.do_action('unpaid_invoice.unpaid_invoice_view_filter');
            console.log('Hi Yaser');
        },

    });

    // ListRenderer Inherits.
 /*   const UnpaidListRenderer = ListRenderer.extend({
        events: _.extend({}, ListRenderer.prototype.events, {
            "click .call_unpaid": "get_call_unpaid",
        }),
        get_call_unpaid() {
            this._rpc({
                model: 'ir.ui.view',
                method: 'get_view_id',
                args: ['account.view_account_invoice_filter'],
            });
            console.log('Hi Yassor');
        },
    });
*/
    // ListView Inherits.
    const UnpaidListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: UnpaidListController,
        }),
    });

    // Register ListView with js Class
    viewRegistry.add('unpaid_list', UnpaidListView);

});