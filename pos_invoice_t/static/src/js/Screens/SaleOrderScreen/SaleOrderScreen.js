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
            let pos_config = this.env.pos.config;
            if (pos_config.invoice_type){
                console.log('Hi Yasser');
                let order = this.env.pos.get_order();
                let currentClient = order.get_client();
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
                                },
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
                super._onClickPay();
            }
            else{
                super._onClickPay();
            }
        }
    }
    

    Registries.Component.extend(ProductScreen, ZProductScreen);


    return ProductScreen;
});