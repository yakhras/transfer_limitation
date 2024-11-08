from odoo import models, fields, api
from odoo.tools import date_utils
from datetime import date, timedelta

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    today = date.today()

    unpaid_invoice_fields = {
        'unpaid_invoice_total_today_usd': ('today', 0, 'usd'),
        'unpaid_invoice_total_today_eur': ('today', 0, 'eur'),
        'unpaid_invoice_total_today_try': ('today', 0, 'try'),
        'unpaid_invoice_total_week_usd': ('week', -1, 'usd'),
        'unpaid_invoice_total_week_eur': ('week', -1, 'eur'),
        'unpaid_invoice_total_week_try': ('week', -1, 'try'),
        'unpaid_invoice_total_2weeks_usd': ('week', -2, 'usd'),
        'unpaid_invoice_total_2weeks_eur': ('week', -2, 'eur'),
        'unpaid_invoice_total_2weeks_try': ('week', -2, 'try'),
        'unpaid_invoice_total_usd': ('week', -4, 'usd'),
        'unpaid_invoice_total_eur': ('week', -4, 'eur'),
        'unpaid_invoice_total_try': ('week', -4, 'try'),
    }

    currency_usd = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.USD').id, readonly=True)
    currency_eur = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR').id, readonly=True)
    currency_try = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.TRY').id, readonly=True)

    for field_name, (period, offset, currency) in unpaid_invoice_fields.items():
        locals()[field_name] = fields.Monetary(
            compute=lambda self, period=period, offset=offset, currency=currency: self._compute_unpaid_invoice_totals(period, offset, currency),
            currency_field=f'currency_{currency}'
        )

    def _get_currency_totals(self, invoices, team):
        total_usd = total_eur = total_try = 0.0
        for invoice in invoices:
            if invoice.currency_id == team.currency_usd:
                total_usd += invoice.amount_due
            elif invoice.currency_id == team.currency_eur:
                total_eur += invoice.amount_due
            elif invoice.currency_id == team.currency_try:
                total_try += invoice.amount_due
        return total_usd, total_eur, total_try

    def _get_date_range(self, offset=0, period='today'):
        if period == 'today':
            return self.today, self.today + timedelta(days=1)
        elif period == 'week':
            start_date = self.today + timedelta(weeks=offset)
            end_date = start_date + timedelta(weeks=1)
            return start_date, end_date

    def _get_invoices_by_date_range(self, team_id, start_date=None, end_date=None):
        domain = [('team_id', '=', team_id)]
        if start_date:
            domain.append(('due_date', '>=', start_date))
        if end_date:
            domain.append(('due_date', '<', end_date))
        return self.env['unpaid.invoice'].search(domain)

    def _compute_unpaid_invoice_totals(self, period, offset, currency):
        for team in self:
            start_date, end_date = self._get_date_range(offset, period)
            invoices = self._get_invoices_by_date_range(team.id, start_date, end_date)
            totals = self._get_currency_totals(invoices, team)
            currency_field = f'unpaid_invoice_total_{period}_{currency}'
            setattr(team, currency_field, totals[{'usd': 0, 'eur': 1, 'try': 2}[currency]])





# from odoo.tools import date_utils
# from odoo import models, fields
# from datetime import date

# class CrmTeam(models.Model):
#     _inherit = 'crm.team'

#     today = date.today()

#     # Define the dictionary with field names as keys and compute methods as values
#     unpaid_invoice_fields = {
#         'unpaid_invoice_total_today_usd': '_compute_unpaid_invoice_totals_today',
#         'unpaid_invoice_total_today_eur': '_compute_unpaid_invoice_totals_today',
#         'unpaid_invoice_total_today_try': '_compute_unpaid_invoice_totals_today',
#         'unpaid_invoice_total_week_usd': '_compute_unpaid_invoice_totals_week',
#         'unpaid_invoice_total_week_eur': '_compute_unpaid_invoice_totals_week',
#         'unpaid_invoice_total_week_try': '_compute_unpaid_invoice_totals_week',
#         'unpaid_invoice_total_2weeks_usd': '_compute_unpaid_invoice_totals_2weeks',
#         'unpaid_invoice_total_2weeks_eur': '_compute_unpaid_invoice_totals_2weeks',
#         'unpaid_invoice_total_2weeks_try': '_compute_unpaid_invoice_totals_2weeks',
#         'unpaid_invoice_total_usd': '_compute_unpaid_invoice_totals',
#         'unpaid_invoice_total_eur': '_compute_unpaid_invoice_totals',
#         'unpaid_invoice_total_try': '_compute_unpaid_invoice_totals',
#     }
    
