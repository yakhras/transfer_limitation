# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date

class AccountCheck(models.Model):
    _inherit = 'account.check'

    
    result_domain = fields.Char(
        string='Result Domain',
        compute='_compute_result_domain',
    )

    
    def _compute_result_domain(self):
        today = date.today()
        all_today_checks = self.env['account.check'].search([
            ('is_different_currency_equivalent', '=', True),
            ('payment_date', '=', today)
        ])
        for record in self:
            record.result_domain = today.strftime('%Y-%m-%d')