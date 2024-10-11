from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'   # Inherit the model

    balance = fields.Char()
    balance_id = fields.Boolean()

    @api.onchange('balance_id')
    def on_change_balance_id(self):
        self.balance = self.get_balance()

    def get_balance(self):
        # acmvln = self.env['account.move.line'].search([])
        # filter = acmvln.filtered(lambda x: x.partner_id == self.id and reconciled == False)
        ids = []
        total_debit = 0
        for one in self.move_line_ids:
            ids.append(one.debit)
            for id in ids:
                total_debit += id
        return total_debit
       