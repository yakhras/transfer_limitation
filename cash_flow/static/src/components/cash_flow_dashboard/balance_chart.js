// /** @odoo-module */

// import { loadJS } from "@web/core/assets"
// const { Component, useRef } = owl

// export class BalanceChart extends Component {
//     setup(){
//         this.chartRef = useRef("chart")
        
//         // Load chart immediately after component setup (Odoo 15 compatible)
//         setTimeout(() => {
//             this.loadChart()
//         }, 100)
//     }

//     async loadChart(){
//         try {
//             console.log('BalanceChart: Loading Chart.js...')
            
//             // Load Chart.js library
//             await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
            
//             console.log('BalanceChart: Chart.js loaded, rendering chart...')
            
//             // Small delay to ensure DOM is ready
//             setTimeout(() => {
//                 this.renderChart()
//             }, 50)
            
//         } catch (error) {
//             console.error("Error loading Chart.js:", error)
//         }
//     }

//     renderChart(){
//         const canvas = this.chartRef.el
//         if (!canvas) {
//             console.log("BalanceChart: Canvas not found")
//             return
//         }
        
//         if (typeof Chart === 'undefined') {
//             console.log("BalanceChart: Chart.js not available")
//             return
//         }

//         console.log('BalanceChart: Rendering chart for account:', this.props.accountCode)

//         // Sample data - we'll make this dynamic later
//         const chartData = {
//             labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
//             datasets: [{
//                 label: 'Balance',
//                 data: [
//                     this.props.currentBalance * 0.8,
//                     this.props.currentBalance * 0.9,
//                     this.props.currentBalance * 0.85,
//                     this.props.currentBalance * 1.1,
//                     this.props.currentBalance * 1.05,
//                     this.props.currentBalance * 0.95,
//                     this.props.currentBalance
//                 ],
//                 borderColor: this.props.balanceColor === 'green' ? '#28a745' : 
//                            this.props.balanceColor === 'red' ? '#dc3545' : '#17a2b8',
//                 backgroundColor: this.props.balanceColor === 'green' ? 'rgba(40, 167, 69, 0.1)' : 
//                                this.props.balanceColor === 'red' ? 'rgba(220, 53, 69, 0.1)' : 'rgba(23, 162, 184, 0.1)',
//                 borderWidth: 2,
//                 fill: true,
//                 tension: 0.3,
//                 pointRadius: 2,
//                 pointHoverRadius: 4
//             }]
//         }

//         new Chart(canvas, {
//             type: 'line',
//             data: chartData,
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 plugins: {
//                     legend: {
//                         display: false
//                     },
//                     tooltip: {
//                         mode: 'index',
//                         intersect: false,
//                         callbacks: {
//                             title: function(context) {
//                                 return 'Month: ' + context[0].label
//                             },
//                             label: function(context) {
//                                 return 'Balance: ₺' + context.parsed.y.toLocaleString()
//                             }
//                         }
//                     }
//                 },
//                 scales: {
//                     x: {
//                         display: true,
//                         grid: {
//                             display: false
//                         },
//                         ticks: {
//                             font: {
//                                 size: 10
//                             }
//                         }
//                     },
//                     y: {
//                         display: false,
//                         beginAtZero: false
//                     }
//                 },
//                 interaction: {
//                     intersect: false,
//                     mode: 'index'
//                 }
//             }
//         })
        
//         console.log('BalanceChart: Chart rendered successfully')
//     }
// }

// BalanceChart.template = "BalanceChart"