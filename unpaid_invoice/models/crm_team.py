from odoo.tools import date_utils
from odoo import models, fields, api

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    unpaid_invoice_total_month = fields.Float(
        compute='_compute_unpaid_invoice_total_month',
        string="Unpaid Invoices This Month", 
        store=True
    )

   
    def _compute_unpaid_invoice_total_month(self):
        today = fields.Date.today()
        month_ago = (today  + date_utils.relativedelta(months=-1)).strftime('%Y-%m-%d')  # Calculate the date 30 days ago

        for team in self:
            # Retrieve unpaid invoices due within the last 30 days specific to this team
            invoices = self.env['unpaid.invoice'].search([
                ('due_date', '>=', month_ago),
                ('due_date', '<', today),
                ('team_id', '=', team.id)
            ])
            
            # Sum the unpaid amounts for this team's invoices due in the last month
            total_due = sum(invoice.amount_due for invoice in invoices)
            team.unpaid_invoice_total_month = total_due
