        # -*- coding: utf-8 -*-

from odoo import models, fields



class UnpaidInvoice(models.AbstractModel):
    _name = 'unpaid.invoice'
    _description = 'Unpaid Invoices Report'

    
    def yaser(self):
        partners_data = {}
        partner = self.env["res.partner"]
        group_id = partner.id
        group_name = partner.name
        partners_data.update({group_id: {"id":group_id, "name":group_name}})
        return partners_data
        
    


