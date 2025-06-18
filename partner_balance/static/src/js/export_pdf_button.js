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
        console.log('Hi Yaser')
        const domain = this.get('domain');
        const context = this.model.get('context');
        const order = this.model.get('order');
        const viewId = this.viewId;
        console.log('domain', sessionStorage.getItem(['type']));
        console.log('context', sessionStorage);
        this._rpc({
            model: 'report.partner_balance.xlsx_report',
            method: 'button_export_xlsx',
            args: [domain, context, order, viewId],
        }).then(function (action) {
            if (action && action.type === 'ir.actions.act_url') {
                window.location.href = action.url;
            }
        });
    }
});


var BalanceListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: ExportPdfButtonListController,
    }),
});


viewRegistry.add('partner_balance', BalanceListView);
});
