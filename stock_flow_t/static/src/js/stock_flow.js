// odoo.define('stock_flow_t.stock_flow_refresh', function (require) {
//     "use strict";
    
//     var ListController = require('web.ListController');
    
//     ListController.include({
//         start: function () {
//             if (this.modelName === 'stock.product.flow.report') {
//                 this._rpc({
//                     model: 'stock.product.flow.report',
//                     method: 'refresh_materialized_view',
//                 });
//             }
//             return this._super.apply(this, arguments);
//         }
//     });
// });

odoo.define('stock_flow_t.stock_flow_refresh', function (require) {
    "use strict";
    
    var AbstractController = require('web.AbstractController');
    
    AbstractController.include({
        willStart: function () {
            var self = this;
            if (this.modelName === 'stock.product.flow.report') {
                return this._rpc({
                    model: 'stock.product.flow.report',
                    method: 'refresh_materialized_view',
                }).then(function () {
                    return self._super.apply(self, arguments);
                });
            }
            return this._super.apply(self, arguments);
        }
    });
});