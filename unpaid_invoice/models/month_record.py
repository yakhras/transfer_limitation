from odoo import models, fields
from datetime import datetime, timedelta
import json

class MonthRecord(models.Model):
    _name = 'month.record'
    _description = 'Month Record'

    name = fields.Char('Month Name', required=True)
    totals = fields.Text(string="Totals", compute="_compute_totals")

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

    # Map of month names to date ranges
    month_to_date_map = {
        'November': ('2024-11-01', '2024-11-30'),
        'December': ('2024-12-01', '2024-12-31'),
        # Add date ranges for other months...
    }
    
    def _compute_month_totals(self):
        # Define the base domain that applies to all cases
        base_domain = [
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('line_ids.account_id.code', '=', '120001'),
            ('amount_residual_signed', '!=', 0),
        ]
        
        # Get today's date as a string
        today_date = datetime.today().strftime('%Y-%m-%d')

        for record in self:
            for month, date_range in self.month_to_date_map.items():
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
        

    def _compute_totals(self):
        today = datetime.today()
        week_start = today - timedelta(days=today.weekday() + 1)  # Last Saturday
        week_end = week_start + timedelta(days=6)  # Next Friday
        month_start = today.replace(day=1)
        month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)

        for record in self:
            totals_data = {
                "today": {
                    "immediate": self._calculate_total(today, today, 'Immediate'),
                    "transfer": self._calculate_total(today, today, 'Transfer'),
                    "check": self._calculate_total(today, today, 'Check'),
                },
                "this_week": {
                    "immediate": self._calculate_total(week_start, week_end, 'Immediate'),
                    "transfer": self._calculate_total(week_start, week_end, 'Transfer'),
                    "check": self._calculate_total(week_start, week_end, 'Check'),
                },
                "this_month": {
                    "immediate": self._calculate_total(month_start, month_end, 'Immediate'),
                    "transfer": self._calculate_total(month_start, month_end, 'Transfer'),
                    "check": self._calculate_total(month_start, month_end, 'Check'),
                },
                "other": {
                    "immediate": self._calculate_total(month_end + timedelta(days=1), None, 'Immediate'),
                    "transfer": self._calculate_total(month_end + timedelta(days=1), None, 'Transfer'),
                    "check": self._calculate_total(month_end + timedelta(days=1), None, 'Check'),
                }
            }
            # Serialize totals to JSON
            record.totals = json.dumps(totals_data)

    def _calculate_total(self, start_date, end_date, term):
        domain = [
            ('invoice_date_due', '>=', start_date),
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('payment_state', 'in', ['not_paid', 'partial']),
            ('line_ids.account_id.code', '=', '120001'),
            ('amount_residual_signed', '!=', 0),
            ('invoice_payment_term_id.name', 'ilike', term)
        ]
        if end_date:
            domain.append(('invoice_date_due', '<=', end_date))

        invoices = self.env['account.move'].search(domain)
        return sum(invoices.mapped('amount_residual_signed'))
