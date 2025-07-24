/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, useState } = owl

class BalanceChart extends Component {
    setup(){
        console.log('BalanceChart component created for:', this.props.accountCode)
        this.chartId = `chart_${Math.random().toString(36).substr(2, 9)}`
        setTimeout(() => this.loadChart(), 200)
    }

    async loadChart(){
        try {
            if (typeof Chart === 'undefined') {
                await this.loadChartJS()
            } else {
                this.renderChart()
            }
        } catch (error) {
            console.error("Error loading Chart.js:", error)
        }
    }

    async loadChartJS() {
        return new Promise((resolve, reject) => {
            const existingScript = document.querySelector('script[src*="chart.umd.min.js"]')
            if (existingScript) {
                setTimeout(() => (typeof Chart !== 'undefined' ? resolve() : reject()), 500)
                return
            }
            const script = document.createElement('script')
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js'
            script.onload = () => setTimeout(() => { this.renderChart(); resolve() }, 100)
            script.onerror = reject
            document.head.appendChild(script)
        })
    }

    renderChart(){
        const canvas = document.getElementById(this.chartId)
        if (!canvas || typeof Chart === 'undefined') return

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                datasets: [{
                    label: 'Balance',
                    data: [
                        this.props.currentBalance * 0.8,
                        this.props.currentBalance * 0.9,
                        this.props.currentBalance * 0.85,
                        this.props.currentBalance * 1.1,
                        this.props.currentBalance * 1.05,
                        this.props.currentBalance * 0.95,
                        this.props.currentBalance
                    ],
                    borderColor: this.props.balanceColor === 'green' ? '#28a745' : 
                                 this.props.balanceColor === 'red' ? '#dc3545' : '#17a2b8',
                    backgroundColor: this.props.balanceColor === 'green' ? 'rgba(40, 167, 69, 0.1)' : 
                                     this.props.balanceColor === 'red' ? 'rgba(220, 53, 69, 0.1)' : 'rgba(23, 162, 184, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            title: function(context) {
                                return 'Month: ' + context[0].label
                            },
                            label: function(context) {
                                return 'Balance: ₺' + context.parsed.y.toLocaleString()
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: { display: false },
                        ticks: { font: { size: 10 } }
                    },
                    y: { display: false, beginAtZero: false }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        })
    }
}

BalanceChart.template = "BalanceChart"

export class CashFlowDashboard extends Component {
    setup(){
        this.state = useState({
            accounts: [],
            period: "30",
        })
        this.orm = useService("orm")
        this.actionService = useService("action")
        this.getAccounts()
    }

    async getAccounts(){
        try {
            const { date_from, date_to } = this.getDateRange()
            const context = {}
            if (date_from) context.date_from = date_from
            if (date_to) context.date_to = date_to

            const accounts = await this.orm.call(
                "cash.flow.dashboard",
                "search_read",
                [[], ["account_code", "display_name", "current_balance", "balance_display", "balance_color"]],
                { context }
            )
            this.state.accounts = accounts
            console.log("Loaded accounts:", accounts)
        } catch (error) {
            console.error("Error loading cash flow data:", error)
            this.state.accounts = []
        }
    }

    getDateRange(){
        if (this.state.period === "all") {
            return { date_from: null, date_to: null }
        }

        const today = new Date()
        const date_to = today.toISOString().split('T')[0]
        const pastDate = new Date()
        pastDate.setDate(today.getDate() - parseInt(this.state.period))
        const date_from = pastDate.toISOString().split('T')[0]
        return { date_from, date_to }
    }

    async onChangePeriod(){
        console.log("Period changed to:", this.state.period)
        await this.getAccounts()
    }

    viewAccountDetails(accountId){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Account Details",
            res_model: "cash.flow.dashboard",
            res_id: accountId,
            views: [[false, "form"]],
            target: "current"
        })
    }
}

CashFlowDashboard.template = "cash_flow.CashFlowDashboard"
CashFlowDashboard.components = { BalanceChart }
registry.category("actions").add("cash_flow.dashboard", CashFlowDashboard)