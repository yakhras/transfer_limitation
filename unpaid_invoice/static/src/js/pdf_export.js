odoo.define('unpaid_invoice.print_pdf', function (require) {
    "use strict";
    var config = require('web.config');
    var core = require('web.core');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var ajax = require('web.ajax');

    var UnpaidListController = ListController.extend({
        buttons_template: 'UnpaidListView.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .o_button_unpaid_tree' : 'pdf_tree',
        }),
        pdf_tree: function () {
            var self = this;
            var fields = this._getExportDialogWidget().defaultExportFields;
            let exported_fields = this._getExportDialogWidget().defaultExportFields.map(field => ({
                name: field,
                label: this._getExportDialogWidget().record.fields[field].string,
            }));
            let groupedBy = this.renderer.state.groupedBy;
            var length_field = Array.from(Array(fields.length).keys());
            var records = this._getExportDialogWidget().record.res_ids
            var data_len = Array.from(Array(records.length).keys());
            var group_length = Array.from(Array(self.renderer.state.groupsCount).keys());
            ajax.jsonRpc('/get_data', 'call', {
                'field': fields,
                'model': this._getExportDialogWidget().record.model,
                'res_ids': records,
                'exported_fields': exported_fields,
                'grouped_by': groupedBy,
                'grouped_by_ids': this.initialState.res_ids,
                'amount': this.renderer.state.data.map(({ aggregateValues }) => aggregateValues),
                'domain': this._getExportDialogWidget().record.domain
            })
                .then(function (data) {
                    if (groupedBy[0]) {

                        var action = {
                            'type': 'ir.actions.report',
                            'report_type': 'qweb-pdf',
                            'report_name': 'unpaid_invoice.export_in_pdf_group_by',
                            'data': { 'length': length_field, 'group_len': group_length, 'record': data, }
                        };
                    }
                    else {
                        var action = {
                            'type': 'ir.actions.report',
                            'report_type': 'qweb-pdf',
                            'report_name': 'unpaid_invoice.export_in_pdf',
                            'data': { 'length': length_field, 'data_len': data_len, 'record': data }
                        };
                    }
                    return self.do_action(action);
                });
        }
    });
    var UnpaidListView = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: UnpaidListController,
        }),
    });
    viewRegistry.add('Pdf_tree', UnpaidListView);

});
