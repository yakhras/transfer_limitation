from odoo import models, fields, api

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    unpaid_invoice_total_today = fields.Float(
        compute='_compute_unpaid_invoice_total_today',
        string="Unpaid Invoices Today", 
        store=True
    )

   
    def _compute_unpaid_invoice_total_today(self):
        today = fields.Date.today()  # Calculate today's date once

        for team in self:
            # Retrieve unpaid invoices for today's due date specific to this team
            invoices = self.env['unpaid.invoice'].search([
                ('due_date', '=', today),
                ('team_id', '=', team.id)
            ])
            
            # Sum the unpaid amounts for this team's invoices
            total_due = sum(invoice.amount_due for invoice in invoices)
            team.unpaid_invoice_total_today = total_due
