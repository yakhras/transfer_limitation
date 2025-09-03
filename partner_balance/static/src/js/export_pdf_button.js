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
    
    balanceExport() {
        let exportedFields = this.defaultExportFields.map(field => ({
            name: field,
            label: this.record.fields[field].string,
            store: this.record.fields[field].store,
            type: this.record.fields[field].type,
        }));
        this._balanceExportData(exportedFields, 'xlsx', false);
    },
    /**
     * Submit the user data and export the file
     * Extended to add console logging of data
     *
     * @private
     */
    _balanceExportData(exportedFields, exportFormat, idsToExport) {

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
            url: '/web/balance_export/' + exportFormat,
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
        'click .o_currency_report': '_onCurrency',
        'change .date-input': '_onDateChange',
        'click .currency-tab': '_onCurrencyTabClick',
    }),
    currencies: [],


    _onCurrencyTabClick: function(ev) {
        var $clickedTab = $(ev.currentTarget);
        var currencyName = $clickedTab.data('currency');
        
        console.log('Selected currency:', currencyName);
        
        // Update active tab visual state
        this.$('.currency-tab').removeClass('active');
        $clickedTab.addClass('active');
        
        // Update active content

        var $allContent = this.$('.currency-content');
        var $targetContent = this.$('.currency-content[data-currency="' + currencyName + '"]');
        
        $allContent.removeClass('active');
        $targetContent.addClass('active');
    },

    _setupSummaryDisplay: function() {
        var context = this.model.loadParams.context || {};
        
        // Check if this is currency-grouped report
        if (context.group_by === 'currency_id' || context.action_name === 'Statement Currency-based of Account') {
            this._showCurrencyTabs();
        } else {
            this._showSingleRowSummary();
        }
    },


    _showSingleRowSummary: function() {
        // Hide tabs, show single row
        this.$('.currency-tabs-container').hide();
        this.$('.single-row-summary').show();
    },


    _showCurrencyTabs: function() {
        // Hide single row, show tabs
        this.$('.single-row-summary').hide(); 
        this.$('.currency-tabs-container').show();
    },


    _onDateChange: async function(ev) {
        const fieldName = $(ev.currentTarget).data('field-name');
        const value = $(ev.currentTarget).val();
        
        // Get both date values
        const dateFrom = this.$('.date-input[data-field-name="date_from"]').val();
        const dateTo = this.$('.date-input[data-field-name="date_to"]').val();
        const summarySection = this.$('.balance-summary-section');

        if (!dateFrom) {
            summarySection.hide();
            if (dateTo) {
                await this._updateViewWithDates(null, dateTo);
            } else {
                await this._updateViewWithDates(null, null);
            }
            return;
        }

        if (dateTo && new Date(dateTo) <= new Date(dateFrom)) {
            $(ev.currentTarget).val('');
            summarySection.hide();
            this.displayNotification({ message: 'End date must be after start date', type: 'warning' });
            return;
        }

        // await the update so the model actually contains initial_balance
        await this._updateViewWithDates(dateFrom, dateTo);
        // await this._buildCurrencyTabs();
        this._updateCurrencyBalances();
        this._setupSummaryDisplay();
        await this._updateSummaryFromModel();
        summarySection.show();
    },

    
    _getAvailableCurrencies: function() {
        var context = this.model.loadParams.context || {};
        var state = this.model.get(this.handle);
        var currencies = [];

        if (context.group_by === 'currency_id' || context.action_name === 'Statement Currency-based of Account') {
            state.data.forEach(function(group) {
                if (group.res_id && group.value) {
                    currencies.push({
                        id: group.res_id,
                        name: group.value,
                    });
                }
                
            });
        } else {
            // If not grouped by currency, default to company currency
                currencies.push({
                    id: 31,
                    name: 'TRY', // Currency code
                });
        }
        console.log('Available Currencies:', currencies);
        
        return currencies;
    },

   

    _buildCurrencyTabs: function() {
        console.log('_buildCurrencyTabs called');
        var self = this;
        var currencies = this._getAvailableCurrencies();
        console.log('Currencies:', currencies);
        // Handle the Promise returned by _getCurrencyBalances
        this._getCurrencyBalance().then(function(currencyBalances) {
            console.log('Fetched Currency Balances:', currencyBalances);
            console.log('RPC completed, updating template');
            
            var tabs = currencies.map((curr, i) => 
                `<div class="currency-tab ${i === 0 ? 'active' : ''}" data-currency="${curr.name}">${curr.name}</div>`
            ).join('');

            var content = currencies.map((curr, i) => {
                // ← Get the specific balance data for THIS currency
                var balanceData = currencyBalances[curr.name] || {
                    opening: 0,
                };
                
                return `<div class="currency-content ${i === 0 ? 'active' : ''}" data-currency="${curr.name}">
                    <div class="balance-summary-row">
                        <span class="summary-cell">Opening Balance:</span>
                        <span class="summary-cell amount">${self._formatCurrency(balanceData.opening, curr.name)}</span>
                    </div>
                </div>`;
            }).join('');

            self.$('.currency-tabs-container').html(`
                <div class="horizontal-layout">
                    <div class="tabs-wrapper">${tabs}</div>
                    <div class="content-wrapper">${content}</div>
                </div>
            `);
        });

    },

    

    _getCurrencyBalance: function() {
        var self = this;
        var context = this.model.loadParams.context || {};
        var domain = this.model.loadParams.domain || [];
        
        // Make direct RPC call to get currency balances
        return this._rpc({
            model: 'account.move.line.report',
            method: 'search_read',
            args: [domain],
            kwargs: {
                fields: ['currency_id', 'initial_balance_amount_currency'],
                context: context,
                limit: 1000 // Adjust as needed
            }
        }).then(function(records) {
            var currencyBalances = {};
            
            // Group by currency and get first occurrence of each
            records.forEach(function(record) {
                var currencyKey = record.currency_id ? record.currency_id[1] : 'TRY';
                
                if (!currencyBalances[currencyKey]) {
                    currencyBalances[currencyKey] = {
                        opening: record.initial_balance_amount_currency || 0,
                    };
                }
            });
            console.log('Fetched Currency Balances:', currencyBalances);
            return currencyBalances;
        });
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
            
            return this.update({domain: domain, context: context});
            
            
        } catch (error) {
            console.error('Error updating view with dates:', error);
        }
        console.log('context', this.model.loadParams.context);
    },
    

    _updateSummaryFromModel: function() {
        this.update({}, {reload: true});
        var state = this.model.get(this.handle);
        console.log('State Data:', state);
        const records = (state && state.data) || [];
        const initialBalance = records.length ? (records[0].data.initial_balance || 0) : 0;
        
        console.log('Initial Balance:', initialBalance);
        
        // Update the template element
        this.$('.summary-cell.final-balance').text(this._formatCurrency(initialBalance));
        
    },


    _formatCurrency(value) {
        return '₺' + Number(value || 0).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
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
    _getBalanceExportDialogWidget() {
        let state = this.model.get(this.handle);
        let defaultExportFields = this.renderer.columns.filter(field => field.tag === 'field' && state.fields[field.attrs.name].exportable !== false).map(field => field.attrs.name);
        let groupedBy = this.renderer.state.groupedBy;
        const domain = this.isDomainSelected && state.getDomain();
        return new DataExportExtended(this, state, defaultExportFields, groupedBy,
            domain, this.getSelectedIds());
    },


    // Method to prepare data for template
    _prepareCurrencyData: function() {
        var self = this;
        var availableCurrencies = this._getAvailableCurrencies();
        
        this._getCurrencyBalance().then(function(currencyBalances) {
            // Prepare data array for QWeb template
            self.currencies = availableCurrencies.map(function(curr, index) {
                var balanceData = currencyBalances[curr.name] || {opening: 0};
                
                return {
                    name: curr.name,
                    balance: balanceData.opening,
                    is_first: index === 0  // For active class
                };
            });
            
            // Re-render the template section
            self._renderCurrencyTabs();
        });
    },

    // Method to re-render template
    _renderCurrencyTabs: function() {
        var $container = this.$('.currency-tabs-container');
        var newContent = QWeb.render('PartnerBalance.Buttons.CurrencyTabs', {
            widget: this
        });
        $container.html(newContent);
    },

    // Helper method for template
    formatCurrency: function(value, currency) {
        var symbol = currency === 'TRY' ? '₺' : 
                    currency === 'USD' ? '$' : 
                    currency === 'EUR' ? '€' : currency + ' ';
        
        return symbol + Number(value || 0).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    },

    // Call when needed (date filter change, etc.)
    _updateCurrencyBalances: function() {
        this._prepareCurrencyData();
    },


    _onCurrency: function () {

        const ctx = this.model?.loadParams?.context || {};
        const partner_id = ctx.default_partner_id;
        if (!partner_id) {
            return;
        }

        this.do_action('partner_balance.action_partner_move_line_currency', {
            additional_context: {
                active_id: partner_id,
                active_ids: [partner_id],
                active_model: 'res.partner',
                default_partner_id: partner_id,
                partner_name: ctx.partner_name || '',
                action_name: 'Statement Currency-based of Account',
            },
        });
    },


    _onExcel: function () {
        console.log('Exporting to Excel');
        return this._rpc({
            model: 'ir.exports',
            method: 'search_read',
            args: [[], ['id']],
            limit: 1,
        }).then(() => this._getBalanceExportDialogWidget().balanceExport())
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

