from odoo import models, fields
from datetime import date, timedelta
import json

class MonthRecord(models.Model):
    _name = 'month.record'
    _description = 'Month Record'

    name = fields.Char('Month Name', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    today_immediate = fields.Float(string="Today Immediate", compute="_compute_totals", store=True)
    today_transfer = fields.Float(string="Today Transfer", compute="_compute_totals", store=True)
    today_check = fields.Float(string="Today Check", compute="_compute_totals", store=True)

    this_week_immediate = fields.Float(string="This Week Immediate", compute="_compute_totals", store=True)
    this_week_transfer = fields.Float(string="This Week Transfer", compute="_compute_totals", store=True)
    this_week_check = fields.Float(string="This Week Check", compute="_compute_totals", store=True)

    this_month_immediate = fields.Float(string="This Month Immediate", compute="_compute_totals", store=True)
    this_month_transfer = fields.Float(string="This Month Transfer", compute="_compute_totals", store=True)
    this_month_check = fields.Float(string="This Month Check", compute="_compute_totals", store=True)

    other_immediate = fields.Float(string="Other Immediate", compute="_compute_totals", store=True)
    other_transfer = fields.Float(string="Other Transfer", compute="_compute_totals", store=True)
    other_check = fields.Float(string="Other Check", compute="_compute_totals", store=True)
 

    def _compute_totals(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday() + 1)  # Last Saturday
        week_end = week_start + timedelta(days=6)  # Next Friday
        month_start = today.replace(day=1)
        month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)

        for record in self:
            record.today_immediate = self._calculate_total(today, today, 'Immediate')
            record.today_transfer = self._calculate_total(today, today, 'Transfer')
            record.today_check = self._calculate_total(today, today, 'Check')

            record.this_week_immediate = self._calculate_total(week_start, week_end, 'Immediate')
            record.this_week_transfer = self._calculate_total(week_start, week_end, 'Transfer')
            record.this_week_check = self._calculate_total(week_start, week_end, 'Check')

            record.this_month_immediate = self._calculate_total(month_start, month_end, 'Immediate')
            record.this_month_transfer = self._calculate_total(month_start, month_end, 'Transfer')
            record.this_month_check = self._calculate_total(month_start, month_end, 'Check')

            record.other_immediate = self._calculate_total(month_end + timedelta(days=1), None, 'Immediate')
            record.other_transfer = self._calculate_total(month_end + timedelta(days=1), None, 'Transfer')
            record.other_check = self._calculate_total(month_end + timedelta(days=1), None, 'Check')


    def _calculate_total(self, start_date, end_date, term):
        """
        Replace this method with logic to calculate totals based on dates and payment terms.
        """
        
        domain = [('invoice_due_date', '>=', start_date),
                  ('state', '=', 'posted'),
                  ('move_type', 'in', ['out_invoice', 'out_refund']),
                  ('payment_state', 'in', ['not_paid', 'partial']),
                  ('line_ids.account_id.code',"=",120001),
                  ('amount_residual_signed',"!=",0),
                  ('invoice_payment_term_id.name', 'ilike', term)
                  ]
        if end_date:
            domain.append(('invoice_due_date', '=', end_date))
        return sum(self.env['account.move'].search(domain).mapped('amount_residual_signed'))
