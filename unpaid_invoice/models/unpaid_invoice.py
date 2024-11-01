# from odoo import models, fields
# from datetime import date

# class CrmTeam(models.Model):
#     _inherit = 'crm.team'

#     total_count = fields.Integer(compute="_count_records", store=True)
    
#     def _count_records(self):
#           self.total_count = self.env['account.move'].search_count(domain)
                

    
from odoo import models, fields, api

class UnpaidInvoice(models.Model):
    _name = 'unpaid.invoice'
    _description = 'Unpaid Invoices for Sales Teams'

    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    document_id = fields.Char(related='invoice_id.document_number', string='Invoice Number')
    partner_id = fields.Many2one(related='invoice_id.partner_id', string="Customer", store=True)
    amount_due = fields.Monetary(related='invoice_id.amount_residual', string="Amount Due")
    due_date = fields.Date(related='invoice_id.invoice_date_due', string="Due Date")
    team_id = fields.Many2one(related='invoice_id.team_id', string="Sales Team", store=True)
    team_member_ids = fields.Many2many('res.users', string="Team Members")
    state = fields.Selection(related='invoice_id.state', string="Invoice Status")
    payment_state = fields.Selection(related='invoice_id.payment_state', string="Payment Status")
    currency_id = fields.Many2one(related='invoice_id.currency_id', string="Currency")
    report_attachment_id = fields.Many2one('ir.attachment', string="Report Attachment")
    last_email_sent = fields.Datetime(string="Last Email Sent")
    email_recipients = fields.Char(string="Email Recipients")
    amount_total = fields.Monetary(string="Total Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Currency")
    unpaid_invoice_count = fields.Char(string="Unpaid Invoice Count",compute='_compute_details')
    action_id = fields.Integer(string='Action ID', compute='_compute_details')
    action_domain = fields.Char(string='Action Domain', compute='_compute_details')


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
          
            # Check if the invoice already exists to avoid duplicate entries
            if not self.search([('invoice_id', '=', move.id)]):
                vals = {
                    'invoice_id': move.id,
                    'partner_id': move.partner_id.id,
                    'amount_total': move.amount_total,
                    'currency_id': move.currency_id.id,
                }
                self.create(vals)  # Pass the vals dictionary to create()
              

    def send_email_unpaid_invoices(self):
        template = self.env.ref('unpaid_invoice.unpaid_invoice')
        for rec in self:
            template.send_mail(rec.id, force_send=True)



    

    @api.depends_context('action', 'search_default_team_id')
    def _compute_details(self):
        for record in self:
            # Compute Action ID and Domain
            action_id = self.env.context.get('action', 0)
            record.action_id = action_id

            action_domain = []
            if action_id:
                action = self.env['ir.actions.act_window'].sudo().browse(action_id)
                action_domain = action.name if action.name else []
                record.action_domain = str(action_domain)
            else:
                record.action_domain = '[]'

            # Compute Unpaid Invoice Count
            base_domain = [
                ('state', '=', 'posted'),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('payment_state', 'in', ['not_paid', 'partial']),
            ]

            # Append the domain with team_id and action_domain
            team_id = self.env.context.get('search_default_team_id')
            if team_id:
                base_domain.append(('team_id', '=', team_id))

            if 'Today' in action_domain:
                base_domain.append(('due_date', '=', fields.Date.today().strftime('%Y-%m-%d')))
            else:
                base_domain.append(('due_date', '<', fields.Date.today().strftime('%Y-%m-%d')))

            record.unpaid_invoice_count = self.env['account.move'].search_count(base_domain)

    