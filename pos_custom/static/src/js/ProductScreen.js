odoo.define('pos_custom.productScreen', function(require) {
	"use strict";

	const Registries = require('point_of_sale.Registries');
	const ProductScreen = require('point_of_sale.ProductScreen');

	const YProductScreen = (ProductScreen) =>
		class extends ProductScreen {
			constructor() {
				super(...arguments);
			}
			async _onClickPay() {
				var self = this;
				let order = self.env.pos.get_order();
				let lines = order.get_orderlines();
				let pos_config = self.env.pos.config;				
				let call_super = true;
				$.each(lines, function( i, line ){
					let prd = line.product;
					let remain = prd.loc_avail_qty - line.quantity;
					//let prod_used_qty = {};
					if(pos_config.out_qty){
						//prod_used_qty[prd.id] = [prd.loc_avail_qty,line.quantity]
						if (prd.type == 'product'){
							if(line.quantity == 0){
								call_super = false;
								let wrning = prd.display_name +' :' + ' \n You have to Enter more than Zero';
								self.showPopup('ErrorPopup', {
									title: self.env._t('Zero Quantity Not allowed'),
									body: self.env._t(wrning),
								});
							}
							//if(line.quantity > prd.loc_avail_qty){
							else if(remain < 0){
								call_super = false;
								let wrning = prd.display_name +' :'+ ' \n Quantity You Entered Not Available. \n You can just sell: ' + prd.loc_avail_qty;
								self.showPopup('ErrorPopup', {
									title: self.env._t('Enterd Quantity Not Available'),
									body: self.env._t(wrning),
								});
							}
							else{
								prd.loc_avail_qty = remain;
							}
						}
					}
					else{
						prd.loc_avail_qty = remain;
					}
				})
				if(call_super){	
					super._onClickPay();
				}
			}
		};

	Registries.Component.extend(ProductScreen, YProductScreen);

	return ProductScreen;

});
