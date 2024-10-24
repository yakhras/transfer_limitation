odoo.define('partner_balance.listpdf', function (require) {
    "use strict";

var ListController = require('web.ListController');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');

var ExportPdfButtonListController = ListController.extend({
    buttons_template: 'PartnerBalance.Buttons',
    events: _.extend({}, ListController.prototype.events, {
        'click .o_button_pdf': '_onExport',
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
});