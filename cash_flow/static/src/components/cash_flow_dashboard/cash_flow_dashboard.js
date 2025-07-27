/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, useState } = owl

// Enhanced Chart Component with proper Chart.js loading
class BalanceChart extends Component {
    setup() {
        console.log('BalanceChart component created for:', this.props.accountData?.display_name)
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

        console.log('BalanceChart: Rendering chart for:', this.props.accountData?.display_name)

        // Get historical data or create sample data
        const chartData = this.getChartData()

        try {
            this.chartInstance = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: chartData.labels,
                    datasets: [{
                        label: 'Balance',
                        data: chartData.values,
                        borderColor: this.getChartColor(this.props.accountData?.balance_color, 'border'),
                        backgroundColor: this.getChartColor(this.props.accountData?.balance_color, 'bg'),
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
        // Get historical data from props if available
        if (this.props.historicalData && this.props.historicalData.length > 0) {
            return {
                labels: this.props.historicalData.map(item => item.date),
                values: this.props.historicalData.map(item => item.balance)
            }
        }

        // Generate sample trend data based on current balance
        const currentBalance = this.props.accountData?.current_balance || 0
        const periods = this.props.periods || 7
        
        const labels = []
        const values = []
        
        // Generate last N periods (days/weeks based on filter)
        const today = new Date()
        for (let i = periods - 1; i >= 0; i--) {
            const date = new Date(today)
            date.setDate(today.getDate() - i)
            labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))
            
            // Generate realistic trend (variation ±15% from current balance)
            const variation = (Math.random() - 0.5) * 0.3 // ±15%
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

// Enhanced Data Manager with Date Filtering
class CashFlowDataManager {
    constructor() {
        this.accounts = new Map()           // account configs
        this.transactions = new Map()       // all transactions
        this.accountTransactions = new Map() // account_id → transaction_ids
        this.lastUpdate = null
        this.dateFilter = null // { date_from, date_to }
    }

    clear() {
        this.accounts.clear()
        this.transactions.clear()
        this.accountTransactions.clear()
    }

    setDateFilter(dateFrom, dateTo) {
        this.dateFilter = { date_from: dateFrom, date_to: dateTo }
        console.log('Date filter set:', this.dateFilter)
    }

    clearDateFilter() {
        this.dateFilter = null
        console.log('Date filter cleared')
    }

    setAccount(accountData) {
        this.accounts.set(accountData.id, {
            id: accountData.id,
            displayName: accountData.display_name,
            accountIds: new Set(accountData.account_ids),
            sequence: accountData.sequence,
            active: accountData.active
        })
    }

    setTransaction(transactionData) {
        const transaction = {
            id: transactionData.id,
            accountId: transactionData.account_id,
            date: new Date(transactionData.date),
            debit: transactionData.debit,
            credit: transactionData.credit,
            balance: transactionData.debit - transactionData.credit
        }

        this.transactions.set(transaction.id, transaction)

        // Index by account
        if (!this.accountTransactions.has(transaction.accountId)) {
            this.accountTransactions.set(transaction.accountId, new Set())
        }
        this.accountTransactions.get(transaction.accountId).add(transaction.id)
    }

    isTransactionInDateRange(transaction) {
        if (!this.dateFilter) return true
        
        const transactionDate = transaction.date
        const fromDate = this.dateFilter.date_from ? new Date(this.dateFilter.date_from) : null
        const toDate = this.dateFilter.date_to ? new Date(this.dateFilter.date_to) : null
        
        if (fromDate && transactionDate < fromDate) return false
        if (toDate && transactionDate > toDate) return false
        
        return true
    }

    calculateAccountBalance(accountConfig) {
        let totalBalance = 0.0
        let filteredTransactions = 0
        
        for (const accountId of accountConfig.accountIds) {
            const transactionIds = this.accountTransactions.get(accountId) || new Set()
            
            for (const transactionId of transactionIds) {
                const transaction = this.transactions.get(transactionId)
                if (transaction && this.isTransactionInDateRange(transaction)) {
                    totalBalance += transaction.balance
                    filteredTransactions++
                }
            }
        }

        console.log(`Balance for ${accountConfig.displayName}: ${totalBalance} (${filteredTransactions} transactions in date range)`)
        return totalBalance
    }

    getHistoricalData(accountConfig, periods = 7) {
        if (!this.dateFilter) return []
        
        // Generate daily balances for the date range
        const fromDate = this.dateFilter.date_from ? new Date(this.dateFilter.date_from) : new Date(Date.now() - periods * 24 * 60 * 60 * 1000)
        const toDate = this.dateFilter.date_to ? new Date(this.dateFilter.date_to) : new Date()
        
        const historicalData = []
        const currentDate = new Date(fromDate)
        
        while (currentDate <= toDate) {
            // Calculate balance up to this date
            const tempFilter = this.dateFilter
            this.dateFilter = { date_from: null, date_to: currentDate.toISOString().split('T')[0] }
            
            const balance = this.calculateAccountBalance(accountConfig)
            
            historicalData.push({
                date: currentDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
                balance: balance
            })
            
            currentDate.setDate(currentDate.getDate() + 1)
        }
        
        // Restore original filter
        this.dateFilter = tempFilter
        
        return historicalData
    }

    getAccountsWithBalances() {
        const result = []

        for (const accountConfig of this.accounts.values()) {
            if (!accountConfig.active) continue

            const balance = this.calculateAccountBalance(accountConfig)
            const balanceColor = balance > 0 ? 'green' : (balance < 0 ? 'red' : 'blue')
            const historicalData = this.getHistoricalData(accountConfig)

            result.push({
                id: accountConfig.id,
                display_name: accountConfig.displayName,
                current_balance: balance,
                balance_display: this.formatBalance(balance),
                balance_color: balanceColor,
                sequence: accountConfig.sequence,
                historical_data: historicalData
            })
        }

        result.sort((a, b) => a.sequence - b.sequence)
        return result
    }

    formatBalance(balance) {
        return `₺${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
}

export class CashFlowDashboard extends Component {
    setup() {
        console.log('Enhanced Cash Flow Dashboard loading...')
        
        // Data Manager (Frontend Model)
        this.dataManager = new CashFlowDataManager()
        
        // Make dataManager globally accessible for debugging
        window.cashFlowDebug = {
            dataManager: this.dataManager,
            component: this
        }
        
        // Reactive State
        this.state = useState({
            accounts: [],
            loading: false,
            error: null,
            lastUpdated: null,
            dataLoaded: false,
            // Date filtering state
            dateFilter: 'all', // 'all', '7d', '30d', '90d', 'custom'
            customDateFrom: '',
            customDateTo: '',
            showCustomDateInputs: false
        })
        
        // Services
        this.orm = useService("orm")
        this.actionService = useService("action")
        this.notification = useService("notification")

        // Load initial data
        this.loadCompleteData()
    }

    async loadCompleteData() {
        console.log('Loading complete dashboard data...')
        this.state.loading = true
        this.state.error = null

        try {
            // Apply date filter to data loading
            const context = this.getDateFilterContext()
            
            const response = await this.orm.call(
                'cash.flow.dashboard',
                'get_complete_dashboard_data',
                [],
                { context }
            )

            console.log('Received data:', response)
            
            if (response.success) {
                this.processCompleteData(response)
                
                this.state.lastUpdated = new Date().toLocaleTimeString()
                this.state.dataLoaded = true
                
                this.notification.add(response.meta.message || "Dashboard data loaded successfully", {
                    type: "success",
                    title: "Data Loaded"
                })
            } else {
                throw new Error(response.error?.message || "Unknown error occurred")
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

    getDateFilterContext() {
        const context = {}
        
        if (this.state.dateFilter === 'custom') {
            if (this.state.customDateFrom) context.date_from = this.state.customDateFrom
            if (this.state.customDateTo) context.date_to = this.state.customDateTo
        } else if (this.state.dateFilter !== 'all') {
            const days = parseInt(this.state.dateFilter.replace('d', ''))
            const today = new Date()
            const fromDate = new Date(today.getTime() - (days * 24 * 60 * 60 * 1000))
            
            context.date_from = fromDate.toISOString().split('T')[0]
            context.date_to = today.toISOString().split('T')[0]
        }
        
        return context
    }

    processCompleteData(response) {
        const accountsCount = response.data.accounts.length
        const transactionsCount = response.data.transactions.length
        
        console.log(`Processing ${accountsCount} accounts, ${transactionsCount} transactions`)
        
        // Clear existing data
        this.dataManager.clear()
        
        // Set date filter in data manager
        const context = this.getDateFilterContext()
        if (context.date_from || context.date_to) {
            this.dataManager.setDateFilter(context.date_from, context.date_to)
        }
        
        // Load accounts
        response.data.accounts.forEach(account => {
            this.dataManager.setAccount(account)
        })
        
        // Load transactions
        response.data.transactions.forEach(transaction => {
            this.dataManager.setTransaction(transaction)
        })
        
        // Update reactive state
        this.updateAccountsDisplay()
        
        console.log(`Data processing complete. Frontend model now contains:`)
        console.log(`- ${this.dataManager.accounts.size} account configs`)
        console.log(`- ${this.dataManager.transactions.size} transactions`)
        console.log(`- Calculated balances for ${this.state.accounts.length} account groups`)
    }

    updateAccountsDisplay() {
        // Get accounts with calculated balances
        this.state.accounts = this.dataManager.getAccountsWithBalances()
        console.log('Updated accounts display:', this.state.accounts)
    }

    async onDateFilterChange() {
        console.log('Date filter changed to:', this.state.dateFilter)
        
        // Show/hide custom date inputs
        this.state.showCustomDateInputs = (this.state.dateFilter === 'custom')
        
        // If not custom, reload data immediately
        if (this.state.dateFilter !== 'custom') {
            await this.loadCompleteData()
        }
    }

    async onCustomDateChange() {
        console.log('Custom dates changed:', this.state.customDateFrom, this.state.customDateTo)
        
        // Only reload if both dates are set
        if (this.state.customDateFrom && this.state.customDateTo) {
            await this.loadCompleteData()
        }
    }

    async refreshData() {
        console.log('Refreshing dashboard data...')
        await this.loadCompleteData()
    }

    clearError() {
        this.state.error = null
    }

    viewAccountDetails(accountId) {
        const context = this.getDateFilterContext()
        
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Cash Flow Details",
            res_model: "cash.flow.dashboard",
            res_id: accountId,
            views: [[false, "form"]],
            target: "current",
            context: context
        })
    }

    getFilterDisplayName() {
        switch (this.state.dateFilter) {
            case 'all': return 'All Time'
            case '7d': return 'Last 7 Days'
            case '30d': return 'Last 30 Days'
            case '90d': return 'Last 90 Days'
            case 'custom': return 'Custom Range'
            default: return 'All Time'
        }
    }
}

CashFlowDashboard.template = "cash_flow.CashFlowDashboard"
CashFlowDashboard.components = { BalanceChart }

registry.category("actions").add("cash_flow.dashboard", CashFlowDashboard)