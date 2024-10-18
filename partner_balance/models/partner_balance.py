from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'   # Inherit the model

    balance_value = fields.Float(compute="get_balance_value", readonly=True)
    balance_state = fields.Boolean(compute="get_balance_state", store=True)
    
# Get Balance State For Record
    def get_balance_state(self):
        for rec in self:
            balance_value = rec.compute_balance()
            if balance_value != 0:
                rec.balance_state = True

# Get Balance Value For Record
    def get_balance_value(self):
        for rec in self:
            rec.balance_value = rec.compute_balance()

# Compute Balance Value For Record
    def compute_balance(self):
        for rec in self:
            credit = rec.get_credits()
            total_credits = rec.total_credit(credit)
            debit = rec.get_debits()
            total_debits = rec.total_debit(debit)
            balance = round(total_debits - total_credits, 2)
            return balance

# Get Debit Values For Record
    def get_debits(self):
        domain = [('full_reconcile_id', '=', False), ('balance', '!=', 0), ('account_id.reconcile', '=', True)]
        ids = []
        for one in self.move_line_ids.filtered_domain(domain):
            ids.append(one.debit)
        return ids

# Calculate Total Debits For Record
    def total_debit(self, list):
        total_debit = 0
        for number in list:
            total_debit += number
        return round(total_debit, 2)

# Get Credit Values For Record
    def get_credits(self):
        domain = [('full_reconcile_id', '=', False), ('balance', '!=', 0), ('account_id.reconcile', '=', True)]
        ids = []
        for one in self.move_line_ids.filtered_domain(domain):
            ids.append(one.credit)
        return ids

# Calculate Total Credits For Record
    def total_credit(self, list):
        total_credit = 0
        for number in list:
            total_credit += number
        return round(total_credit, 2)
