odoo.define('partner_balance.listpdf', function (require) {
    "use strict";

var DataExport = require('web.DataExport');
var ListController = require('web.ListController');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');
var framework = require('web.framework');
var pyUtils = require('web.py_utils');
var DatePicker = require('web.DatePicker');
var fieldUtils = require('web.field_utils');

var DataExportExtended = DataExport.extend({
    /**
     * Submit the user data and export the file
     * Extended to add console logging of data
     *
     * @private
     */
    _exportData(exportedFields, exportFormat, idsToExport) {

        if (_.isEmpty(exportedFields)) {
            Dialog.alert(this, _t("Please select fields to export..."));
            return;
        }
        if (this.isCompatibleMode) {
            exportedFields.unshift({ name: 'id', label: _t('External ID') });
        }
        console.log('exportedFields', exportedFields);
        framework.blockUI();
        this.getSession().get_file({
            url: '/web/export/' + exportFormat,
            data: {
                data: JSON.stringify({
                    model: this.record.model,
                    fields: exportedFields,
                    ids: idsToExport,
                    domain: this.domain,
                    groupby: this.groupby,
                    context: pyUtils.eval('contexts', [this.record.getContext()]),
                    import_compat: this.isCompatibleMode,
                })
            },
            complete: framework.unblockUI,
            error: (error) => this.call('crash_manager', 'rpc_error', error),
        }),
        console.log(this.domain);
    },
});

var ExportPdfButtonListController = ListController.extend({
    buttons_template: 'PartnerBalance.Buttons',
    events: _.extend({}, ListController.prototype.events, {
        'click .o_button_pdf': '_onExport',
        'focus .partner-balance-date-input': '_onDateInputFocus',
    }),

    _onDateInputFocus: function(ev) {
        var $input = $(ev.currentTarget);
        $input.attr('type', 'date');
    },

    _onExport: function(){
        console.log('Hi Yaser')
        const domain = this.get('domain');
        const context = this.model.get('context');
        const order = this.model.get('order');
        const viewId = this.viewId;
        const actionData = JSON.parse(sessionStorage.getItem('current_action'));
        
        // Get date values
        const dateFrom = this.$('.partner-balance-date-input[data-field-name="date_from"]').val();
        const dateTo = this.$('.partner-balance-date-input[data-field-name="date_to"]').val();
        
        console.log('domain', actionData.domain);
        console.log('Selected dates:', { dateFrom, dateTo });
        
        this._rpc({
            model: 'account.move.line.report',
            method: 'export_to_excel',
            args: [[]],
            kwargs: {
                date_from: dateFrom,
                date_to: dateTo,
            }
        }).then(function (action) {
            if (action && action.type === 'ir.actions.act_url') {
                window.location.href = action.url;
            }
        });
    },

    /**
     * @returns {DataExportExtended} the export dialog widget
     * @private
     */
    _getExportDialogWidget() {
        let state = this.model.get(this.handle);
        let defaultExportFields = this.renderer.columns.filter(field => field.tag === 'field' && state.fields[field.attrs.name].exportable !== false).map(field => field.attrs.name);
        let groupedBy = this.renderer.state.groupedBy;
        const domain = this.isDomainSelected && state.getDomain();
        return new DataExportExtended(this, state, defaultExportFields, groupedBy,
            domain, this.getSelectedIds());
    },
});

var BalanceListView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Controller: ExportPdfButtonListController,
    }),
});

viewRegistry.add('partner_balance', BalanceListView);
return DataExportExtended;
});