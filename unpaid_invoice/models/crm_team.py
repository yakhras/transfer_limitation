from odoo.tools import date_utils
from odoo import models, fields, api

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    # Month #
    unpaid_invoice_total_usd = fields.Monetary(
        compute='_compute_unpaid_invoice_totals', currency_field='currency_usd', string="Unpaid Invoices Total (USD)")
    unpaid_invoice_total_eur = fields.Monetary(
        compute='_compute_unpaid_invoice_totals', currency_field='currency_eur', string="Unpaid Invoices Total (EUR)")
    unpaid_invoice_total_try = fields.Monetary(
        compute='_compute_unpaid_invoice_totals', currency_field='currency_try', string="Unpaid Invoices Total (TRY)")
    
    # 2Weeks #
    unpaid_invoice_total_2weeks_usd = fields.Float(
        string='Total Due in USD for Last 2 Weeks', compute='_compute_unpaid_invoice_totals_2weeks')
    unpaid_invoice_total_2weeks_eur = fields.Float(
        string='Total Due in EUR for Last 2 Weeks', compute='_compute_unpaid_invoice_totals_2weeks')
    unpaid_invoice_total_2weeks_try = fields.Float(
        string='Total Due in TRY for Last 2 Weeks', compute='_compute_unpaid_invoice_totals_2weeks')
    
    # Week #
    unpaid_invoice_total_week_usd = fields.Float(
        string='Total Due in USD for Last Week', compute='_compute_unpaid_invoice_totals_week')
    unpaid_invoice_total_week_eur = fields.Float(
        string='Total Due in EUR for Last Week', compute='_compute_unpaid_invoice_totals_week')
    unpaid_invoice_total_week_try = fields.Float(
        string='Total Due in TRY for Last Week', compute='_compute_unpaid_invoice_totals_week')
    
    # Today #
    unpaid_invoice_total_today_usd = fields.Float(
        string='Total Due in USD for Today', compute='_compute_unpaid_invoice_totals_today')
    unpaid_invoice_total_today_eur = fields.Float(
        string='Total Due in EUR for Today', compute='_compute_unpaid_invoice_totals_today')
    unpaid_invoice_total_today_try = fields.Float(
        string='Total Due in TRY for Today', compute='_compute_unpaid_invoice_totals_today')

    # Currency fields for multi-currency support
    currency_usd = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.USD').id, readonly=True)
    currency_eur = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR').id, readonly=True)
    currency_try = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.TRY').id, readonly=True)

   
    def _compute_unpaid_invoice_totals(self):
        today = fields.Date.today()
        month_ago = (today  + date_utils.relativedelta(months=-1)).strftime('%Y-%m-%d')  # Calculate the date 30 days ago
       
        for team in self:
            total_usd = total_eur = total_try = 0.0  # Initialize totals for each currency

            # Retrieve unpaid invoices within the last 30 days for the team
            invoices = self.env['unpaid.invoice'].search([
                ('due_date', '>=', month_ago),
                ('due_date', '<', today),
                ('team_id', '=', team.id)
            ])

            # Sum amounts by currency
            for invoice in invoices:
                if invoice.currency_id == team.currency_usd:
                    total_usd += invoice.amount_due
                elif invoice.currency_id == team.currency_eur:
                    total_eur += invoice.amount_due
                elif invoice.currency_id == team.currency_try:
                    total_try += invoice.amount_due
                # Add more conditions if other currencies are needed.

            # Assign computed values to each field
            team.unpaid_invoice_total_usd = total_usd
            team.unpaid_invoice_total_eur = total_eur
            team.unpaid_invoice_total_try = total_try
            # Set values for other currency fields if they exist.

    def _compute_unpaid_invoice_totals_2weeks(self):
        today = fields.Date.today()
        two_weeks_ago = (today  + date_utils.relativedelta(weeks=-2)).strftime('%Y-%m-%d')  # Calculate the date 15 days ago

        for team in self:
            total_usd = total_eur = total_try = 0.0  # Initialize totals for each currency
            
            domain = [
                ('due_date', '>=', two_weeks_ago),
                ('due_date', '<', today),
                ('team_id', '=', team.id),
            ]
            invoices = self.env['unpaid.invoice'].search(domain)

            # Sum amounts by currency
            for invoice in invoices:
                if invoice.currency_id == team.currency_usd:
                    total_usd += invoice.amount_due
                elif invoice.currency_id == team.currency_eur:
                    total_eur += invoice.amount_due
                elif invoice.currency_id == team.currency_try:
                    total_try += invoice.amount_due

            # Assign totals to the respective fields
            team.unpaid_invoice_total_2weeks_usd = total_usd
            team.unpaid_invoice_total_2weeks_eur = total_eur
            team.unpaid_invoice_total_2weeks_try = total_try


    def _compute_unpaid_invoice_totals_week(self):
        today = fields.Date.today()
        one_week_ago = (today  + date_utils.relativedelta(weeks=-1)).strftime('%Y-%m-%d')  # Calculate the date 7 days ago

        for team in self:
            total_usd = total_eur = total_try = 0.0  # Initialize totals for each currency
            
            domain = [
                ('due_date', '>=', one_week_ago),
                ('due_date', '<', today),
                ('team_id', '=', team.id),
            ]
            invoices = self.env['unpaid.invoice'].search(domain)

            # Sum amounts by currency
            for invoice in invoices:
                if invoice.currency_id == team.currency_usd:
                    total_usd += invoice.amount_due
                elif invoice.currency_id == team.currency_eur:
                    total_eur += invoice.amount_due
                elif invoice.currency_id == team.currency_try:
                    total_try += invoice.amount_due


            # Assign totals to the respective fields
            team.unpaid_invoice_total_week_usd = total_usd
            team.unpaid_invoice_total_week_eur = total_eur
            team.unpaid_invoice_total_week_try = total_try

    def _compute_unpaid_invoice_totals_today(self):
        today = fields.Date.today()

        for team in self:
            total_usd = total_eur = total_try = 0.0  # Initialize totals for each currency
            
            domain = [
                ('due_date', '=', today),
                ('team_id', '=', team.id),
            ]
            invoices = self.env['unpaid.invoice'].search(domain)

            for invoice in invoices:
                if invoice.currency_id == team.currency_usd:
                    total_usd += invoice.amount_due
                elif invoice.currency_id == team.currency_eur:
                    total_eur += invoice.amount_due
                elif invoice.currency_id == team.currency_try:
                    total_try += invoice.amount_due

            # Assign totals to the respective fields
            team.unpaid_invoice_total_today_usd = total_usd
            team.unpaid_invoice_total_today_eur = total_eur
            team.unpaid_invoice_total_today_try = total_try
