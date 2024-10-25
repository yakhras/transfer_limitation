# from odoo import models, fields
# from datetime import date

# class CrmTeam(models.Model):
#     _inherit = 'crm.team'

#     label_date = fields.Char(
#         default=lambda s: "Today",
#         translate=True,
#         ) 
#     total_count = fields.Integer(compute="_count_records", store=True)
    
#     def _count_records(self):
#           today = date.today()
#           domain = [
#             ('move_type', '=', 'out_invoice'),
#                 ('state', '=', 'posted'),
#                 ('payment_state', 'in', ('not_paid', 'partial')),
#                 ('invoice_date_due', '=', today.strftime('%Y-%m-%d')),
#                 ('partner_id.property_account_receivable_id.code', '=', 120001)
#         ]
#           self.total_count = self.env['account.move'].search_count(domain)
                
#     def action_unpaid_invoice(self):
#          action = self.env["ir.actions.actions"]._for_xml_id(
#               "unpaid_invoice.action_report_unpaid_invoice_html")
#          return action
    
from odoo import models, fields, api

class UnpaidInvoice(models.Model):
    _name = 'unpaid.invoice'
    _description = 'Unpaid Invoices for Sales Teams'

    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    partner_id = fields.Many2one(related='invoice_id.partner_id', string="Customer")
    amount_due = fields.Monetary(related='invoice_id.amount_residual', string="Amount Due")
    due_date = fields.Date(related='invoice_id.invoice_date_due', string="Due Date")
    team_id = fields.Many2one('crm.team', string="Sales Team")
    team_member_ids = fields.Many2many('res.users', string="Team Members")
    state = fields.Selection(related='invoice_id.state', string="Invoice Status")
    currency_id = fields.Many2one(related='invoice_id.currency_id', string="Currency")
    report_attachment_id = fields.Many2one('ir.attachment', string="Report Attachment")
    last_email_sent = fields.Datetime(string="Last Email Sent")
    email_recipients = fields.Char(string="Email Recipients")

    @api.model
    def update_unpaid_invoices(self):
        # Logic to fetch unpaid invoices and populate this model
        pass

    def send_daily_report(self):
        # Logic to generate and send the PDF report
        pass
    
# class CrmTeam(models.Model):
#     _inherit = 'crm.team'
