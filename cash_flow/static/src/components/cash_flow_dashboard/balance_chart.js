/** @odoo-module */

import { loadJS } from "@web/core/assets"
const { Component, useRef, onMounted } = owl

export class BalanceChart extends Component {
    setup(){
        this.chartRef = useRef("chart")
        
        onMounted(async ()=>{
            await this.loadChart()
        })
    }

    async loadChart(){
        try {
            // Load Chart.js library
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
            
            // Render the chart
            this.renderChart()
        } catch (error) {
            console.error("Error loading Chart.js:", error)
        }
    }

    renderChart(){
        const canvas = this.chartRef.el
        if (!canvas || typeof Chart === 'undefined') {
            console.log("Canvas or Chart.js not available")
            return
        }

        // Sample data - we'll make this dynamic later
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
                pointRadius: 3,
                pointHoverRadius: 6
            }]
        }

        new Chart(canvas, {
            type: 'line',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
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
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 10
                            }
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
    }
}

BalanceChart.template = "BalanceChart"