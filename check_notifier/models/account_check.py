# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date

class AccountCheck(models.Model):
    _inherit = 'account.check'

    
    result_domain = fields.Char(
        string='Result Domain',
    )

    
    def get_check(self):
        today = date.today()
        all_today_checks = self.env['account.check'].search([
            ('is_different_currency_equivalent', '=', True),
            ('payment_date', '=', '2025-04-20')
        ])
        if all_today_checks:
            return True
        else:
            return False

    def send_email_check_notifier(self):
        self.result_domain = '23569'

                