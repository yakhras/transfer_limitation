from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'   # Inherit the model

    balance = fields.Float(compute="get_balance")
    

    def get_balance(self):
        for rec in self:
            rec.balance = rec.compute_balance()
        

    def compute_balance(self):
        for rec in self:
            credit = rec.get_credits()
            total_credits = rec.total_credit(credit)
            debit = rec.get_debits()
            total_debits = rec.total_debit(debit)
            balance = round(total_debits - total_credits, 2)
        return balance

    def get_debits(self):
        domain = [('full_reconcile_id', '=', False), ('balance', '!=', 0), ('account_id.reconcile', '=', True)]
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
        domain = [('full_reconcile_id', '=', False), ('balance', '!=', 0), ('account_id.reconcile', '=', True)]
        ids = []
        for one in self.move_line_ids.filtered_domain(domain):
            ids.append(one.credit)
        return ids

    def total_credit(self, list):
        total_credit = 0
        for number in list:
            total_credit += number
        return round(total_credit, 2)
