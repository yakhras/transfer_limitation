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
            // const { confirmed, payload: selectedOption } = await this.showPopup('SalesSelectionPopup',
            //     {
            //         title: this.env._t('Sale Order'),
            //         list: [
            //                 {
            //                     id:1, 
            //                     label: this.env._t("Confirm Sales Order"), 
            //                     item: true,
            //                     icon: 'fa fa-check-circle',
            //                 }, 
            //             {
            //                 id:2, 
            //                 label: this.env._t("Cancel Sales Order"), 
            //                 item: false,
            //                 icon: 'fa fa-close',
            //             }
            //         ],
            //     });
            // if (confirmed){
            //     if(selectedOption){
            //         if (clickedOrder.state !== 'sale') {
            //             var result = await this.rpc({
            //                 model: 'sale.order',
            //                 method: 'action_confirm',
            //                 args: [clickedOrder.id]
            //             });
            //         }
            //         else {
            //             await this.showPopup('ConfirmPopup', {
            //                 title: this.env._t('Already Confirmed'),
            //                 body: this.env._t(
            //                     'This Sales Order is Already in confirmed state!!!!'
            //                 ),
            //             });
            //         }
            //     }
            //     if (!selectedOption){
            //         if (clickedOrder.state !== 'cancel') {
            //             var result = await this.rpc({
            //                 model: 'sale.order',
            //                 method: 'action_cancel',
            //                 args: [clickedOrder.id]
            //             });
            //         }
            //         else {
            //             await this.showPopup('ConfirmPopup', {
            //                 title: this.env._t('Already Cancelled'),
            //                 body: this.env._t(
            //                     'This Sales Order is Already in Cancel State!!!!'
            //                 ),
            //             });
            //         }
            //     }
            // }
        }
    }
    

    Registries.Component.extend(ProductScreen, ZProductScreen);


    return ProductScreen;
});