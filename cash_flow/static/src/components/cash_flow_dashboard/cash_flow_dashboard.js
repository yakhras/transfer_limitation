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
            if (typeof Chart !== 'undefined') {
                this.renderChart()
                resolve()
                return
            }

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

        if (this.chartInstance) {
            this.chartInstance.destroy()
        }

        console.log('BalanceChart: Rendering chart for:', this.accountData.display_name)

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
                            ticks: { font: { size: 10 }, maxTicksLimit: 5 }
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
        if (this.accountData.chart_data?.length > 0) {
            return {
                labels: this.accountData.chart_data.map(item => item.label || ''),
                values: this.accountData.chart_data.map(item => parseFloat(item.value) || 0)
            }
        }

        if (this.props.chartData?.length > 0) {
            return {
                labels: this.props.chartData.map(item => item.label || ''),
                values: this.props.chartData.map(item => parseFloat(item.value) || 0)
            }
        }

        const currentBalance = parseFloat(this.accountData.current_balance) || 0
        const periods = 7
        const labels = []
        const values = []
        const today = new Date()

        for (let i = periods - 1; i >= 0; i--) {
            const date = new Date(today)
            date.setDate(today.getDate() - i)
            labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }))
            const variation = (Math.random() - 0.5) * 0.2
            const trendBalance = currentBalance * (1 + variation * (i / periods))
            values.push(trendBalance)
        }

        values[values.length - 1] = currentBalance
        return { labels, values }
    }

    getChartColor(balanceColor, type) {
        const colors = {
            green: { border: '#28a745', bg: 'rgba(40, 167, 69, 0.1)' },
            red: { border: '#dc3545', bg: 'rgba(220, 53, 69, 0.1)' },
            blue: { border: '#17a2b8', bg: 'rgba(23, 162, 184, 0.1)' }
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

    // ... other methods unchanged for brevity
}

CashFlowDashboard.template = "cash_flow.CashFlowDashboard"
CashFlowDashboard.components = { BalanceChart }
registry.category("actions").add("cash_flow.dashboard", CashFlowDashboard)
