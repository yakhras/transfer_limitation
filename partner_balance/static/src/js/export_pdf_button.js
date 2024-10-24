/** @odoo-module **/

var ListController = require('web.ListController');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');

var ExportPdfButtonListController = ListController.extend({
    buttons_template: 'BalanceListView.buttons',
    events: _.extend({}, ListController.prototype.events, {
        'click .call_unpaid': '_onExport',
    }),
    _onExport: function(){
        console.log('kjdfvndfkjbvn')
    }
});



var BalanceListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: ExportPdfButtonListController,
    }),
});

viewRegistry.add('partner_balance', BalanceListView);
