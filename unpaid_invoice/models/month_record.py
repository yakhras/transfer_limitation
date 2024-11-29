from odoo import models, fields
from datetime import datetime

class MonthRecord(models.Model):
    _name = 'month.record'
    _description = 'Month Record'

    name = fields.Char('Month Name', required=True)
    november_total = fields.Monetary(string="January Total", compute="_compute_month_totals", currency_field='currency_id')
    december_total = fields.Monetary(string="February Total", compute="_compute_month_totals", currency_field='currency_id')
   
    # Add fields for other months similarly...
    today_total = fields.Monetary(string="Today Total", compute="_compute_month_totals", currency_field='currency_id')
    november_total_paid = fields.Monetary(string="November Paid Total", compute="_compute_november_totals", currency_field='currency_id')
    november_total_unpaid = fields.Monetary(string="November Unpaid/Partial Total", compute="_compute_november_totals", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    november_total_immediate = fields.Monetary(string="November Immediate Total", compute="_compute_november_payment_terms", currency_field='currency_id')
    november_total_transfer = fields.Monetary(string="November Transfer Total", compute="_compute_november_payment_terms", currency_field='currency_id')
    november_total_check = fields.Monetary(string="November Check Total", compute="_compute_november_payment_terms", currency_field='currency_id')

    
    def _compute_month_totals(self):
        # Define the base domain that applies to all cases
        base_domain = [
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('line_ids.account_id.code', '=', '120001'),
            ('amount_residual_signed', '!=', 0),
        ]
        # Map of month names to date ranges
        month_to_date_map = {
            'November': ('2024-11-01', '2024-11-30'),
            'December': ('2024-12-01', '2024-12-31'),
            # Add date ranges for other months...
        }
        # Get today's date as a string
        today_date = datetime.today().strftime('%Y-%m-%d')

        for record in self:
            for month, date_range in month_to_date_map.items():
                # Add date range to the domain dynamically
                domain = base_domain + [
                    ('invoice_date_due', '>=', date_range[0]),
                    ('invoice_date_due', '<=', date_range[1]),
                ]
                invoices = self.env['account.move'].search(domain)
                total = sum(invoices.mapped('amount_residual_signed'))

                # Assign totals to the corresponding fields
                if month == 'November':
                    record.november_total = total
                elif month == 'December':
                    record.december_total = total
                # Add conditions for other months...

            # Calculate today's total by modifying the base domain
            today_domain = base_domain + [('invoice_date_due', '=', today_date)]
            today_invoices = self.env['account.move'].search(today_domain)
            record.today_total = sum(today_invoices.mapped('amount_residual_signed'))


    def _compute_november_totals(self):
        for record in self:
            if record.name == 'November':
                # Define the date range for November
                domain = [
                    ('invoice_date_due', '>=', '2024-11-01'),
                    ('invoice_date_due', '<=', '2024-11-30'),
                    ('state', '=', 'posted'),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('line_ids.account_id.code', '=', '120001'),
                ]

                # Paid Invoices
                paid_domain = domain + [('payment_state', '=', 'paid')]
                paid_invoices = self.env['account.move'].search(paid_domain)
                record.november_total_paid = sum(paid_invoices.mapped('amount_residual_signed'))

                # Unpaid or Partial Invoices
                unpaid_domain = domain + [('payment_state', 'in', ['not_paid', 'partial'])]
                unpaid_invoices = self.env['account.move'].search(unpaid_domain)
                record.november_total_unpaid = sum(unpaid_invoices.mapped('amount_residual_signed'))
            else:
                record.november_total_paid = 0
                record.november_total_unpaid = 0


    def _compute_november_payment_terms(self):
        for record in self:
            if record.name == 'November':
                # Define the date range for November
                domain = [
                    ('invoice_date_due', '>=', '2024-11-01'),
                    ('invoice_date_due', '<=', '2024-11-30'),
                    ('state', '=', 'posted'),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('line_ids.account_id.code', '=', '120001'),
                ]

                # Immediate Payment Term
                immediate_domain = domain + [('invoice_payment_term_id.name', 'ilike', 'Immediate')]
                immediate_invoices = self.env['account.move'].search(immediate_domain)
                record.november_total_immediate = sum(immediate_invoices.mapped('amount_residual_signed'))

                # Transfer Payment Term
                transfer_domain = domain + [('invoice_payment_term_id.name', 'ilike', 'Transfer')]
                transfer_invoices = self.env['account.move'].search(transfer_domain)
                record.november_total_transfer = sum(transfer_invoices.mapped('amount_residual_signed'))

                # Check Payment Term
                check_domain = domain + [('invoice_payment_term_id.name', 'ilike', 'Check')]
                check_invoices = self.env['account.move'].search(check_domain)
                record.november_total_check = sum(check_invoices.mapped('amount_residual_signed'))
            else:
                record.november_total_immediate = 0
                record.november_total_transfer = 0
                record.november_total_check = 0