/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, onWillStart, useState } = owl

export class CashFlowDashboard extends Component {
    setup(){
        this.state = useState({
            accounts: [],
            period: 30,
        })
        this.orm = useService("orm")
        this.actionService = useService("action")

        onWillStart(async ()=>{
            await this.getAccounts()
        })
    }

    async getAccounts(){
        try {
            // Fetch cash flow dashboard data from your existing model
            const accounts = await this.orm.searchRead(
                "cash.flow.dashboard", 
                [], 
                ["account_code", "display_name", "current_balance", "balance_display", "balance_color"]
            )
            this.state.accounts = accounts
        } catch (error) {
            console.error("Error loading cash flow data:", error)
            this.state.accounts = []
        }
    }

    async onChangePeriod(){
        await this.getAccounts()
    }

    viewAccountDetails(accountId){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Account Details",
            res_model: "cash.flow.dashboard",
            res_id: accountId,
            views: [[false, "form"]],
            target: "current",
        })
    }
}

CashFlowDashboard.template = "cash_flow.CashFlowDashboard"

registry.category("actions").add("cash_flow.dashboard", CashFlowDashboard)