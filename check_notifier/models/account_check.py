# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date

class AccountCheck(models.Model):
    _inherit = 'account.check'

    
    result_domain = fields.Char(
        string='Result Domain',
        compute='_compute_result_domain',
        store=False
    )

    @api.depends('is_different_currency_equivalent', 'payment_date')
    def _compute_result_domain(self):
        for record in self:
            domain = [
                ('is_different_currency_equivalent', '=', True),
                ('payment_date', '=', record.payment_date)
            ]
            result = self.search(domain)
            record.result_domain = ', '.join(result.mapped('name'))
    
    def process_weekly_checks(self):
        today = date.today()
        weekday = today.weekday()  # Monday = 0, Sunday = 6

        # Get all relevant checks
        checks = self.search([
            ('is_different_currency_equivalent', '=', True),
            ('payment_date', '=', today)
        ])

        queue_obj = self.env['check.report.queue']

        # Step 1: Categorize today's checks
        for check in checks:
            existing = queue_obj.search([('check_id', '=', check.id)])
            if existing:
                continue  # Already queued

            if weekday in [5, 6]:  # Saturday or Sunday
                queue_obj.create({
                    'check_id': check.id,
                    'status': 'holiday'
                })
            else:
                queue_obj.create({
                    'check_id': check.id,
                    'status': 'week'
                })

        # Step 2: Monday adjustment
        if weekday == 0:
            holiday_checks = queue_obj.search([('status', '=', 'holiday'), ('emailed', '=', False)])
            for rec in holiday_checks:
                rec.status = 'week'

        # Step 3: Send email if any check is in week list and not emailed
        week_checks = queue_obj.search([('status', '=', 'week'), ('emailed', '=', False)])
        if week_checks:
            # Dummy email for now (implement template logic later)
            check_list = ', '.join(week_checks.mapped('check_id.check_number'))

            # Use mail.mail for now or define template later
            self.env['mail.mail'].create({
                'subject': 'Weekly Check Notification',
                'body_html': f'<p>The following checks are due this week: {check_list}</p>',
                'email_to': 'accounting@example.com',  # Change to dynamic
            }).send()

            # Mark all as emailed
            week_checks.write({'emailed': True})
