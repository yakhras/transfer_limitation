odoo.define('pos_invoice.SaleOrderScreen', function (require) {
    'use strict';

    const { useState } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const ProductScreen = require('point_of_sale.ProductScreen');


    const ZProductScreen = (ProductScreen) =>
		class extends ProductScreen {
			constructor() {
				super(...arguments);
			}
        async _onClickPay() {
            console.log('Hi Yaser');
            const order = self.env.pos.get_order();
            const currentClient = this.order.get_order();
            const { confirmed, payload: selectedOption } = await this.showPopup('SalesSelectionPopup',
                {
                    title: this.env._t('Select an Invoice'),
                    list: [
                            {
                                id:1, 
                                label: this.env._t("Formal Invoice"), 
                                item: true,
                                icon: 'fa fa-check-circle',
                            }, 
                        {
                            id:2, 
                            label: this.env._t("Informal Invoice"), 
                            item: false,
                            icon: 'fa fa-close',
                        }
                    ],
                });
            if (confirmed){
                if(selectedOption){
                   console.log('True');
                   console.log(currentClient);
                    }
                }
                if (!selectedOption){
                    console.log('False');
                    }
            
        }
    }
    

    Registries.Component.extend(ProductScreen, ZProductScreen);


    return ProductScreen;
});