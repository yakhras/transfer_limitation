/** @odoo-module */

import { registry } from "@web/core/registry"
const ajax = require('web.ajax');
const { Component } = owl
const { useRef, onWillStart, onMounted } = owl.hooks;

export class ChartRenderer extends Component {
    setup(){
        this.chartRef = useRef("chart")
        onWillStart(async ()=>{
            await ajax.loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
        })

        onMounted(()=>this.renderChart())
    }

    renderChart(){
        new Chart(this.chartRef.el,
        {
          type: this.props.type,
          data: {
            labels: [
                'Red',
                'Blue',
                'Yellow'
              ],
              datasets: [
              {
                label: 'My First Dataset',
                data: [300, 50, 100],
                hoverOffset: 4
              },{
                label: 'My Second Dataset',
                data: [100, 70, 150],
                hoverOffset: 4
              }]
          },
          options: {
            responsive: true,
            plugins: {
              legend: {
                position: 'bottom',
              },
              title: {
                display: true,
                text: this.props.title,
                position: 'bottom',
              }
            }
          },
        }
      );
    }
}

ChartRenderer.template = "owl.ChartRenderer"