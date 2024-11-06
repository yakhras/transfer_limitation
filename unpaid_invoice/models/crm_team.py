from odoo import models, fields, api
from datetime import date

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    unpaid_invoice_total_today = fields.Float(
        compute='_compute_unpaid_invoice_total_today',
        string="Unpaid Invoices Today", 
        store=True
    )

    
    def _compute_unpaid_invoice_total_today(self):
        total_due = 0.0
        today = fields.Date.today()  # Get today's date
        
        # Retrieve unpaid invoices where the due date is today
        invoices = self.env['unpaid.invoice'].search([
            ('due_date', '=', today),  # Filter by today's due date
            ('team_id', '=', self.id)  # Filter by the current sales team
        ])
        
        for invoice in invoices:
            total_due += invoice.amount_due
        
        self.unpaid_invoice_total_today = total_due
