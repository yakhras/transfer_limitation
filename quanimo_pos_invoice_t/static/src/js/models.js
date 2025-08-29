odoo.define('quanimo_pos_invoice_t.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');

    models.load_fields('res.partner', ['property_is_printed_invoice']);

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        is_to_invoice: function () {
            this.to_invoice = false;
            if (this.pos.get_order().orderlines.length > 0) {
                this.to_invoice = true;
            }
            return _super_order.is_to_invoice.call(this, arguments);
        },
    });

});

