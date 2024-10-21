odoo.define('geolocation.getLocation', function (require) {
    'use strict';

    const { useState } = owl.hooks;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const session = require("web.session");
    const { useListener } = require('web.custom_hooks');
    const ProductScreen = require('point_of_sale.ProductScreen');
    

    const ZProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
            }
            async _onClickPay() {
                console.log('Hi Yaser');
                var self = this;
                let order = this.env.pos.get_order();
                let currentClient = order.get_client().id
                const { confirmed, payload: selectedOption } = await this.showPopup('SalesSelectionPopup',
                    {
                        title: this.env._t('Select an Invoice'),
                        list: [
                            {
                                id: 1,
                                label: this.env._t("Formal Invoice"),
                                item: true,
                                icon: 'fa fa-check-circle',
                            },
                        ],
                    });
                if (confirmed) {
                    if (selectedOption) {
                        console.log('True');
                        navigator.geolocation.getCurrentPosition(function(position){
                            console.log(position)
                        })
                    }
                    super._onClickPay();
                }
            }
        }
    

    Registries.Component.extend(ProductScreen, ZProductScreen);


    return ProductScreen;
});