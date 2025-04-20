# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date

class AccountCheck(models.Model):
    _inherit = 'account.check'

    
    result_domain = fields.Char(
        string='Result Domain',
    )

    
    def get_today_currency_check_records(self):
        today = date.today()
        checks = self.search([
            ('is_different_currency_equivalent', '=', True),
            ('payment_date', '=', "2025-04-28")
        ])
        return checks

    def update_result_domain_for_matching_checks(self):
        template = self.env.ref('check_notifier.check_notifier')
        matching_checks = self.get_today_currency_check_records()
        if matching_checks:
        # Send the email ONCE, for the first check (or just to trigger the template logic)
            template.send_mail(matching_checks[0].id, force_send=True)

    def send_email_check_notifier(self):
        self.update_result_domain_for_matching_checks()


                