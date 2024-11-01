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
    unpaid_invoice_count = fields.Char(string="Unpaid Invoice Count", store=True)
    action_id = fields.Integer(string='Action ID', compute='_compute_action_id')
    action_domain = fields.Char(string='Action Domain', compute='_compute_action_domain')


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



    

    @api.depends_context('search_default_team_id')
    def compute_unpaid_invoice_count(self):
        """Compute the count of unpaid invoices for the current sales team if provided in context."""
        for record in self:
            # Define the base domain for unpaid invoices due today
            domain = [
                ('state', '=', 'posted'),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('payment_state', 'in', ['not_paid', 'partial']),
            ]
            
            # Check context for 'search_default_team_id' and filter by team_id if provided
            team_id = self.env.context.get('search_default_team_id')
            if team_id:
                domain.append(('team_id', '=', team_id))
            
            # Use search_count to get the count of matching records
            record.unpaid_invoice_count = self.env['account.move'].search_count(domain)


    def get_current_action_domain(self):
        # Retrieve the action ID from the context
        action_id = self.env.context.get('current_action_id')
        
        if action_id:
            # Fetch the action record using the action ID
            action = self.env['ir.actions.act_window'].browse(action_id)
            
            # Get the domain from the action
            domain = action.domain if action else []
            self.unpaid_invoice_count =  domain
        else:
            return []
        

    @api.depends_context('action')
    def _compute_action_id(self):
        for record in self:
            record.action_id = self.env.context.get('action', 0)

    @api.depends('action_id')
    def _compute_action_domain(self):
        for record in self:
            action = self.env['ir.actions.actions'].sudo().browse(record.action_id)
            record.action_domain = str(action.domain) if action.domain else '[]'

    