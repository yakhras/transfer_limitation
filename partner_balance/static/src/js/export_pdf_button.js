odoo.define('partner_balance.listpdf', function (require) {
    "use strict";


var DataExport = require('web.DataExport') ;
var ListController = require('web.ListController');
var ListView = require('web.ListView');
var viewRegistry = require('web.view_registry');
var framework = require('web.framework');
var pyUtils = require('web.py_utils');
var core = require('web.core');
var _t = core._t;


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
        'click .o_button_pdf': '_onPdf',
        'click .o_button_excel': '_onExcel',
        'change .date-input': '_onDateChange',
    }),

    _onDateChange: function(ev) {
        const fieldName = $(ev.currentTarget).data('field-name');
        const value = $(ev.currentTarget).val();
        
        // Get both date values
        const dateFrom = this.$('.date-input[data-field-name="date_from"]').val();
        const dateTo = this.$('.date-input[data-field-name="date_to"]').val();
        
        // Validate date range
        if (dateFrom && dateTo) {
            if (new Date(dateTo) <= new Date(dateFrom)) {
                $(ev.currentTarget).val('');
                this.displayNotification({
                    message: 'End date must be after start date',
                    type: 'warning'
                });
                return;
            }
            
            // Both dates valid - apply filter
            this._updateViewWithDates(dateFrom, dateTo);
        } else if (dateFrom || dateTo) {
            // Only one date selected - apply partial filter
            this._updateViewWithDates(dateFrom, dateTo);
        }
        // If no dates selected, reset the filter
        else {
            this._updateViewWithDates(null, null);
        }
    },

    _updateViewWithDates: function(dateFrom, dateTo) {
        try {
            // Get domain from correct location
            let domain = this.model.loadParams.domain || this.initialState.domain || [];
            let context = this.model.loadParams.context || {};
            
            // Remove existing date filters
            domain = domain.filter(filter => 
                !Array.isArray(filter) || (filter[0] !== 'date' && filter[0] !== 'date_from' && filter[0] !== 'date_to')
            );
            
            // Add new date filters
            if (dateFrom) {
                domain.push(['date', '>=', dateFrom]);
            }
            if (dateTo) {
                domain.push(['date', '<=', dateTo]);
            }
            
            context.date_from = dateFrom || null;  // Clear if empty
            context.date_to = dateTo || null;    
            
            // Update both locations
            this.model.loadParams.domain = domain;
            this.model.loadParams.context = context;
            if (this.initialState.domain) {
                this.initialState.domain = domain;
            }
            
            this.update({domain: domain, context: context});
            
        } catch (error) {
            console.error('Error updating view with dates:', error);
        }
        console.log('context', this.model.loadParams.context);
    },

    _onExport: function(){
        console.log('Hi Yaser')
        const domain = this.get('domain');
        const context = this.model.get('context');
        const order = this.model.get('order');
        const viewId = this.viewId;
        const actionData = JSON.parse(sessionStorage.getItem('current_action'));
        console.log('domain', actionData.domain);
        console.log('context', sessionStorage);
        this._rpc({
            model: 'account.move.line.report',
            method: 'export_to_excel',
            args: [[]],
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

    _onPdf: function () {
        console.log('Exporting to PDF');
    },

    _onExcel: function () {
        console.log('Exporting to Excel');
        return this._rpc({
            model: 'ir.exports',
            method: 'search_read',
            args: [[], ['id']],
            limit: 1,
        }).then(() => this._getExportDialogWidget().export())
    },

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

