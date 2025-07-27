/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, useState } = owl

// Enhanced Chart Component working with the updated backend model
class BalanceChart extends Component {
    setup() {
        this.accountData = this.props.accountData || {}
        console.log('BalanceChart component created for:', this.accountData.display_name)
        
        this.chartId = `chart_${Math.random().toString(36).substr(2, 9)}`
        this.chartInstance = null
        
        // Load chart after component is rendered
        setTimeout(() => this.loadChart(), 300)
    }

    async loadChart() {
        try {
            console.log('BalanceChart: Loading Chart.js...')
            
            if (typeof Chart === 'undefined') {
                await this.loadChartJS()
            } else {
                console.log('BalanceChart: Chart.js already available')
                this.renderChart()
            }
            
        } catch (error) {
            console.error("Error loading Chart.js:", error)
            this.showChartError()
        }
    }

    async loadChartJS() {
        return new Promise((resolve, reject) => {
            // Check if Chart.js is already available
            if (typeof Chart !== 'undefined') {
                this.renderChart()
                resolve()
                return
            }

            // Check if script already exists
            const existingScript = document.querySelector('script[src*="chart.umd.min.js"]')
            if (existingScript) {
                console.log('BalanceChart: Chart.js script already exists, waiting...')
                setTimeout(() => {
                    if (typeof Chart !== 'undefined') {
                        this.renderChart()
                        resolve()
                    } else {
                        reject(new Error('Chart.js script exists but Chart object not available'))
                    }
                }, 800)
                return
            }

            // Load Chart.js script
            const script = document.createElement('script')
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js'
            script.onload = () => {
                console.log('BalanceChart: Chart.js loaded successfully')
                setTimeout(() => {
                    this.renderChart()
                    resolve()
                }, 200)
            }
            script.onerror = (error) => {
                console.error('BalanceChart: Failed to load Chart.js', error)
                this.showChartError()
                reject(error)
            }
            
            document.head.appendChild(script)
        })
    }

    renderChart() {
        const canvas = document.getElementById(this.chartId)
        if (!canvas) {
            console.log("BalanceChart: Canvas not found with ID:", this.chartId)
            return
        }
        
        if (typeof Chart === 'undefined') {
            console.log("BalanceChart: Chart.js not available")
            this.showChartError()
            return
        }

        // Destroy existing chart if exists
        if (this.chartInstance) {
            this.chartInstance.destroy()
        }

        console.log('BalanceChart: Rendering chart for:', this.accountData.display_name)

        // Get chart data - now works with updated backend model
        const chartData = this.getChartData()

        try {
            this.chartInstance = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        label: 'Balance',
                        data: chartData.values,
                        borderColor: this.getChartColor(this.accountData.balance_color, 'border'),
                        backgroundColor: this.getChartColor(this.accountData.balance_color, 'bg'),
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
                                title: (context) => 'Date: ' + context[0].label,
                                label: (context) => 'Balance: ₺' + context.parsed.y.toLocaleString()
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            grid: { display: false },
                            ticks: { 
                                font: { size: 10 },
                                maxTicksLimit: 5
                            }
                        },
                        y: { 
                            display: false, 
                            beginAtZero: false 
                        }
                    },
                    interaction: { 
                        intersect: false, 
                        mode: 'index' 
                    }
                }
            })
            
            console.log('BalanceChart: Chart rendered successfully')
        } catch (error) {
            console.error('BalanceChart: Error creating chart:', error)
            this.showChartError()
        }
    }

    getChartData() {
        // Use chart_data from the updated backend if available
        if (this.accountData.chart_data && Array.isArray(this.accountData.chart_data) && this.accountData.chart_data.length > 0) {
            return {
                labels: this.accountData.chart_data.map(item => item.label || ''),
                values: this.accountData.chart_data.map(item => parseFloat(item.value) || 0)
            }
        }

        // Use chartData prop if available
        if (this.props.chartData && Array.isArray(this.props.chartData) && this.props.chartData.length > 0) {
            return {
                labels: this.props.chartData.map(item => item.label || ''),
                values: this.props.chartData.map(item => parseFloat(item.value) || 0)
            }
        }

        // Fallback: Generate sample trend data based on current balance
        const currentBalance = parseFloat(this.accountData.current_balance) || 0
        const periods = 7
        
        const labels = []
        const values = []
        
        // Generate last 7 days with realistic variation
        const today = new Date()
        for (let i = periods - 1; i >= 0; i--) {
            const date = new Date(today)
            date.setDate(today.getDate() - i)
            labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))
            
            // Generate realistic trend (variation ±10% from current balance)
            const variation = (Math.random() - 0.5) * 0.2 // ±10%
            const trendBalance = currentBalance * (1 + variation * (i / periods))
            values.push(trendBalance)
        }
        
        // Ensure last value is current balance
        values[values.length - 1] = currentBalance
        
        return { labels, values }
    }

    getChartColor(balanceColor, type) {
        const colors = {
            green: { 
                border: '#28a745', 
                bg: 'rgba(40, 167, 69, 0.1)' 
            },
            red: { 
                border: '#dc3545', 
                bg: 'rgba(220, 53, 69, 0.1)' 
            },
            blue: { 
                border: '#17a2b8', 
                bg: 'rgba(23, 162, 184, 0.1)' 
            }
        }
        
        return (colors[balanceColor] || colors.blue)[type]
    }

    showChartError() {
        const canvas = document.getElementById(this.chartId)
        if (canvas) {
            const ctx = canvas.getContext('2d')
            ctx.fillStyle = '#f8f9fa'
            ctx.fillRect(0, 0, canvas.width, canvas.height)
            ctx.fillStyle = '#6c757d'
            ctx.font = '12px Arial'
            ctx.textAlign = 'center'
            ctx.fillText('Chart loading...', canvas.width / 2, canvas.height / 2)
        }
    }

    willUnmount() {
        if (this.chartInstance) {
            this.chartInstance.destroy()
        }
    }
}

