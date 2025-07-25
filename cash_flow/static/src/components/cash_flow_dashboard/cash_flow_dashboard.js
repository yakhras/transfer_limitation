/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, useState } = owl

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

        // Debounce timeout for custom dates
        this.customDateTimeout = null

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
            
            // Use enhanced OWL method with detailed logging
            const accounts = await this.orm.call(
                "cash.flow.dashboard", 
                "get_owl_dashboard_data",
                [],
                {
                    period_type: this.state.period,
                    date_from: dateRange.date_from,
                    date_to: dateRange.date_to
                }
            )
            
            this.state.accounts = accounts || []
            this.state.lastUpdated = new Date().toLocaleTimeString()
            
            console.log('Successfully loaded accounts:', accounts)
            
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
        console.log('Handling error:', error)
        
        // Determine error type and handle accordingly
        if (error.message && error.message.includes('network')) {
            // Network error - toast notification
            this.notification.add("Connection issue. Please check your internet.", {
                type: "warning",
                title: "Connection Error"
            })
        } else if (error.message && (error.message.includes('permission') || error.message.includes('AccessError'))) {
            // Permission error - inline message
            this.state.error = {
                message: "You don't have permission to view this data.",
                showRetry: false
            }
        } else {
            // API/Other errors - inline with retry
            this.state.error = {
                message: error.message || "Failed to load cash flow data. Please try again.",
                showRetry: true
            }
        }
    }

    /**
     * Retry loading data after error
     */
    async retryLoadData() {
        console.log('Retrying data load...')
        this.state.error = null
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
        
        // Clear any previous errors
        this.state.error = null
        
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
        if (this.customDateTimeout) {
            clearTimeout(this.customDateTimeout)
        }
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
// Using existing BalanceChart component from balance_chart.xml
// No need to define components if BalanceChart is globally available

registry.category("actions").add("cash_flow.dashboard", CashFlowDashboard)