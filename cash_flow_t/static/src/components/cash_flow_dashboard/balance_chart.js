// /** @odoo-module */

// const { Component } = owl

// export class BalanceChart extends Component {
//     setup(){
//         console.log('BalanceChart component created for:', this.props.accountCode)
//         this.chartId = `chart_${Math.random().toString(36).substr(2, 9)}`
//         setTimeout(() => this.loadChart(), 200)
//     }

//     async loadChart(){
//         try {
//             if (typeof Chart === 'undefined') {
//                 await this.loadChartJS()
//             } else {
//                 this.renderChart()
//             }
//         } catch (error) {
//             console.error("Error loading Chart.js:", error)
//         }
//     }

//     async loadChartJS() {
//         return new Promise((resolve, reject) => {
//             const existingScript = document.querySelector('script[src*="chart.umd.min.js"]')
//             if (existingScript) {
//                 setTimeout(() => (typeof Chart !== 'undefined' ? resolve() : reject()), 500)
//                 return
//             }

//             const script = document.createElement('script')
//             script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js'
//             script.onload = () => setTimeout(() => { this.renderChart(); resolve() }, 100)
//             script.onerror = reject
//             document.head.appendChild(script)
//         })
//     }

//     renderChart(){
//         const canvas = document.getElementById(this.chartId)
//         if (!canvas || typeof Chart === 'undefined') return

//         new Chart(canvas, {
//             type: 'line',
//             data: {
//                 labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
//                 datasets: [{
//                     label: 'Balance',
//                     data: [
//                         this.props.currentBalance * 0.8,
//                         this.props.currentBalance * 0.9,
//                         this.props.currentBalance * 0.85,
//                         this.props.currentBalance * 1.1,
//                         this.props.currentBalance * 1.05,
//                         this.props.currentBalance * 0.95,
//                         this.props.currentBalance
//                     ],
//                     borderColor: this.getColor(this.props.balanceColor, 'border'),
//                     backgroundColor: this.getColor(this.props.balanceColor, 'bg'),
//                     borderWidth: 2,
//                     fill: true,
//                     tension: 0.3,
//                     pointRadius: 2,
//                     pointHoverRadius: 4
//                 }]
//             },
//             options: {
//                 responsive: true,
//                 maintainAspectRatio: false,
//                 plugins: {
//                     legend: { display: false },
//                     tooltip: {
//                         mode: 'index',
//                         intersect: false,
//                         callbacks: {
//                             title: ctx => 'Month: ' + ctx[0].label,
//                             label: ctx => 'Balance: ₺' + ctx.parsed.y.toLocaleString()
//                         }
//                     }
//                 },
//                 scales: {
//                     x: { display: true, grid: { display: false }, ticks: { font: { size: 10 } } },
//                     y: { display: false, beginAtZero: false }
//                 },
//                 interaction: { intersect: false, mode: 'index' }
//             }
//         })
//     }

//     getColor(color, type){
//         const colors = {
//             green: { border: '#28a745', bg: 'rgba(40, 167, 69, 0.1)' },
//             red: { border: '#dc3545', bg: 'rgba(220, 53, 69, 0.1)' },
//             default: { border: '#17a2b8', bg: 'rgba(23, 162, 184, 0.1)' }
//         }
//         return (colors[color] || colors.default)[type]
//     }
// }

// BalanceChart.template = "BalanceChart"