BalanceChart.template = "BalanceChart"

export class CashFlowDashboard extends Component {
    setup() {
        console.log('Enhanced Cash Flow Dashboard loading with updated backend model...')
        
        // Reactive State
        this.state = useState({
            accounts: [],
            loading: false,
            error: null,
            lastUpdated: null,
            // Date filtering state
            period: 'all', // 'all', 'this_week', 'this_month', etc.
            customDateFrom: '',
            customDateTo: '',
            showCustomDateInputs: false,
            // Summary data
            totalBalance: 0,
            positiveAccounts: 0,
            negativeAccounts: 0
        })
        
        // Period options
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
        
        // Services
        this.orm = useService("orm")
        this.actionService = useService("action")
        this.notification = useService("notification")

        // Load initial data
        this.loadDashboardData()
    }

    async loadDashboardData() {
        console.log('Loading dashboard data with updated backend model...')
        this.state.loading = true
        this.state.error = null

        try {
            // Get date range context
            const dateRange = this.getDateRange()
            console.log('Date range:', dateRange)
            
            // Call the updated backend method
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

            console.log('Received accounts data:', accountsData)
            
            // Process the response with null checks
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

    getDateRange() {
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

    updateSummaryStats() {
        let totalBalance = 0
        let positiveAccounts = 0
        let negativeAccounts = 0
        
        try {
            this.state.accounts.forEach(account => {
                const balance = parseFloat(account.current_balance) || 0
                totalBalance += balance
                if (balance > 0) positiveAccounts++
                else if (balance < 0) negativeAccounts++
            })
        } catch (error) {
            console.warn('Error calculating summary stats:', error)
        }
        
        this.state.totalBalance = totalBalance
        this.state.positiveAccounts = positiveAccounts
        this.state.negativeAccounts = negativeAccounts
    }

    async onPeriodChange() {
        console.log('Period changed to:', this.state.period)
        
        // Show/hide custom date inputs
        this.state.showCustomDateInputs = (this.state.period === 'custom')
        
        // Reset custom dates when changing away from custom
        if (this.state.period !== 'custom') {
            this.state.customDateFrom = ''
            this.state.customDateTo = ''
        }
        
        // Reload data if not custom or if custom dates are set
        if (this.state.period !== 'custom') {
            await this.loadDashboardData()
        }
    }

    async onCustomDateChange() {
        console.log('Custom dates changed:', this.state.customDateFrom, this.state.customDateTo)
        
        // Validate date range
        if (this.state.customDateFrom && this.state.customDateTo) {
            if (this.state.customDateFrom > this.state.customDateTo) {
                this.notification.add("Start date cannot be after end date", {
                    type: "warning",
                    title: "Invalid Date Range"
                })
                return
            }
            
            // Reload data when both dates are set
            await this.loadDashboardData()
        }
    }

    async refreshData() {
        console.log('Refreshing dashboard data...')
        await this.loadDashboardData()
    }

    clearError() {
        this.state.error = null
    }

    viewAccountDetails(accountId) {
        const dateRange = this.getDateRange()
        
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Cash Flow Details",
            res_model: "cash.flow.dashboard",
            res_id: accountId,
            views: [[false, "form"]],
            target: "current",
            context: {
                date_from: dateRange.date_from,
                date_to: dateRange.date_to,
                period_type: this.state.period
            }
        })
    }

    getPeriodLabel() {
        const option = this.periodOptions.find(opt => opt.value === this.state.period)
        if (this.state.period === 'custom' && this.state.customDateFrom && this.state.customDateTo) {
            return `${this.state.customDateFrom} to ${this.state.customDateTo}`
        }
        return option ? option.label : 'All Time'
    }

    formatBalance(balance) {
        return `₺${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }

    getIndividualAccountCount(account) {
        try {
            if (account.individual_balances && typeof account.individual_balances === 'string') {
                const data = JSON.parse(account.individual_balances)
                return Array.isArray(data) ? data.length : 0
            }
            return 0
        } catch (error) {
            console.warn('Error parsing individual_balances:', error)
            return 0
        }
    }

    getIndividualAccountsData(account) {
        try {
            if (account.individual_balances && typeof account.individual_balances === 'string') {
                const data = JSON.parse(account.individual_balances)
                return Array.isArray(data) ? data : []
            }
            return []
        } catch (error) {
            console.warn('Error parsing individual_balances:', error)
            return []
        }
    }
}

CashFlowDashboard.template = "cash_flow.CashFlowDashboard"
CashFlowDashboard.components = { BalanceChart }

registry.category("actions").add("cash_flow.dashboard", CashFlowDashboard)