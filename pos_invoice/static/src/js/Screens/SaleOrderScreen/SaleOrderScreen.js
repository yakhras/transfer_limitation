odoo.define('pos_invoice.SaleOrderScreen', function (require) {
    'use strict';

    const { useState } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const ClientScreen = require('point_of_sale.ClientScreen');


    const ZProductScreen = (ClientScreen) =>
		class extends ClientScreen {
			constructor() {
				super(...arguments);
			}
        async cliclNext() {
            console.log('Hi Yaser');
            let order = this.env.pos.get_order();
            let currentClient = order.get_client()
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
                   await this.rpc({
                        model: 'res.partner',
                        method: 'formal_invoice',
                        args: [currentClient.id]
                    });
                console.log('formal');
                }
                if (!selectedOption){
                    console.log('False');
                    await this.rpc({
                        model: 'res.partner',
                        method: 'informal_invoice',
                        args: [currentClient.id]
                    });
                    console.log('informal');
                }
            }
            super.cliclNext();
                
            
        }
    }
    

    Registries.Component.extend(ClientScreen, ZProductScreen);


    return ClientScreen;
});