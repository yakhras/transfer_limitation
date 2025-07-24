/** @odoo-module */

import { registry } from "@web/core/registry"
import { useService } from "@web/core/utils/hooks"
import { loadJS } from "@web/core/assets"
const { Component, useState, useRef } = owl

// Inline Chart Component for testing
class BalanceChart extends Component {
    setup(){
        this.chartRef = useRef("chart")
        console.log('BalanceChart component created for:', this.props.accountCode)
        
        // Load chart immediately after component setup
        setTimeout(() => {
            this.loadChart()
        }, 100)
    }

    async loadChart(){
        try {
            console.log('BalanceChart: Loading Chart.js...')
            
            // Load Chart.js library
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
            
            console.log('BalanceChart: Chart.js loaded, rendering chart...')
            
            // Small delay to ensure DOM is ready
            setTimeout(() => {
                this.renderChart()
            }, 50)
            
        } catch (error) {
            console.error("Error loading Chart.js:", error)
        }
    }

    renderChart(){
        const canvas = this.chartRef.el
        if (!canvas) {
            console.log("BalanceChart: Canvas not found")
            return
        }
        
        if (typeof Chart === 'undefined') {
            console.log("BalanceChart: Chart.js not available")
            return
        }

        console.log('BalanceChart: Rendering chart for account:', this.props.accountCode)

        // Sample data 
        const chartData = {
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
        }

        new Chart(canvas, {
            type: 'line',
            data: chartData,
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
        
        console.log('BalanceChart: Chart rendered successfully')
    }
}

BalanceChart.template = "BalanceChart"

export class CashFlowDashboard extends Component {
    setup(){
        console.log('OWL object keys:', Object.keys(owl))
        console.log('CashFlowDashboard component loading...')
        console.log('BalanceChart class defined:', BalanceChart)
        
        this.state = useState({
            accounts: [],
            period: 30,
        })
        this.orm = useService("orm")
        this.actionService = useService("action")

        // Load data immediately
        this.getAccounts()
    }

    async getAccounts(){
        try {
            // Get date range based on selected period
            const dateRange = this.getDateRange()
            
            // Fetch cash flow dashboard data with date context
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

CashFlowDashboard.template = "CashFlowDashboard"
CashFlowDashboard.components = { BalanceChart }

CashFlowDashboard.template = "CashFlowDashboard"

registry.category("actions").add("cash_flow.dashboard", CashFlowDashboard)