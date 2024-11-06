import re
from collections import defaultdict
from datetime import datetime
from odoo import models, fields

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    unpaid_invoice_totals_json = fields.Char(compute='_compute_unpaid_invoice_totals_json', store=True)

    def _compute_unpaid_invoice_totals_json(self):
        # Initialize a defaultdict to store totals by team and currency
        totals_by_team_and_currency = defaultdict(lambda: defaultdict(int))

        # Get all active CRM teams
        teams = self.env['crm.team'].search([]).ids  # Retrieves all crm.team records

        # Dynamically fetch actions related to unpaid invoices
        actions = self.env['ir.actions.act_window'].search([
            ('name', 'ilike', 'unpaid_invoice')  # Filter actions related to unpaid invoices
        ])

        # Dynamically fetch domains based on the action's domain field
        action_domains = {}
        for action in actions:
            if action.domain:
                # Use eval to execute the domain expression (you may want to sanitize this in real-world apps)
                action_domains[action.id] = eval(action.domain)

        # Function to replace context_today() with the current date in the domain
        def replace_context_today(domain_str):
            return re.sub(r'context_today\(\)', f"'{datetime.today().date()}'", domain_str)

        # Loop through each team and apply the domain logic for each
        for team in teams:
            # Loop through each action domain
            for action_id, domain in action_domains.items():
                # Replace any context_today() in the domain string
                domain_str = str(domain)  # Convert the domain to a string for replacement
                domain_str = replace_context_today(domain_str)
                domain = eval(domain_str)  # Re-parse the domain after replacement
                
                # Now, add the dynamic team ID filter
                team_domain = domain + [('team_id', '=', team.id)]

                # Fetch the unpaid invoices based on the domain and sum their amounts due by currency
                unpaid_invoices = self.env['unpaid.invoice'].search(team_domain)

                # Sum the amounts due by currency
                for invoice in unpaid_invoices:
                    currency = invoice.currency_id.name
                    totals_by_team_and_currency[team.id][currency] += invoice.amount_due

        # Now, store the totals in a JSON field for easy retrieval
        self.unpaid_invoice_totals_json = str(totals_by_team_and_currency)
