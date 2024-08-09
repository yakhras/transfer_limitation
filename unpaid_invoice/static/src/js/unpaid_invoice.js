odoo.define('owl.call_button', function (require) {
    "use strict";

    const ReportAction = require('report.client_action');
    var core = require('web.core');
    // const ListView = require('web.ListView');
    // var viewRegistry = require('web.view_registry');
   
    // ListController Inherites,
    // Add Button Template,
    // Add click Event.
    const UnpaidReportAction = ReportAction.extend({
        hasControlPanel: true,
        contentTemplate: 'report.client_action',

        init: function (parent, action, options) {
            this._super.apply(this, arguments);
        },

        start: function () {
            var self = this;
            this.iframe = this.$('iframe')[0];
            this.$buttons = $(QWeb.render('unpaid_button.buttons', {}));
            this.$buttons.on('click', '.call_unpaid', this.call_unpaid);
            this.controlPanelProps.cp_content = {
                $buttons: this.$buttons,
            };
        },
        // buttons_template: "unpaid_button.buttons123",
        // events: _.extend({}, ListController.prototype.events, {
        //     "click .call_unpaid": "get_call_unpaid",
        // }),
        // get_call_unpaid () {
        //     console.log('Hi Yassor');
        //     this.do_action('unpaid_invoice.unpaid_invoices_action');
        //     console.log('Hi Yaser');
        // },
    })

    // ListView Inherits.
    // const UnpaidListView = ListView.extend({
    //     config: _.extend({}, ListView.prototype.config, {
    //         Controller: UnpaidReportAction,
    //     }),
    // })

    // Register ListView with js Class
    // viewRegistry.add('unpaid_list', UnpaidListView);

    core.action_registry.add('report.client_action', UnpaidReportAction);

});