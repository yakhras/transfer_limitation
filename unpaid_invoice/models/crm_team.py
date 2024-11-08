from odoo.tools import date_utils
from odoo import models, fields, api

class CrmTeam(models.Model):
    _inherit = 'crm.team'


    # Today #
    unpaid_invoice_total_today_usd = fields.Monetary(compute='_compute_unpaid_invoice_totals_today', currency_field='currency_usd')
    unpaid_invoice_total_today_eur = fields.Monetary(compute='_compute_unpaid_invoice_totals_today', currency_field='currency_eur')
    unpaid_invoice_total_today_try = fields.Monetary(compute='_compute_unpaid_invoice_totals_today', currency_field='currency_try')


    # Week #
    unpaid_invoice_total_week_usd = fields.Monetary(compute='_compute_unpaid_invoice_totals_week', currency_field='currency_usd')
    unpaid_invoice_total_week_eur = fields.Monetary(compute='_compute_unpaid_invoice_totals_week', currency_field='currency_eur')
    unpaid_invoice_total_week_try = fields.Monetary(compute='_compute_unpaid_invoice_totals_week', currency_field='currency_try')
    

    # 2Weeks #
    unpaid_invoice_total_2weeks_usd = fields.Monetary(compute='_compute_unpaid_invoice_totals_2weeks', currency_field='currency_usd')
    unpaid_invoice_total_2weeks_eur = fields.Monetary(compute='_compute_unpaid_invoice_totals_2weeks', currency_field='currency_eur')
    unpaid_invoice_total_2weeks_try = fields.Monetary(compute='_compute_unpaid_invoice_totals_2weeks', currency_field='currency_try')
    

    # Month #
    unpaid_invoice_total_usd = fields.Monetary(compute='_compute_unpaid_invoice_totals', currency_field='currency_usd')
    unpaid_invoice_total_eur = fields.Monetary(compute='_compute_unpaid_invoice_totals', currency_field='currency_eur')
    unpaid_invoice_total_try = fields.Monetary(compute='_compute_unpaid_invoice_totals', currency_field='currency_try')
    
    
    # Currency fields for multi-currency support
    currency_usd = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.USD').id, readonly=True)
    currency_eur = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR').id, readonly=True)
    currency_try = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.TRY').id, readonly=True)


    def _get_currency_totals(self, invoices, team):
        """Helper method to sum amounts by currency."""
        total_usd = total_eur = total_try = 0.0
        for invoice in invoices:
            if invoice.currency_id == team.currency_usd:
                total_usd += invoice.amount_due
            elif invoice.currency_id == team.currency_eur:
                total_eur += invoice.amount_due
            elif invoice.currency_id == team.currency_try:
                total_try += invoice.amount_due
        return total_usd, total_eur, total_try


    def _get_date_range(self, weeks=0):
        """Helper method to calculate date range."""
        today = fields.Date.today()
        start_date = (today + date_utils.relativedelta(weeks=weeks)).strftime('%Y-%m-%d')
        return start_date, today


    def _compute_unpaid_invoice_totals_today(self):
        today = fields.Date.today()
        for team in self:
            invoices = self.env['unpaid.invoice'].search([('due_date', '=', today), ('team_id', '=', team.id)])
            team.unpaid_invoice_total_today_usd, team.unpaid_invoice_total_today_eur, team.unpaid_invoice_total_today_try = self._get_currency_totals(invoices, team)


    def _compute_unpaid_invoice_totals_week(self):
        for team in self:
            one_week_ago, today = self._get_date_range(weeks=-1)
            invoices = self.env['unpaid.invoice'].search([('due_date', '>=', one_week_ago), ('due_date', '<', today), ('team_id', '=', team.id)])
            team.unpaid_invoice_total_week_usd, team.unpaid_invoice_total_week_eur, team.unpaid_invoice_total_week_try = self._get_currency_totals(invoices, team)


    def _compute_unpaid_invoice_totals_2weeks(self):
        for team in self:
            two_weeks_ago, one_week_ago = self._get_date_range(weeks=-2), self._get_date_range(weeks=-1)
            invoices = self.env['unpaid.invoice'].search([('due_date', '>=', two_weeks_ago), ('due_date', '<', one_week_ago), ('team_id', '=', team.id)])
            team.unpaid_invoice_total_2weeks_usd, team.unpaid_invoice_total_2weeks_eur, team.unpaid_invoice_total_2weeks_try = self._get_currency_totals(invoices, team)


    def _compute_unpaid_invoice_totals(self):
        """Compute unpaid invoice totals by date range."""
        for team in self:
            # Monthly totals (or any other specific period you need)
            month_ago, two_weeks_ago = self._get_date_range(weeks=-4), self._get_date_range(weeks=-2)
            invoices = self.env['unpaid.invoice'].search([('due_date', '>=', month_ago), ('due_date', '<', two_weeks_ago), ('team_id', '=', team.id)])
            team.unpaid_invoice_total_usd, team.unpaid_invoice_total_eur, team.unpaid_invoice_total_try = self._get_currency_totals(invoices, team)