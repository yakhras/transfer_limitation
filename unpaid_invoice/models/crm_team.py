from odoo.tools import date_utils
from odoo import models, fields, api

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    unpaid_invoice_total_usd = fields.Monetary(
        compute='_compute_unpaid_invoice_totals', currency_field='currency_usd',
        string="Unpaid Invoices Total (USD)"
    )
    unpaid_invoice_total_eur = fields.Monetary(
        compute='_compute_unpaid_invoice_totals', currency_field='currency_eur',
        string="Unpaid Invoices Total (EUR)"
    )

    # Currency fields for multi-currency support
    currency_usd = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.USD').id, readonly=True)
    currency_eur = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR').id, readonly=True)

   
    def _compute_unpaid_invoice_total_month(self):
        today = fields.Date.today()
        month_ago = (today  + date_utils.relativedelta(months=-1)).strftime('%Y-%m-%d')  # Calculate the date 30 days ago

        

        for team in self:
            total_usd = total_eur = 0.0  # Initialize totals for each currency

            # Retrieve unpaid invoices within the last 30 days for the team
            invoices = self.env['unpaid.invoice'].search([
                ('due_date', '>=', month_ago),
                ('due_date', '<', today),
                ('team_id', '=', team.id)
            ])

            # Sum amounts by currency
            for invoice in invoices:
                if invoice.currency_id == team.currency_usd:
                    total_usd += invoice.amount_due
                elif invoice.currency_id == team.currency_eur:
                    total_eur += invoice.amount_due
                # Add more conditions if other currencies are needed.

            # Assign computed values to each field
            team.unpaid_invoice_total_usd = total_usd
            team.unpaid_invoice_total_eur = total_eur
            # Set values for other currency fields if they exist.
