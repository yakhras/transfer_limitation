/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, useState } = owl

// Enhanced Chart Component working with the updated backend model
class BalanceChart extends Component {
    setup() {
        this.accountData = this.props.accountData || {}
        
        this.chartId = `chart_${Math.random().toString(36).substr(2, 9)}`
        this.chartInstance = null
        
        // Load chart after component is rendered
        setTimeout(() => this.loadChart(), 300)
    }

    async loadChart() {
        try {
            
            if (typeof Chart === 'undefined') {
                await this.loadChartJS()
            } else {
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
        console.log("=== CHART DEBUG ===")
        console.log("Account chart_data:", this.accountData.chart_data)
        console.log("Selected currencies from props:", this.props.selectedCurrencies)
        console.log("==================")
        const canvas = document.getElementById(this.chartId)
        if (!canvas) {
            return
        }
        
        if (typeof Chart === 'undefined') {
            this.showChartError()
            return
        }

        // Destroy existing chart if exists
        if (this.chartInstance) {
            this.chartInstance.destroy()
        }

        // Get chart data - now works with multiple currencies
        const chartData = this.getChartData()
        console.log("Processed chart data:", chartData)

        try {
            // Check if we have multiple currencies
            const isMultiCurrency = this.isMultipleCurrencies(chartData)
            console.log("Is multi currency:", isMultiCurrency)
            
            let datasets = []
            let labels = []

            if (isMultiCurrency) {
                console.log("Rendering multi-currency chart")
                // Multiple currencies - create dataset for each
                
                // Get labels from first available currency data
                if (chartData.TRY && Array.isArray(chartData.TRY) && chartData.TRY.length > 0) {
                    labels = chartData.TRY.map(item => item.label || '')
                } else if (chartData.USD && Array.isArray(chartData.USD) && chartData.USD.length > 0) {
                    labels = chartData.USD.map(item => item.label || '')
                } else if (chartData.EUR && Array.isArray(chartData.EUR) && chartData.EUR.length > 0) {
                    labels = chartData.EUR.map(item => item.label || '')
                }
                
                // Add TRY dataset if available and selected
                if (chartData.TRY && Array.isArray(chartData.TRY) && 
                    this.props.selectedCurrencies && this.props.selectedCurrencies.includes('TRY')) {
                    console.log("Adding TRY dataset with", chartData.TRY.length, "points")
                    datasets.push({
                        label: 'TRY Balance',
                        data: chartData.TRY.map(item => parseFloat(item.value) || 0),
                        borderColor: '#dc3545', // Red line for TRY
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        yAxisID: 'y-try'
                    })
                }

                // Add USD dataset if available and selected
                if (chartData.USD && Array.isArray(chartData.USD) && 
                    this.props.selectedCurrencies && this.props.selectedCurrencies.includes('USD')) {
                    console.log("Adding USD dataset with", chartData.USD.length, "points")
                    datasets.push({
                        label: 'USD Balance',
                        data: chartData.USD.map(item => parseFloat(item.value) || 0),
                        borderColor: '#28a745', // Green line for USD
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        yAxisID: 'y-usd'
                    })
                }

                // Add EUR dataset if available and selected
                if (chartData.EUR && Array.isArray(chartData.EUR) && 
                    this.props.selectedCurrencies && this.props.selectedCurrencies.includes('EUR')) {
                    console.log("Adding EUR dataset with", chartData.EUR.length, "points")
                    datasets.push({
                        label: 'EUR Balance',
                        data: chartData.EUR.map(item => parseFloat(item.value) || 0),
                        borderColor: '#6f42c1', // Purple line for EUR
                        backgroundColor: 'rgba(111, 66, 193, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.3,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        yAxisID: 'y-eur'
                    })
                }

            } else {
                console.log("Rendering single currency chart")
                // Single currency - existing logic
                datasets = [{
                    label: 'Balance',
                    data: chartData.values || [],
                    borderColor: this.getChartColor(this.accountData.balance_color, 'border'),
                    backgroundColor: this.getChartColor(this.accountData.balance_color, 'bg'),
                    borderWidth: 2,
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
                labels = chartData.labels || []
            }

            console.log("Final datasets count:", datasets.length)
            console.log("Final labels count:", labels.length)

            // Chart configuration
            const config = {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { 
                            display: isMultiCurrency,
                            position: 'top',
                            labels: {
                                usePointStyle: true,
                                pointStyle: 'line',
                                font: { size: 11 },
                                padding: 15
                            }
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                title: (context) => 'Date: ' + context[0].label,
                                label: (context) => {
                                    const value = context.parsed.y
                                    if (context.dataset.label === 'TRY Balance') {
                                        return `TRY: ₺${value.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                    } else if (context.dataset.label === 'USD Balance') {
                                        return `USD: $${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                    } else if (context.dataset.label === 'EUR Balance') {
                                        return `EUR: €${value.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                    } else {
                                        return `Balance: ₺${value.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                                    }
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            display: true,
                            grid: { display: false },
                            ticks: { 
                                font: { size: 10 },
                                maxTicksLimit: 6
                            }
                        },
                        y: { 
                            display: !isMultiCurrency,
                            beginAtZero: false,
                            grid: { display: true }
                        }
                    },
                    interaction: { 
                        intersect: false, 
                        mode: 'index' 
                    }
                }
            }

            // Add separate Y-axes for multi-currency
            if (isMultiCurrency) {
                // Add TRY Y-axis (left side)
                if (datasets.some(d => d.yAxisID === 'y-try')) {
                    config.options.scales['y-try'] = {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'TRY (₺)',
                            color: '#dc3545',
                            font: { size: 11, weight: 'bold' }
                        },
                        ticks: {
                            color: '#dc3545',
                            font: { size: 10 },
                            callback: function(value) {
                                return '₺' + value.toLocaleString('tr-TR', { maximumFractionDigits: 0 })
                            }
                        },
                        grid: { 
                            display: true,
                            color: 'rgba(220, 53, 69, 0.1)'
                        }
                    }
                }

                // Add USD Y-axis (right side)
                if (datasets.some(d => d.yAxisID === 'y-usd')) {
                    config.options.scales['y-usd'] = {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'USD ($)',
                            color: '#28a745',
                            font: { size: 11, weight: 'bold' }
                        },
                        ticks: {
                            color: '#28a745',
                            font: { size: 10 },
                            callback: function(value) {
                                return '$' + value.toLocaleString('en-US', { maximumFractionDigits: 0 })
                            }
                        },
                        grid: { 
                            display: false  // Hide grid for secondary axis
                        }
                    }
                }

                // Add EUR Y-axis (right side, offset)
                if (datasets.some(d => d.yAxisID === 'y-eur')) {
                    config.options.scales['y-eur'] = {
                        type: 'linear',
                        display: datasets.filter(d => d.yAxisID.startsWith('y-')).length <= 2, // Only show if 2 or fewer currencies
                        position: 'right',
                        title: {
                            display: true,
                            text: 'EUR (€)',
                            color: '#6f42c1',
                            font: { size: 11, weight: 'bold' }
                        },
                        ticks: {
                            color: '#6f42c1',
                            font: { size: 10 },
                            callback: function(value) {
                                return '€' + value.toLocaleString('de-DE', { maximumFractionDigits: 0 })
                            }
                        },
                        grid: { 
                            display: false
                        }
                    }
                }
            }

            console.log("Creating chart with config:", config)
            this.chartInstance = new Chart(canvas, config)
            
        } catch (error) {
            console.error('BalanceChart: Error creating chart:', error)
            this.showChartError()
        }
    }

    isMultipleCurrencies(chartData) {
        // Check if chartData is an object with currency keys (TRY, USD, EUR)
        const isMulti = chartData && typeof chartData === 'object' && 
            !Array.isArray(chartData) && 
            (chartData.TRY || chartData.USD || chartData.EUR) &&
            !chartData.values && !chartData.labels
        
        console.log("isMultipleCurrencies check:", {
            chartData: chartData,
            isObject: typeof chartData === 'object',
            isNotArray: !Array.isArray(chartData),
            hasCurrencyKeys: (chartData && (chartData.TRY || chartData.USD || chartData.EUR)),
            hasNoFallbackKeys: chartData && !chartData.values && !chartData.labels,
            result: isMulti
        })
        
        return isMulti
    }

    getChartData() {
        console.log("getChartData called with accountData:", this.accountData)
        
        // Use chart_data from the updated backend if available
        if (this.accountData.chart_data) {
            console.log("Found chart_data:", this.accountData.chart_data)
            
            // Check if it's multi-currency data (object with currency keys)
            if (typeof this.accountData.chart_data === 'object' && 
                !Array.isArray(this.accountData.chart_data) &&
                (this.accountData.chart_data.TRY || this.accountData.chart_data.USD || this.accountData.chart_data.EUR)) {
                
                console.log("Detected multi-currency chart data")
                // Multi-currency chart data - return as-is
                return this.accountData.chart_data
            } 
            // Single currency chart data (array format)
            else if (Array.isArray(this.accountData.chart_data) && this.accountData.chart_data.length > 0) {
                console.log("Detected single currency array chart data")
                return {
                    labels: this.accountData.chart_data.map(item => item.label || ''),
                    values: this.accountData.chart_data.map(item => parseFloat(item.value) || 0)
                }
            }
        }

        // Use chartData prop if available
        if (this.props.chartData && Array.isArray(this.props.chartData) && this.props.chartData.length > 0) {
            console.log("Using props chartData")
            return {
                labels: this.props.chartData.map(item => item.label || ''),
                values: this.props.chartData.map(item => parseFloat(item.value) || 0)
            }
        }

        console.log("Generating fallback chart data")
        // Fallback: Generate sample trend data
        return this.generateFallbackChartData()
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

    generateFallbackChartData() {
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
            selectedCurrencies: ['TRY'],
            availableCurrencies: [
                {code: 'TRY', name: 'TL', symbol: '₺', flag: '🇹🇷'},
                {code: 'USD', name: 'USD', symbol: '$', flag: '🇺🇸'},
                {code: 'EUR', name: 'Eur', symbol: '€', flag: '🇪🇺'},
            ],
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

    toggleCurrency(currencyCode) {
        const index = this.state.selectedCurrencies.indexOf(currencyCode);
        if (index > -1) {
            this.state.selectedCurrencies.splice(index, 1);
        } else {
            this.state.selectedCurrencies.push(currencyCode);
        }
        this.loadDashboardData(); // Reload with new filter
    }

    getCurrencyOptionClass(code) {
        return this.state.selectedCurrencies.includes(code) ? 'selected' : '';
    }

    isSelectedCurrency(code) {
        return this.state.selectedCurrencies.includes(code);
    }

    getSelectedCurrencyTags() {
        return this.state.availableCurrencies.filter(c => 
            this.state.selectedCurrencies.includes(c.code)
        );
    }

    getCurrencyFlag(code) {
        const currency = this.state.availableCurrencies.find(c => c.code === code);
        return currency ? currency.flag : '';
    }

    // ADDED: Helper function to format dates without timezone issues
    formatLocalDate(date) {
        const year = date.getFullYear()
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
    }

    async loadDashboardData() {
        
    
        this.state.loading = true
        this.state.error = null

        try {
            // Get date range context
            const dateRange = this.getDateRange()

            console.log("=== BACKEND CALL DEBUG ===")
            console.log("Sending to backend:", {
                period_type: this.state.period,
                date_from: dateRange.date_from,
                date_to: dateRange.date_to,
                currencies: this.state.selectedCurrencies
            })
            console.log("=========================")
            
            // UPDATED: Call the backend method with currency filtering
            const accountsData = await this.orm.call(
                'cash.flow.dashboard',
                'get_filtered_dashboard_data',
                [],
                {
                    period_type: this.state.period,
                    date_from: dateRange.date_from,
                    date_to: dateRange.date_to,
                    currencies: this.state.selectedCurrencies  // ADDED: Pass selected currencies
                }
            )

            
            // Process the response with null checks
            if (Array.isArray(accountsData)) {
                this.state.accounts = accountsData.map(account => ({
                    id: account.id || 0,
                    account_codes: account.account_codes || '',
                    account_names: account.account_names || '',
                    display_name: account.display_name || 'Unknown',
                    current_balance: parseFloat(account.current_balance) || 0,
                    current_balance_usd: parseFloat(account.current_balance_usd) || 0,
                    // ADD: Use USD balance and display when USD is selected
                    display_balance: this.getDisplayBalance(account),
                    balance_display: this.getFormattedBalance(account),
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
            // Console log USD total balance if USD is selected
            if (this.state.selectedCurrencies.includes('USD')) {
                const totalUsdBalance = this.state.accounts.reduce((sum, account) => {
                    return sum + (parseFloat(account.current_balance_usd) || 0)
                }, 0)
                console.log(`=== USD TOTAL BALANCE ===`)
                console.log(`Total Balance in USD: $${totalUsdBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`)
                console.log(`Number of accounts: ${this.state.accounts.length}`)
                console.log(`=========================`)
            }
            console.log("Selected currencies:", this.state.selectedCurrencies)
            console.log("Accounts data:", accountsData)
            // ADD BACKEND DEBUG:
            if (accountsData && accountsData.length > 0) {
                const firstAccount = accountsData[0]
                console.log("=== BACKEND DEBUG ===")
                console.log("Backend received currencies:", firstAccount.debug_currencies)
                console.log("Currency count:", firstAccount.debug_currency_count)
                console.log("Chart data type:", firstAccount.debug_chart_type)
                console.log("Chart data keys:", firstAccount.debug_chart_keys)
                
                // ADD CHART METHOD DEBUG:
                if (firstAccount.chart_data && firstAccount.chart_data.debug) {
                    console.log("=== CHART METHOD DEBUG ===")
                    console.log("Method debug info:", firstAccount.chart_data.debug)
                    console.log("========================")
                }
                
                console.log("===================")
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

    getDisplayBalance(account) {
        if (this.state.selectedCurrencies.includes('USD')) {
            return parseFloat(account.current_balance_usd) || 0
        }
        return parseFloat(account.current_balance) || 0
    }

    getFormattedBalance(account) {
        if (this.state.selectedCurrencies.includes('USD')) {
            const usdBalance = parseFloat(account.current_balance_usd) || 0
            return `$${usdBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
        }
        return account.balance_display || '₺0'
    }

    getFormattedTotalBalance() {
        if (this.state.selectedCurrencies.includes('USD')) {
            return `$${this.state.totalBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
        }
        return this.formatBalance(this.state.totalBalance)
    }

    getDateRange() {
        const today = new Date()
        const period = this.state.period
        
        
        if (period === 'all') {
            return { date_from: null, date_to: null }
        }
        
        if (period === 'custom') {
            const result = {
                date_from: this.state.customDateFrom,
                date_to: this.state.customDateTo
            }
            return result
        }

        // FIXED: Use formatLocalDate instead of toISOString() to avoid timezone issues
        let date_from, date_to = this.formatLocalDate(today)
        
        switch(period) {
            case 'this_week':
                const startOfWeek = new Date(today)
                startOfWeek.setDate(today.getDate() - today.getDay() + 1)
                date_from = this.formatLocalDate(startOfWeek)
                break
                
            case 'this_month':
                const monthStart = new Date(today.getFullYear(), today.getMonth(), 1)
                date_from = this.formatLocalDate(monthStart)
                break
                
            case 'last_month':
                const lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1)
                const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0)
                date_from = this.formatLocalDate(lastMonthStart)
                date_to = this.formatLocalDate(lastMonthEnd)
                break
                
            case 'this_quarter':
                const quarterStart = new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3, 1)
                date_from = this.formatLocalDate(quarterStart)
                break
                
            case 'last_quarter':
                const lastQuarterStart = new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3 - 3, 1)
                const lastQuarterEnd = new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3, 0)
                date_from = this.formatLocalDate(lastQuarterStart)
                date_to = this.formatLocalDate(lastQuarterEnd)
                break
                
            case 'this_year':
                const yearStart = new Date(today.getFullYear(), 0, 1)
                date_from = this.formatLocalDate(yearStart)
                break
                
            case 'last_year':
                const lastYearStart = new Date(today.getFullYear() - 1, 0, 1)
                const lastYearEnd = new Date(today.getFullYear() - 1, 11, 31)
                date_from = this.formatLocalDate(lastYearStart)
                date_to = this.formatLocalDate(lastYearEnd)
                break
                
            default:
                date_from = null
                date_to = null
        }
        
        const result = { date_from, date_to }
        
        return result
    }

    updateSummaryStats() {
        let totalBalance = 0
        let positiveAccounts = 0
        let negativeAccounts = 0
        
        this.state.accounts.forEach(account => {
            const balance = this.getDisplayBalance(account)  // Use this method
            totalBalance += balance
            if (balance > 0) positiveAccounts++
            else if (balance < 0) negativeAccounts++
        })
        
        this.state.totalBalance = totalBalance
        this.state.positiveAccounts = positiveAccounts
        this.state.negativeAccounts = negativeAccounts
    }

    async onPeriodChange(event) {
        setTimeout(() => {
        }, 10)
        
        // Manual state update to test
        const selectedValue = event.target.value
        this.state.period = selectedValue
        
        
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
        } else {
        }
        
    }

    async refreshData() {
        await this.loadDashboardData()
    }

    clearError() {
        this.state.error = null
    }

    // viewAccountDetails(accountId) {
    //     const dateRange = this.getDateRange()
        
    //     this.actionService.doAction({
    //         type: "ir.actions.act_window",
    //         name: "Cash Flow Details",
    //         res_model: "cash.flow.dashboard",
    //         res_id: accountId,
    //         views: [[false, "form"]],
    //         target: "current",
    //         context: {
    //             date_from: dateRange.date_from,
    //             date_to: dateRange.date_to,
    //             period_type: this.state.period
    //         }
    //     })
    // }
// [["account_id.code","in",["120001","120002"]]]
    viewAccountDetails(accountId) {
        const dateRange = this.getDateRange()
        const account_codes = accountId.split(', ')
        const domain = [
            ["account_id.code","in", account_codes],
            ["move_id.state", "=", "posted"],
            ["company_id", "=", this.env.company.id]
        ]
        console.log(domain)
        
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Cash Flow Details",
            res_model: "account.move.line",
            domain: domain,
            views: [[false, "list"],[false, "form"]],
            view_mode: "list",
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

CashFlowDashboard.template = "cash_flow_t.CashFlowDashboard"
CashFlowDashboard.components = { BalanceChart }

registry.category("actions").add("cash_flow_t.dashboard", CashFlowDashboard)