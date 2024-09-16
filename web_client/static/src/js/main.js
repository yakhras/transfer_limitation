/** @odoo-module **/

import {templates} from "@web/core/assets";
import {page} from "./web_client"; //the component we want to mount
import {mount, whenReady} from "@odoo/owl";

// Mount the Page component when the document.body is ready
whenReady(() => {
    mount(page, document.body, {templates, dev: true, name: "Web client App"});
}); 