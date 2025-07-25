/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, useState } = owl

// Import existing BalanceChart component if available, otherwise define minimal one
class BalanceChart extends Component {
    setup() {
        this.chartId = `chart_${Math.random().toString(36).substr(2, 9)}`
        setTimeout(() => this.renderChart(), 200)
    }

    renderChart() {
        const canvas = document.getElementById(this.chartId)
        if (!canvas || typeof Chart === 'undefined') return

        const chartData = this.props.chartData && this.props.chartData.length > 0 
            ? this.props.chartData.map(item => item.value)
            : [this.props.currentBalance * 0.8, this.props.currentBalance * 0.9, this.props.currentBalance]

        const labels = this.props.chartData && this.props.chartData.length > 0
            ? this.props.chartData.map(item => item.label)
            : ['Period 1', 'Period 2', 'Current']

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    data: chartData,
                    borderColor: this.props.balanceColor === 'green' ? '#28a745' : 
                               this.props.balanceColor === 'red' ? '#dc3545' : '#17a2b8',
                    backgroundColor: this.props.balanceColor === 'green' ? 'rgba(40, 167, 69, 0.1)' : 
                                   this.props.balanceColor === 'red' ? 'rgba(220, 53, 69, 0.1)' : 'rgba(23, 162, 184, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: true, grid: { display: false } },
                    y: { display: false }
                }
            }
        })
    }
}

BalanceChart.template = "BalanceChart"

export class CashFlowDashboard extends Component {
    setup(){
        console.log('CashFlowDashboard component loading...')
        
        this.state = useState({
            accounts: [],
            period: 'all',
            customDateFrom: null,
            customDateTo: null,
            loading: false,
            error: null,
            lastUpdated: null
        })
        
        this.orm = useService("orm")
        this.actionService = useService("action")
        this.notification = useService("notification")

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

        this.customDateTimeout = null
        this.getAccounts()
    }

    getDateRange(){
        const today = new Date()
        const period = this.state.period
        
        if (period === 'all') {
            return { date_from: null, date_to: null }
        }
        
        if (period === 'custom') {
            return {
                date_from: this.state.customDateFrom,
                date_to: this.state.customDateTo
            }
        }

        let date_from, date_to = today.toISOString().split('T')[0]
        
        switch(period) {
            case 'this_week':
                const startOfWeek = new Date(today)
                startOfWeek.setDate(today.getDate() - today.getDay() + 1)
                date_from = startOfWeek.toISOString().split('T')[0]
                break
                
            case 'this_month':
                date_from = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0]
                break
                
            case 'last_month':
                const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
                date_from = lastMonth.toISOString().split('T')[0]
                date_to = new Date(today.getFullYear(), today.getMonth(), 0).toISOString().split('T')[0]
                break
                
            case 'this_quarter':
                const quarterStart = new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3, 1)
                date_from = quarterStart.toISOString().split('T')[0]
                break
                
