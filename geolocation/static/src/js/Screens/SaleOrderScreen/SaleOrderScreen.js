odoo.define('geolocation.getLocation', function (require) {
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
            let long = 'yaser';
            let order = this.env.pos.get_order();
            let currentClient = order.get_client().id
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
                    ],
                });
            if (confirmed){
                if(selectedOption){
                    console.log('True');
                //     navigator.geolocation.getCurrentPosition((position) => {
                //         return long = position.coords.longitude,
                //         // lat : position.coords.latitude,
                     
                //     console.log("long", long) ;
                //     // console.log(lat);
                    
                //    });
                   await this.env.services.rpc({
                    model: 'res.partner',
                    method: 'geo',
                    args: [currentClient],
                    long: long,
                   });
                   console.log(long)
                };
            }
            super._onClickPay();
        }
    }
    

    Registries.Component.extend(ProductScreen, ZProductScreen);


    return ProductScreen;
});