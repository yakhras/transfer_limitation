/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, useState } = owl

// Inline Chart Component for Odoo 15 (OWL 1.x compatible)
class BalanceChart extends Component {
    setup(){
        console.log('BalanceChart component created for:', this.props.accountCode)
        
        // Generate unique ID for canvas
        this.chartId = `chart_${Math.random().toString(36).substr(2, 9)}`
        
        // Load chart after component is rendered
        setTimeout(() => {
            this.loadChart()
        }, 200)
    }

    async loadChart(){
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
        }
    }

    async loadChartJS() {
        return new Promise((resolve, reject) => {
            if (typeof Chart !== 'undefined') {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js';
            script.onload = () => {
                console.log('BalanceChart: Chart.js loaded successfully');
                setTimeout(() => {
                    this.renderChart();
                    resolve();
                }, 100);
            };
            script.onerror = (error) => {
                console.error('BalanceChart: Failed to load Chart.js', error);
                reject(error);
            };
            
            // Check if script already exists
            const existingScript = document.querySelector('script[src*="chart.umd.min.js"]');
            if (existingScript) {
                console.log('BalanceChart: Chart.js script already exists, waiting...');
                setTimeout(() => {
                    if (typeof Chart !== 'undefined') {
                        this.renderChart();
                        resolve();
                    } else {
                        reject(new Error('Chart.js script exists but Chart object not available'));
                    }
                }, 500);
                return;
            }
            
            document.head.appendChild(script);
        });
    }

    renderChart(){
        const canvas = document.getElementById(this.chartId)
        if (!canvas) {
            console.log("BalanceChart: Canvas not found with ID:", this.chartId)
            return
        }
        
        if (typeof Chart === 'undefined') {
            console.log("BalanceChart: Chart.js not available")
            return
        }

        console.log('BalanceChart: Rendering chart for account:', this.props.accountCode)

        // Use real chart data if provided, otherwise sample data
        let chartData, labels;
        
        if (this.props.chartData && this.props.chartData.length > 0) {
            // Real data from backend
            const data = this.props.chartData;
            labels = data.map(item => item.label);
            chartData = data.map(item => item.value);
        } else {
            // Fallback sample data
            labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
            chartData = [
                this.props.currentBalance * 0.8,
                this.props.currentBalance * 0.9,
                this.props.currentBalance * 0.95,
                this.props.currentBalance
            ];
        }

        const datasets = [{
            label: 'Balance',
            data: chartData,
            borderColor: this.props.balanceColor === 'green' ? '#28a745' : 
                       this.props.balanceColor === 'red' ? '#dc3545' : '#17a2b8',
            backgroundColor: this.props.balanceColor === 'green' ? 'rgba(40, 167, 69, 0.1)' : 
                           this.props.balanceColor === 'red' ? 'rgba(220, 53, 69, 0.1)' : 'rgba(23, 162, 184, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointRadius: 2,
            pointHoverRadius: 4
        }];

        try {
            new Chart(canvas, {
                type: 'line',
                data: { labels, datasets },
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
                                    return 'Period: ' + context[0].label
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
            
            console.log('BalanceChart: Chart rendered successfully')
        } catch (error) {
            console.error('BalanceChart: Error creating chart:', error)
        }
    }
}

BalanceChart.template = "BalanceChart"

export class CashFlowDashboard extends Component {
    setup(){
        console.log('CashFlowDashboard component loading with OWL 1.x...')
        
        // OWL 1.x compatible state management
        this.state = useState({
            accounts: [],
            period: 'all',
            customDateFrom: null,
            customDateTo: null,
            loading: false,
            error: null,
            lastUpdated: null
        })
        
        // Services for OWL 1.x
        this.orm = useService("orm")
        this.actionService = useService("action")
        this.notification = useService("notification")

        // Period options with detailed definitions
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

        // Load initial data
        this.getAccounts()
    }

    /**
     * Get date range based on selected period
     */
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
                // Monday to today
                const startOfWeek = new Date(today)
                startOfWeek.setDate(today.getDate() - today.getDay() + 1)
                date_from = startOfWeek.toISOString().split('T')[0]
                break
                
            case 'this_month':
                // First day of current month to today
                date_from = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0]
                break
                
            case 'last_month':
                // First to last day of previous month
                const lastMonth = new Date(today.getFullYear(), today.getMonth() - 1, 1)
                date_from = lastMonth.toISOString().split('T')[0]
                date_to = new Date(today.getFullYear(), today.getMonth(), 0).toISOString().split('T')[0]
                break
                
            case 'this_quarter':
                // First day of current quarter to today
                const quarterStart = new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3, 1)
                date_from = quarterStart.toISOString().split('T')[0]
                break
                
            case 'last_quarter':
                // Previous quarter
                const lastQuarterStart = new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3 - 3, 1)
                const lastQuarterEnd = new Date(today.getFullYear(), Math.floor(today.getMonth() / 3) * 3, 0)
                date_from = lastQuarterStart.toISOString().split('T')[0]
                date_to = lastQuarterEnd.toISOString().split('T')[0]
                break
                
            case 'this_year':
                // January 1st to today
                date_from = new Date(today.getFullYear(), 0, 1).toISOString().split('T')[0]
                break
                
            case 'last_year':
                // Previous year
                date_from = new Date(today.getFullYear() - 1, 0, 1).toISOString().split('T')[0]
                date_to = new Date(today.getFullYear() - 1, 11, 31).toISOString().split('T')[0]
                break
                
            default:
                date_from = null
                date_to = null
        }
        
        return { date_from, date_to }
    }

    /**
     * Load accounts data with current period filter
     */
    async getAccounts(){
        try {
            // Clear previous error
            this.state.error = null
            this.state.loading = true
            
            // Get date range based on selected period
            const dateRange = this.getDateRange()
            
            console.log('Loading accounts with period:', this.state.period, dateRange)
            
            // Fetch cash flow dashboard data with date context
            const accounts = await this.orm.call(
                "cash.flow.dashboard", 
                "get_owl_dashboard_data",
                [],
                {
                    period_type: this.state.period,
                    date_from: dateRange.date_from,
                    date_to: dateRange.date_to,
                    context: {
                        date_from: dateRange.date_from,
                        date_to: dateRange.date_to
                    }
                }
            )
            
            this.state.accounts = accounts || []
            this.state.lastUpdated = new Date().toLocaleTimeString()
            
            console.log('Loaded accounts:', accounts)
            
        } catch (error) {
            console.error("Error loading cash flow data:", error)
            this.handleError(error)
        } finally {
            this.state.loading = false
        }
    }

    /**
     * Handle different types of errors with appropriate UX
     */
    handleError(error) {
        // Determine error type and handle accordingly
        if (error.message && error.message.includes('network')) {
            // Network error - toast notification
            this.notification.add("Connection issue. Please check your internet.", {
                type: "warning",
                title: "Connection Error"
            })
        } else if (error.message && error.message.includes('permission')) {
            // Permission error - inline message
            this.state.error = {
                message: "You don't have permission to view this data.",
                showRetry: false
            }
        } else {
            // API/Other errors - inline with retry
            this.state.error = {
                message: error.message || "Failed to load cash flow data.",
                showRetry: true
            }
        }
    }

    /**
     * Retry loading data after error
     */
    async retryLoadData() {
        console.log('Retrying data load...')
        await this.getAccounts()
    }

    /**
     * Clear error state
     */
    clearError() {
        this.state.error = null
    }

    /**
     * Handle period change with smooth UX
     */
    async onChangePeriod(){
        console.log('Period changed to:', this.state.period)
        
        // Reset custom dates when changing away from custom
        if (this.state.period !== 'custom') {
            this.state.customDateFrom = null
            this.state.customDateTo = null
        }
        
        await this.getAccounts()
    }

    /**
     * Handle custom date changes with debouncing
     */
    onCustomDateChange(){
        console.log('Custom date changed:', this.state.customDateFrom, this.state.customDateTo)
        
        // Validate date range
        if (this.state.customDateFrom && this.state.customDateTo) {
            if (this.state.customDateFrom > this.state.customDateTo) {
                this.notification.add("Start date cannot be after end date.", {
                    type: "warning",
                    title: "Invalid Date Range"
                })
                return
            }
        }
        
        // Debounced update (wait for user to finish selecting dates)
        clearTimeout(this.customDateTimeout)
        this.customDateTimeout = setTimeout(() => {
            if (this.state.customDateFrom && this.state.customDateTo) {
                this.getAccounts()
            }
        }, 500)
    }

    /**
     * Get formatted period label for display
     */
    getPeriodLabel() {
        const option = this.periodOptions.find(opt => opt.value === this.state.period)
        if (this.state.period === 'custom' && this.state.customDateFrom && this.state.customDateTo) {
            return `${this.state.customDateFrom} to ${this.state.customDateTo}`
        }
        return option ? option.label : 'All Time'
    }

    /**
     * Navigate to account details (form view)
     */
    viewAccountDetails(accountId){
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Cash Flow Details",
            res_model: "cash.flow.dashboard",
            res_id: accountId,
            views: [[false, "form"]],
            target: "current",
            context: {
                date_from: this.getDateRange().date_from,
                date_to: this.getDateRange().date_to,
                period_type: this.state.period
            }
        })
    }

    /**
     * Check if custom date range is valid
     */
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