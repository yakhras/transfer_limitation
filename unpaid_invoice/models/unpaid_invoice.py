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
    amount_total = fields.Monetary(string="Total Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Currency")

    @api.model
    def update_unpaid_invoices(self):
        # Logic to fetch unpaid invoices and populate this model
        pass

    def send_daily_report(self):
        # Logic to generate and send the PDF report
        pass

    @api.model
    def populate_unpaid_invoices(self):
        # Define the domain for unpaid invoices
        domain = [
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('payment_state', 'in', ['not_paid', 'partial'])
        ]
        
        # Fetch records from account.move that meet the domain criteria
        account_moves = self.env['account.move'].search(domain)
        
        # Loop through each fetched record and create a record in unpaid.invoice
        for move in account_moves:
            self.create({
                'name': move.name,
                'invoice_id': move.id,
                'partner_id': move.partner_id.id,
                'amount_total': move.amount_total,
                'currency_id': move.currency_id.id,
            })

    @api.model
    def create(self, vals):
        # Call the populate method to fetch and populate unpaid invoices
        self.populate_unpaid_invoices()
        
        # Proceed with the default create behavior
        return super(UnpaidInvoice, self).create(vals)
    
