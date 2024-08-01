        # -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, timedelta



class UnpaidInvoice(models.Model):
    _name = 'unpaid.invoice'
    _description = 'Unpaid Invoices Report'

    
    def yaser(self):
        env = self.env['account.move']
        for i in env:
            name = i.name
        return name


