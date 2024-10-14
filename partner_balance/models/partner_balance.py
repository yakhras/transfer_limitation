from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'   # Inherit the model

    balance = fields.Char()
    balance_id = fields.Boolean()


    @api.onchange('balance_id')
    def on_change_balance_id(self):
        credit = self.get_credits()
        self.balance = round(self.total_credit(credit), 2)

    def get_debits(self):
        domain = [('full_reconcile_id', '=', False), ('balance', '!=', 0), ('account_id.reconcile', '=', True), ('account_id', '=', self.property_account_receivable_id.code)]
        ids = []
        for one in self.move_line_ids.filtered_domain(domain):
            ids.append(one.debit)
        return ids

    def total_debit(self, list):
        total_debit = 0
        for number in list:
            total_debit += number
        return round(total_debit, 2)

    def get_credits(self):
        domain = [('full_reconcile_id', '=', False), ('balance', '!=', 0), ('account_id.reconcile', '=', True), ('account_id', '=', self.property_account_receivable_id.code)]
        ids = []
        for one in self.move_line_ids.filtered_domain(domain):
            ids.append(one.credit)
        return ids

    def total_credit(self, list):
        total_credit = 0
        for number in list:
            total_credit += number
        return round(total_credit, 2)
