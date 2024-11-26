from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import date



class UnpaidInvoice(models.Model):
    _name = 'unpaid.invoice'
    _description = 'Unpaid Invoices for Sales Teams'

    invoice_id = fields.Many2one('account.move', string='Invoice', required=True)
    document_id = fields.Char(related='invoice_id.document_number', string='Invoice Number')
    invoice_date = fields.Date(related='invoice_id.invoice_date', string='Invoice Date')
    partner_id = fields.Many2one(related='invoice_id.partner_id', string="Customer", store=True)
    partner_mail = fields.Char(related='partner_id.email', string="Email")
    partner_phone = fields.Char(related='partner_id.phone', string="Phone")
    partner_term = fields.Char(related='partner_id.property_payment_term_id.name', string="Payment Term")
    amount_due = fields.Monetary(related='invoice_id.amount_residual', string="Amount Due (Invoice)")
    amount_due_signed = fields.Monetary(related='invoice_id.amount_residual_signed', string="Amount Due (Company)")
    due_date = fields.Date(related='invoice_id.invoice_date_due', string="Due Date")
    team_id = fields.Many2one(related='invoice_id.team_id', string="Sales Team", store=True)
    sales_person = fields.Many2one(related='invoice_id.invoice_user_id', string="Sales Person", store=True)
    sale_order_ids = fields.Many2many('sale.order', string="Sale Orders", compute='_compute_sale_orders', store=False)
    sale_order = fields.Char(related='sale_order_ids.name', string="Sale Order")
    days_since_invoice = fields.Integer(string='Days Since Invoice', compute='_compute_days_since_invoice', store=True)
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
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    month = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December'),
    ], string="Month")


    def populate_unpaid_invoices(self):
        # Calculate the first and last day of the current month
        # today = datetime.today()
        # first_day_of_month = today.replace(day=1)
        # last_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)
        # Define the domain for unpaid invoices
        # domain = [
        #     ('state', '=', 'posted'),
        #     ('move_type', 'in', ['out_invoice', 'out_refund']),
        #     ('payment_state', 'in', ['not_paid', 'partial']),
        #     ('invoice_date_due', '>=', first_day_of_month.strftime('%Y-%m-%d')),
        #     ('invoice_date_due', '<=', last_day_of_month.strftime('%Y-%m-%d'))
        # ]
        # first_day_of_previous_month = (today.replace(day=1) - relativedelta(months=1)).replace(day=1)
        # last_day_of_previous_month = first_day_of_previous_month + relativedelta(months=1, days=-1)
        # Update the domain with the additional date criteria for the previous month
        # domain = [
        #     ('state', '=', 'posted'),
        #     ('move_type', 'in', ['out_invoice', 'out_refund']),
        #     ('payment_state', 'in', ['not_paid', 'partial']),
        #     ('invoice_date_due', '>=', first_day_of_previous_month.strftime('%Y-%m-%d')),
        #     ('invoice_date_due', '<=', last_day_of_previous_month.strftime('%Y-%m-%d'))
        # ]

        domain = [
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('amount_residual_signed',"!=",0),
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
              

    # to display the partner’s name instead of the default object name
    def name_get(self):
        result = []
        for record in self:
            name = record.invoice_id.name  # Get the partner name
            result.append((record.id, name))  # Return a tuple of (record_id, name)
        return result    


    def send_email_unpaid_invoices(self):
        template = self.env.ref('unpaid_invoice.unpaid_invoice')
        for rec in self:
            template.send_mail(rec.id, force_send=True)


    @api.depends_context('action', 'search_default_team_id')
    def _compute_details(self):
        for record in self:
            domain = []

            # Compute Action ID and Name
            action_id = self.env.context.get('action', 0)
            if action_id:
                action = self.env['ir.actions.act_window'].sudo().browse(action_id)
                action_name = action.name if action.name else []

                # Append the domain with action_name
                if 'Today' in action_name:
                    domain.append(('due_date', '=', fields.Date.today().strftime('%Y-%m-%d')))
                else:
                    domain.append(('due_date', '<', fields.Date.today().strftime('%Y-%m-%d')))
            
            # Append the domain with team_id 
            team_id = self.env.context.get('search_default_team_id')
            if team_id:
                domain.append(('team_id', '=', team_id))

            # Assign the record count to unpaid_invoice_count field
            record.unpaid_invoice_count = self.env['unpaid.invoice'].search_count(domain)

    
    @api.depends('invoice_id')
    def _compute_sale_orders(self):
        for record in self:
            if record.invoice_id:
                record.sale_order_ids = record.invoice_id.sale_ids
            else:
                record.sale_order_ids = False

    
    @api.depends('invoice_date')
    def _compute_days_since_invoice(self):
        for record in self:
            if record.invoice_date:
                record.days_since_invoice = (date.today() - record.invoice_date).days
            else:
                record.days_since_invoice = 0
