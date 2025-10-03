odoo.define('partner_balance_t.listpdf', function (require) {
    "use strict";


var DataExport = require('web.DataExport') ;
var ListController = require('web.ListController');
var ListView = require('web.ListView');
// var ListRenderer = require('web.ListRenderer');
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

// var PartnerBalanceRenderer = ListRenderer.extend({
//     _renderGroupRow: function(group, groupLevel) {
//         var $row = this._super.apply(this, arguments);
        
//         try {
//             console.log('Adding balance aggregation for group:', group);
            
//             if (!group || !group.data || !this.state || !this.state.fields) {
//                 console.warn('Missing required data');
//                 return $row;
//             }
            
//             var $groupCell = $row.find('.o_group_name');
//             if ($groupCell.length === 0) {
//                 console.warn('Group cell not found');
//                 return $row;
//             }
            
//             var balanceField = this.state.fields['balance'];
//             if (!balanceField) {
//                 console.log('Balance field not found');
//                 return $row;
//             }
            
//             if (balanceField.type === 'float' || balanceField.type === 'integer' || balanceField.type === 'monetary') {
//                 var balanceSum = 1500;
                
//                 var formattedBalance;
//                 try {
//                     formattedBalance = this._formatFieldValue(balanceSum, balanceField);
//                 } catch(e) {
//                     formattedBalance = balanceSum.toFixed(2);
//                 }
                
//                 var $balanceSpan = $('<span class="o_list_number" style="margin-left: 20px;">Balance: ' + 
//                     formattedBalance + 
//                 '</span>');
                
//                 $groupCell.append($balanceSpan);
//                 console.log('Balance sum added:', balanceSum);
//             }
            
//         } catch(error) {
//             console.error('Balance aggregation error:', error);
//         }
        
//         return $row;
//     }
// });

var ExportPdfButtonListController = ListController.extend({
    buttons_template: 'PartnerBalance.Buttons',
    events: _.extend({}, ListController.prototype.events, {
        'click .o_button_pdf': '_getPartnersDetails',
        'click .o_button_excel': '_onExcel',
        'click .o_currency_report': '_onCurrency',
        'click .o_partner_currency': '_onPartnerCurrency',
        'change .date-input': '_onDateChange',
    }),

    
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
        this.$('.horizontal-currency-summary').hide();
        this.$('.single-row-summary').show();
    },


    _showCurrencyTabs: function() {
        // Hide single row, show tabs
        this.$('.single-row-summary').hide();
        this.$('.horizontal-currency-summary').show();
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
        await this._buildCurrencyTabs();
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
        
        return currencies;
    },


    _buildCurrencyTabs: function() {
        var self = this;
        var currencies = this._getAvailableCurrencies();
        
        this._getCurrencyBalance().then(function(currencyBalances) {
            
            // Build all currency blocks
            var currencyBlocksHtml = currencies.map(function(currency) {
                var balanceData = currencyBalances[currency.name] || {opening: 0};
                var formattedBalance = self._formatCurrency(balanceData.opening, currency.name);
                
                return `<div class="currency-block">
                    <span class="currency-label">${currency.name}</span>
                    <span class="final-balance">${formattedBalance}</span>
                </div>`;
            }).join('');
            
            // Update the container with all blocks at once
            self.$('.horizontal-currency-summary').html(currencyBlocksHtml);
        });
    },
    

    _getCurrencyBalance: function() {
        var self = this;
        var context = this.model.loadParams.context || {};
        var domain = this.model.loadParams.domain || [];
        console.log(domain);
        
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
            return currencyBalances;
        });
    },

    _getPartnersDetails: function() {
        var self = this;
        var user_id = this.getSession().user_id;
        return this._rpc({
            model: 'account.move.line.report', 
            method: 'partner_details',
            args: [[], user_id],
        }).then(function(users) {
            console.log(users);
            self.$('.currency-label').text(users.name + users.login);
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
    },
    

    _updateSummaryFromModel: function() {
        this.update({}, {reload: true});
        var state = this.model.get(this.handle);
        const records = (state && state.data) || [];
        console.log(records);
        const initialBalance = records.length ? (records[0].data.initial_balance || records[0].data.initial_balance_partner_currency || 0) : 0;
        
        
        // Update the template element
        this.$('.summary-cell.final-balance').text(this._formatCurrency(initialBalance));
        
    },


    _formatCurrency(value) {
        return Number(value || 0).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    },


    _onExport: function(){
        const domain = this.get('domain');
        const context = this.model.get('context');
        const order = this.model.get('order');
        const viewId = this.viewId;
        const actionData = JSON.parse(sessionStorage.getItem('current_action'));
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
    


    // _onCurrency: function () {

    //     const ctx = this.model?.loadParams?.context || {};
    //     const partner_id = ctx.default_partner_id;
    //     if (!partner_id) {
    //         return;
    //     }

    //     this.do_action('partner_balance_t.action_partner_move_line_currency', {
    //         additional_context: {
    //             active_id: partner_id,
    //             active_ids: [partner_id],
    //             active_model: 'res.partner',
    //             default_partner_id: partner_id,
    //             partner_name: ctx.partner_name || '',
    //             action_name: 'Statement Currency-based of Account',
    //         },
    //     });
    // },

    _onCurrency: function () {
        const ctx = this.model?.loadParams?.context || {};
        const partner_id = ctx.default_partner_id;
        
        if (partner_id) {
            this.do_action('partner_balance_t.action_partner_move_line_currency_from_partner', {
                additional_context: {
                    active_id: partner_id,
                    partner_name: ctx.partner_name || '',
                }
            });
        } else {
            const state = this.model.get(this.handle);
            this.do_action('partner_balance_t.action_partner_move_line_currency_from_lines', {
                domain: state.getDomain(),
                additional_context: state.getContext(),
            });
        }
    },

    // _onPartnerCurrency: function () {

    //     const ctx = this.model?.loadParams?.context || {};
    //     const partner_id = ctx.default_partner_id;
    //     if (!partner_id) {
    //         return;
    //     }

    //     this.do_action('partner_balance_t.action_partner_move_line_partner_currency', {
    //         additional_context: {
    //             active_id: partner_id,
    //             active_ids: [partner_id],
    //             active_model: 'res.partner',
    //             default_partner_id: partner_id,
    //             partner_name: ctx.partner_name || '',
    //             action_name: 'Statement in Partner Currency',
    //         },
    //     });
    // },

    // _onPartnerCurrency: function () {
    //     const ctx = this.model?.loadParams?.context || {};
    //     const partner_id = ctx.default_partner_id;
        
    //     // Called from res.partner form view
    //     if (partner_id) {
    //         this.do_action('partner_balance_t.action_partner_move_line_partner_currency', {
    //             additional_context: {
    //                 active_id: partner_id,
    //                 active_ids: [partner_id],
    //                 active_model: 'res.partner',
    //                 default_partner_id: partner_id,
    //                 partner_name: ctx.partner_name || '',
    //                 action_name: 'Statement in Partner Currency',
    //             },
    //             domain: [['partner_id', '=', partner_id]],
    //         });
    //     } 
    //     // Called from account.move.line list view
    //     else {
    //         const state = this.model.get(this.handle);
    //         const currentDomain = state.getDomain();
    //         const currentContext = state.getContext();
            
    //         this.do_action('partner_balance_t.action_partner_move_line_partner_currency', {
    //             additional_context: {
    //                 ...currentContext,
    //                 search_default_group_by_account: 1,
    //             },
    //             domain: currentDomain,
    //         });
    //     }
    // },

    _onPartnerCurrency: function () {
        const ctx = this.model?.loadParams?.context || {};
        const partner_id = ctx.default_partner_id;
        
        if (partner_id) {
            this.do_action('partner_balance_t.action_partner_move_line_partner_currency_from_partner', {
                additional_context: {
                    active_id: partner_id,
                    partner_name: ctx.partner_name || '',
                }
            });
        } else {
            const state = this.model.get(this.handle);
            this.do_action('partner_balance_t.action_partner_move_line_partner_currency_from_lines', {
                domain: state.getDomain(),
                additional_context: state.getContext(),
            });
        }
    },


    _onExcel: function () {
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
        // Renderer: PartnerBalanceRenderer,
    }),
});


viewRegistry.add('partner_balance_t', BalanceListView);
return DataExportExtended;
});

