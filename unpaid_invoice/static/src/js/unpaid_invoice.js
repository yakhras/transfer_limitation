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
        /**  
         @param {Object} group
        */
        get_call_unpaid () {
            console.log('Hi Yassor');
            this.do_action('unpaid_invoice.unpaid_invoices_action');
            console.log('Hi Yaser');
            console.log(group);
        },

    })

    // ListView Inherits.
    const UnpaidListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: UnpaidListController,
        }),
    })

    // Register ListView with js Class
    viewRegistry.add('unpaid_list', UnpaidListView);

});