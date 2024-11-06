from odoo import models, fields, api
from datetime import date

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    # Compute fields for unpaid invoices
    unpaid_invoice_total_today = fields.Float(
        compute='_compute_unpaid_invoice_total_today',
        string="Unpaid Invoices Today", 
        store=True
    )

    
    def _compute_unpaid_invoice_total_today(self):
        # Loop over all crm.team records
        for team in self:
            total_due = 0.0
            today = fields.Date.today()  # Get today's date
            
            # Retrieve unpaid invoices for today's due date for each team
            invoices = self.env['unpaid.invoice'].search([
                ('due_date', '=', today),  # Filter by today's due date
                ('team_id', '=', team.id)  # Filter by the current team's ID
            ])
            
            # Sum the unpaid amounts for the invoices
            for invoice in invoices:
                total_due += invoice.amount_due
            
            # Set the total due for the team
            team.unpaid_invoice_total_today = total_due