            case 'last_quarter':
                const lastQuarterStart = new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3 - 3, 1)
                const lastQuarterEnd = new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3, 0)
                date_from = lastQuarterStart.toISOString().split('T')[0]
                date_to = lastQuarterEnd.toISOString().split('T')[0]
                break
                
            case 'this_year':
                date_from = new Date(today.getFullYear(), 0, 1).toISOString().split('T')[0]
                break
                
            case 'last_year':
                date_from = new Date(today.getFullYear() - 1, 0, 1).toISOString().split('T')[0]
                date_to = new Date(today.getFullYear() - 1, 11, 31).toISOString().split('T')[0]
                break
                
            default:
                date_from = null
                date_to = null
        }
        
        return { date_from, date_to }
    }

    async getAccounts(){
        try {
            this.state.error = null
            this.state.loading = true
            
            const dateRange = this.getDateRange()
            
            console.log('Loading accounts with period:', this.state.period, dateRange)
            
            // SIMPLE APPROACH: Pass dates as direct arguments, not context
            const accounts = await this.orm.call(
                "cash.flow.dashboard", 
                "get_filtered_dashboard_data",
                [dateRange.date_from, dateRange.date_to, this.state.period]
            )
            
            this.state.accounts = accounts || []
            this.state.lastUpdated = new Date().toLocaleTimeString()
            
            console.log('Successfully loaded accounts:', accounts)
            
        } catch (error) {
            console.error("Error loading cash flow data:", error)
            this.state.error = {
                message: error.message || "Failed to load cash flow data.",
                showRetry: true
            }
        } finally {
            this.state.loading = false
        }
    }

    async retryLoadData() {
        console.log('Retrying data load...')
        this.state.error = null
        await this.getAccounts()
    }

    clearError() {
        this.state.error = null
    }

    async onChangePeriod(){
        console.log('Period changed to:', this.state.period)
        
        if (this.state.period !== 'custom') {
            this.state.customDateFrom = null
            this.state.customDateTo = null
        }
        
        this.state.error = null
        await this.getAccounts()
    }

    onCustomDateChange(){
        console.log('Custom date changed:', this.state.customDateFrom, this.state.customDateTo)
        
        if (this.state.customDateFrom && this.state.customDateTo) {
            if (this.state.customDateFrom > this.state.customDateTo) {
                this.notification.add("Start date cannot be after end date.", {
                    type: "warning",
                    title: "Invalid Date Range"
                })
                return
            }
        }
        
        if (this.customDateTimeout) {
            clearTimeout(this.customDateTimeout)
        }
        this.customDateTimeout = setTimeout(() => {
            if (this.state.customDateFrom && this.state.customDateTo) {
                this.getAccounts()
            }
        }, 500)
    }

    getPeriodLabel() {
        const option = this.periodOptions.find(opt => opt.value === this.state.period)
        if (this.state.period === 'custom' && this.state.customDateFrom && this.state.customDateTo) {
            return `${this.state.customDateFrom} to ${this.state.customDateTo}`
        }
        return option ? option.label : 'All Time'
    }

    viewAccountDetails(accountId){
        const dateRange = this.getDateRange()
        
        // Create context with period information
        const context = {
            period_type: this.state.period,
            period_label: this.getPeriodLabel()
        }
        
        // Add date filtering to context
        if (dateRange.date_from) context.date_from = dateRange.date_from
        if (dateRange.date_to) context.date_to = dateRange.date_to

        // Open form view with enhanced context
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `Cash Flow Details - ${this.getPeriodLabel()}`,
            res_model: "cash.flow.dashboard",
            res_id: accountId,
            views: [[false, "form"]],
            target: "current",
            context: context,
            // ALSO pass as URL parameters for JavaScript access
            flags: {
                mode: 'readonly'
            },
            additional_context: {
                period_type: this.state.period,
                date_from: dateRange.date_from,
                date_to: dateRange.date_to,
                period_label: this.getPeriodLabel()
            }
        })
        
        // Alternative approach: Store in session storage for form view to access
        try {
            const periodData = {
                period_type: this.state.period,
                date_from: dateRange.date_from,
                date_to: dateRange.date_to,
                period_label: this.getPeriodLabel(),
                timestamp: Date.now()
            }
            sessionStorage.setItem('cash_flow_period_context', JSON.stringify(periodData))
        } catch (e) {
            console.log('Session storage not available:', e)
        }
    }

    isCustomDateRangeValid() {
        if (this.state.period !== 'custom') return true
        
        return this.state.customDateFrom && 
               this.state.customDateTo && 
               this.state.customDateFrom <= this.state.customDateTo
    }
}

CashFlowDashboard.template = "cash_flow.CashFlowDashboard"
CashFlowDashboard.components = { BalanceChart }

registry.category("actions").add("cash_flow.dashboard", CashFlowDashboard)