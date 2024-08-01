        # -*- coding: utf-8 -*-

from odoo import models, fields



class UnpaidInvoice(models.AbstractModel):
    _name = 'unpaid.invoice'
    _description = 'Unpaid Invoices Report'

    name = fields.Char()
    
    def yaser(self):
        env = self.env['account.move']
        for i in env:
            self.name = i.name
        return self.name


