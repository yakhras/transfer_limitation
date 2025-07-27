/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, useState } = owl

class BalanceChart extends Component {
    // ... Chart code remains unchanged
}

BalanceChart.template = "BalanceChart"

export class CashFlowDashboard extends Component {
    setup() {
        console.log('Enhanced Cash Flow Dashboard loading with updated backend model...')

        this.state = useState({
            accounts: [],
            loading: false,
            error: null,
            lastUpdated: null,
            period: 'all',
            customDateFrom: '',
            customDateTo: '',
            showCustomDateInputs: false,
            totalBalance: 0,
            positiveAccounts: 0,
            negativeAccounts: 0
        })

        this.periodOptions = [
            { value: 'all', label: 'All Time' },
            { value: 'this_week', label: 'This Week' },
            { value: 'this_month', label: 'This Month' },
            { value: 'last_month', label: 'Last Month' },
            { value: 'this_quarter', label: 'This Quarter' },
            { value: 'last_quarter', label: 'Last Quarter' },
            { value: 'this_year', label: 'This Year' },
            { value: 'last_year', label: 'Last Year' },
            { value: 'custom', label: 'Custom Range' }
        ]

        this.orm = useService("orm")
        this.actionService = useService("action")
        this.notification = useService("notification")

        this.loadDashboardData()
    }

    async loadDashboardData() {
        console.log('Loading dashboard data with updated backend model...')
        this.state.loading = true
        this.state.error = null

        try {
            const dateRange = this.getDateRange()
            console.log('Date range:', dateRange)

            const accountsData = await this.orm.call(
                'cash.flow.dashboard',
                'get_filtered_dashboard_data',
                [],
                {
                    period_type: this.state.period,
                    date_from: dateRange.date_from,
                    date_to: dateRange.date_to
                }
            )

            if (Array.isArray(accountsData)) {
                this.state.accounts = accountsData.map(account => ({
                    id: account.id || 0,
                    account_codes: account.account_codes || '',
                    account_names: account.account_names || '',
                    display_name: account.display_name || 'Unknown',
                    current_balance: parseFloat(account.current_balance) || 0,
                    balance_display: account.balance_display || '₺0',
                    balance_color: account.balance_color || 'blue',
                    chart_data: Array.isArray(account.chart_data) ? account.chart_data : [],
                    individual_balances: account.individual_balances || '[]',
                    period_info: account.period_info || {}
                }))
            } else {
                this.state.accounts = []
            }

            this.updateSummaryStats()
            this.state.lastUpdated = new Date().toLocaleTimeString()

            if (this.state.accounts.length > 0) {
                this.notification.add("Dashboard data loaded successfully", {
                    type: "success",
                    title: "Data Loaded"
                })
            }
        } catch (error) {
            console.error('Failed to load dashboard data:', error)
            this.state.error = {
                message: error.message || "Failed to load dashboard data",
                showRetry: true
            }
            this.notification.add("Failed to load dashboard data", {
                type: "danger",
                title: "Loading Error"
            })
        } finally {
            this.state.loading = false
        }
    }

    async onPeriodChange(event) {
        const newPeriod = event.target.value
        console.log('User selected period:', newPeriod)

        this.state.period = newPeriod
        this.state.showCustomDateInputs = (newPeriod === 'custom')

        if (newPeriod !== 'custom') {
            this.state.customDateFrom = ''
            this.state.customDateTo = ''
            await this.loadDashboardData()
        }
    }

    // ... Other unchanged methods like onCustomDateChange, getDateRange, etc.
}

CashFlowDashboard.template = "cash_flow.CashFlowDashboard"
CashFlowDashboard.components = { BalanceChart }
registry.category("actions").add("cash_flow.dashboard", CashFlowDashboard)
