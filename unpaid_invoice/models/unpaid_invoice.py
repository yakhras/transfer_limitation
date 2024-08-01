        # -*- coding: utf-8 -*-

from odoo import models



class UnpaidInvoice(models.AbstractModel):
    _name = 'unpaid.invoice'
    _description = 'Unpaid Invoices Report'

    
    def yaser(self):
        env = self.env['account.move']
        for i in env:
            name = i.name
        return name


