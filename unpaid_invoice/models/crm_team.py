from odoo import models, fields
from collections import defaultdict

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    unpaid_invoice_totals_json = fields.Char(
        string="Unpaid Invoice Totals",
        compute='_compute_unpaid_invoice_totals_json',
        store=True
    )

    def _compute_unpaid_invoice_totals_json(self):
        # Define a specific domain for the unpaid invoices
        domain = self._get_action_domain()

        # Calculate total unpaid invoice amounts for the given domain
        totals = self._compute_unpaid_invoice_total_for_domain(domain)

        # Store the totals in the unpaid_invoice_totals_json field
        self.unpaid_invoice_totals_json = totals

    def _get_action_domain(self):
        """
        Fetches the domain from a specific action and converts context_today() to its equivalent in Python.
        """
        # This is just a placeholder domain for demonstration. You can dynamically retrieve it if needed.
        action_id = 'unpaid_invoice.action_unpaid_invoice_today'  # Example action ID
        action = self.env.ref(action_id)

        if action and action.domain:
            # Replace 'context_today()' with equivalent Python logic (today's date)
            domain = eval(action.domain, {"context_today": fields.Date.today()})
            return domain
        return []

    def _compute_unpaid_invoice_total_for_domain(self, domain):
        """
        Computes the total amount_due for unpaid invoices based on the given domain.
        Returns a dictionary with currency as key and total amount due as value.
        """
        total_due_by_currency = defaultdict(float)

        # Fetch the unpaid invoices that match the domain filter
        unpaid_invoices = self.env['unpaid.invoice'].search(domain)

        # Sum the amounts due for each currency
        for invoice in unpaid_invoices:
            currency = invoice.currency_id
            amount_due = invoice.amount_due

            # Sum the amount due for the currency
            total_due_by_currency[currency] += amount_due

        return total_due_by_currency
