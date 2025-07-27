/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
const { Component, useState } = owl

// Simple Chart Component
class BalanceChart extends Component {
    setup() {
        this.chartId = `chart_${Math.random().toString(36).substr(2, 9)}`
        setTimeout(() => this.renderChart(), 200)
    }

    renderChart() {
        const canvas = document.getElementById(this.chartId)
        if (!canvas || typeof Chart === 'undefined') return

        // Simple sample chart for now
        const data = [
            this.props.currentBalance * 0.8,
            this.props.currentBalance * 0.9,
            this.props.currentBalance * 0.95,
            this.props.currentBalance
        ]

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: ['Period 1', 'Period 2', 'Period 3', 'Current'],
                datasets: [{
                    data: data,
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

// Data Manager Class for Frontend Model
class CashFlowDataManager {
    constructor() {
        this.accounts = new Map()           // account configs
        this.transactions = new Map()       // all transactions
        this.accountTransactions = new Map() // account_id → transaction_ids
        this.lastUpdate = null
    }

    clear() {
        this.accounts.clear()
        this.transactions.clear()
        this.accountTransactions.clear()
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

    calculateAccountBalance(accountConfig) {
        let totalBalance = 0.0
        const debugInfo = {
            accountConfig: accountConfig.displayName,
            accountIds: Array.from(accountConfig.accountIds),
            transactionDetails: []
        }

        for (const accountId of accountConfig.accountIds) {
            const transactionIds = this.accountTransactions.get(accountId) || new Set()
            let accountTotal = 0.0
            
            for (const transactionId of transactionIds) {
                const transaction = this.transactions.get(transactionId)
                if (transaction) {
                    accountTotal += transaction.balance
                    debugInfo.transactionDetails.push({
                        id: transaction.id,
                        accountId: transaction.accountId,
                        date: transaction.date.toISOString().split('T')[0],
                        debit: transaction.debit,
                        credit: transaction.credit,
                        balance: transaction.balance
                    })
                }
            }
            
            totalBalance += accountTotal
            console.log(`Account ${accountId} balance: ${accountTotal} (${transactionIds.size} transactions)`)
        }

        console.log(`Total balance for ${accountConfig.displayName}: ${totalBalance}`)
        console.log('Debug info:', debugInfo)
        
        // Store debug info for inspection
        if (window.cashFlowDebug) {
            window.cashFlowDebug.lastCalculation = debugInfo
        }

        return totalBalance
    }

    getAccountsWithBalances() {
        const result = []

        for (const accountConfig of this.accounts.values()) {
            if (!accountConfig.active) continue

            const balance = this.calculateAccountBalance(accountConfig)
            const balanceColor = balance > 0 ? 'green' : (balance < 0 ? 'red' : 'blue')

            result.push({
                id: accountConfig.id,
                display_name: accountConfig.displayName,
                current_balance: balance,
                balance_display: this.formatBalance(balance),
                balance_color: balanceColor,
                sequence: accountConfig.sequence
            })
        }

        // Sort by sequence
        result.sort((a, b) => a.sequence - b.sequence)
        return result
    }

    formatBalance(balance) {
        return `₺${balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
}

export class CashFlowDashboard extends Component {
    setup() {
        console.log('Basic Cash Flow Dashboard loading...')
        
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
            dataLoaded: false
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
            const response = await this.orm.call(
                'cash.flow.dashboard',
                'get_complete_dashboard_data',
                []
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

    processCompleteData(response) {
        const accountsCount = response.data.accounts.length
        const transactionsCount = response.data.transactions.length
        
        console.log(`Processing ${accountsCount} accounts, ${transactionsCount} transactions`)
        
        // Clear existing data
        this.dataManager.clear()
        
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

    async refreshData() {
        console.log('Refreshing dashboard data...')
        await this.loadCompleteData()
    }

    clearError() {
        this.state.error = null
    }

    viewAccountDetails(accountId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Cash Flow Details",
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