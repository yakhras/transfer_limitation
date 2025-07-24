/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
import { BalanceChart } from "./balance_chart_component"
const { Component, useState } = owl

export class CashFlowDashboard extends Component {
    setup(){
        console.log('CashFlowDashboard component loading...')
        this.state = useState({
            accounts: [],
            period: 30,
        })
        this.orm = useService("orm")
        this.actionService = useService("action")
        this.getAccounts()
    }

    async getAccounts(){
        try {
            const dateRange = this.getDateRange()
            const accounts = await this.orm.call(
                "cash.flow.dashboard", 
                "search_read", 
                [[], ["account_code", "display_name", "current_balance", "balance_display", "balance_color"]],
                {
                    context: {
                        date_from: dateRange.date_from,
                        date_to: dateRange.date_to
                    }
                }
            )
            this.state.accounts = accounts
            console.log('Loaded accounts:', accounts)
        } catch (error) {
            console.error("Error loading cash flow data:", error)
            this.state.accounts = []
        }
    }

    getDateRange(){
        const today = new Date()
        const date_to = today.toISOString().split('T')[0]
        const pastDate = new Date()
        pastDate.setDate(today.getDate() - this.state.period)
        const date_from = pastDate.toISOString().split('T')[0]
        return { date_from, date_to }
    }

    async onChangePeriod(){
        console.log('Period changed to:', this.state.period)
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
CashFlowDashboard.components = { BalanceChart }
registry.category("actions").add("cash_flow_dashboard", CashFlowDashboard)