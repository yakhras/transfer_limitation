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
            ('payment_date', '=', today)
        ])
        return checks

    def update_result_domain_for_matching_checks(self):
        template = self.env.ref('check_notifier.check_notifier')
        matching_checks = self.get_today_currency_check_records()
        for check in matching_checks:
            template.send_mail(check.id, force_send=True)
            check.result_domain = ', '.join(matching_checks.mapped('name'))

    def send_email_check_notifier(self):
        self.update_result_domain_for_matching_checks()


                