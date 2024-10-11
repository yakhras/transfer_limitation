from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'   # Inherit the model

    balance = fields.Char()
    balance_id = fields.Boolean()

    @api.onchange('balance_id')
    def on_change_balance_id(self):
        list = sef.get_balance()
        self.balance = self.total_debit(list)

    def get_balance(self):
        # acmvln = self.env['account.move.line'].search([])
        # filter = acmvln.filtered(lambda x: x.partner_id == self.id and reconciled == False)
        ids = []
        for one in self.move_line_ids:
            ids.append(one.debit)
        return ids

    def total_debit(self, list):
        total_debit = 0
        for number in list:
            total_debit += number
        return total_debit

       