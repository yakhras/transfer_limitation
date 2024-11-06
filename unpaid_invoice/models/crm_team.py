from collections import defaultdict
import json
from datetime import datetime
from odoo import models, fields, api



class CrmTeam(models.Model):
    _inherit = 'crm.team'

    unpaid_invoice_totals_json = fields.Text(
        string="Unpaid Invoice Totals (JSON)",
        compute='_compute_unpaid_invoice_totals'
    )

    @api.depends()
    def _compute_unpaid_invoice_totals(self):
        # Retrieve all active sales team IDs dynamically
        all_sales_team_ids = self.env['crm.team'].search([]).ids

        # List of action external IDs to fetch dynamically
        action_external_ids = [
            'unpaid_invoice.action_unpaid_invoice_today',
            'unpaid_invoice.action_unpaid_invoice_week',
            'unpaid_invoice.action_unpaid_invoice_2weeks',
            'unpaid_invoice.action_unpaid_invoice_month'
        ]
        
        # Retrieve domains dynamically for each action by its external ID
        action_domains = {}
        for action_id in action_external_ids:
            action = self.env.ref(action_id)
            if action and action.domain:
                action_domains[action_id] = eval(action.domain)

        for team in self:
            totals = {}
            for action_key, date_domain in action_domains.items():
                for team_id in all_sales_team_ids:
                    # Combine the action's domain with the sales team ID
                    domain = date_domain + [('team_id', '=', team_id)]
                    invoices = self.env['unpaid.invoice'].search(domain)
                    
                    # Calculate totals for each currency
                    currency_totals = defaultdict(float)
                    for inv in invoices:
                        currency_totals[inv.currency_id] += inv.amount_due
                    
                    # Format the key to include both the action and the team ID
                    key = f"{action_key}_team_{team_id}"
                    totals[key] = {
                        currency.name: f"{amount:.2f}" for currency, amount in currency_totals.items()
                    }

            # Store totals as JSON
            team.unpaid_invoice_totals_json = json.dumps(totals)
