/** @ odoo-module */

import registry from "web.Registry";
import listview from "web.ListView";
import ListController from 'web.ListController';

class ResPartnerListController extends ListController{
    setup(){
        super.setup();
        console.log("this is res partner controller")
    }
}


const resPartnerListView = listview.extend({
    config: _.extend({}, listview.prototype.config, {
        Controller: ResPartnerListController,
    }),
});

registry.category("views").add("res_partner_list_view", resPartnerListView)