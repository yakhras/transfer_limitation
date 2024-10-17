from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'   # Inherit the model

    account_check_ids = fields.One2many(
        comodel_name="account.check",
        inverse_name="source_partner_id",
        string="Partner Checks",)
    check_amount = fields.Float('Check Amount')
    
    
# Get Amount Value For Record
    def get_balance(self):
        for rec in self:
            rec.check_amount = rec.compute_amount()
        
# Compute Amount Value For Record
    def compute_amount(self):
        for rec in self:
            amounts = rec.get_amounts()
            total_amount = rec.total_amount(amounts)
        return total_amount


# Get Amount Values For Record
    def get_amounts(self):
        domain = ["reconciled","=",False]
        ids = []
        for one in self.account_check_ids.filtered_domain(domain):
            ids.append(one.amount)
        return ids

# Calculate Total Amount For Record
    def total_amount(self, list):
        total_amount = 0
        for number in list:
            total_amount += number
        return round(total_amount, 2)
