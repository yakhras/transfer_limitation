/** @odoo-module **/

import { registry } from "@web/core/registry";
import { MailingListUpdaterMain } from "./mailing_list_updater_main";

/**
 * Client Action Registration for Mailing List Updater
 * 
 * Registers the main OWL component with Odoo's web client
 * so it can be called via ir.actions.client with tag 'mailing_list_updater'
 * 
 * File: static/src/js/client_action_registry.js
 */

const actionRegistry = registry.category("actions");

// Register the component with the exact tag name used in XML
actionRegistry.add("mailing_list_updater", MailingListUpdaterMain);

console.log("Mailing List Updater client action registered successfully");