#     # Currency fields for multi-currency support
#     currency_usd = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.USD').id, readonly=True)
#     currency_eur = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.EUR').id, readonly=True)
#     currency_try = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.TRY').id, readonly=True)

#     # Dynamically create the field for testing
#     for field_name, compute_method in unpaid_invoice_fields.items():
#         locals()[field_name] = fields.Monetary(compute=compute_method, currency_field=f'currency_{field_name[-3:]}')

    

#     def _get_currency_totals(self, invoices, team):
#         """Helper method to sum amounts by currency."""
#         total_usd = total_eur = total_try = 0.0
#         for invoice in invoices:
#             if invoice.currency_id == team.currency_usd:
#                 total_usd += invoice.amount_due
#             elif invoice.currency_id == team.currency_eur:
#                 total_eur += invoice.amount_due
#             elif invoice.currency_id == team.currency_try:
#                 total_try += invoice.amount_due
#         return total_usd, total_eur, total_try


#     def _get_date_range(self, weeks=0):
#         """Helper method to calculate date range."""
#         start_date = self.today + date_utils.relativedelta(weeks=weeks)  # Apply relativedelta
#         return start_date
    

#     def _get_invoices_by_date_range(self, team_id, start_date=None, end_date=None):
#         """Fetch unpaid invoices within a specified date range for a given team.
        
#         :param team_id: Sales team ID
#         :param start_date: Start of the due_date range (inclusive)
#         :param end_date: End of the due_date range (exclusive)
#         :return: Recordset of unpaid.invoice matching the date range and team
#         """
#         domain = [('team_id', '=', team_id)]
        
#         # Set due_date range based on provided dates
#         if start_date:
#             domain.append(('due_date', '>=', start_date))
#         if end_date:
#             domain.append(('due_date', '<', end_date))
        
#         return self.env['unpaid.invoice'].search(domain)
    

#     def _compute_unpaid_invoice_totals_today(self):
#         for team in self:
#             invoices = self.env['unpaid.invoice'].search([('due_date', '=', self.today), ('team_id', '=', team.id)])
#             team.unpaid_invoice_total_today_usd, team.unpaid_invoice_total_today_eur, team.unpaid_invoice_total_today_try = self._get_currency_totals(invoices, team)


#     def _compute_unpaid_invoice_totals_week(self):
#         for team in self:
#             one_week_ago = self._get_date_range(weeks=-1)
#             invoices = self._get_invoices_by_date_range(team_id=team.id, start_date=one_week_ago, end_date=self.today)
#             team.unpaid_invoice_total_week_usd, team.unpaid_invoice_total_week_eur, team.unpaid_invoice_total_week_try = self._get_currency_totals(invoices, team)


#     def _compute_unpaid_invoice_totals_2weeks(self):
#         for team in self:
#             two_weeks_ago, one_week_ago = self._get_date_range(weeks=-2), self._get_date_range(weeks=-1)
#             invoices = self._get_invoices_by_date_range(team_id=team.id, start_date=two_weeks_ago, end_date=one_week_ago)
#             team.unpaid_invoice_total_2weeks_usd, team.unpaid_invoice_total_2weeks_eur, team.unpaid_invoice_total_2weeks_try = self._get_currency_totals(invoices, team)


#     def _compute_unpaid_invoice_totals(self):
#         for team in self:
#             month_ago, two_weeks_ago = self._get_date_range(weeks=-4), self._get_date_range(weeks=-2)
#             invoices = self._get_invoices_by_date_range(team_id=team.id, start_date=month_ago, end_date=two_weeks_ago)
#             team.unpaid_invoice_total_usd, team.unpaid_invoice_total_eur, team.unpaid_invoice_total_try = self._get_currency_totals(invoices, team)