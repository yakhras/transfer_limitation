/** @odoo-module **/

import {component} from "@odoo/owl";
import {Navbar} from "./navbar";

export class WebClient extends component{
    static template ="webclient.Page";
    static component = {Navbar};
}