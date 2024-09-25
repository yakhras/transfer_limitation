odoo.define('pos_custom.model', function(require) {
	"use strict";

	const models = require('point_of_sale.models');

	models.load_fields('product.product', ['loc_avail_qty','type']);


});
