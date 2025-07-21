odoo.define('stock_flow.stock_flow_refresh', function (require) {
    "use strict";
    
    var ListController = require('web.ListController');
    
    ListController.include({
        willStart: function () {
            var self = this;
            if (this.modelName === 'stock.product.flow.report') {
                // Call refresh method before loading
                return this._rpc({
                    model: 'stock.product.flow.report',
                    method: 'refresh_materialized_view',
                }).then(function () {
                    return self._super.apply(self, arguments);
                });
            }
            return this._super.apply(this, arguments);
        }
    });
});