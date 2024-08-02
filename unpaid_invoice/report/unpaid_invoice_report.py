        # -*- coding: utf-8 -*-

from odoo import models, fields



class UnpaidInvoice(models.AbstractModel):
    _name = 'report.unpaid_invoice.unpaid_report'
    _description = 'Unpaid Invoices Report'

    
    def get_data(self, **kw):
        # partners_data = {}
        # partner = self.env["res.partner"]
        # group_id = partner.id
        # group_name = partner.name
        # partners_data.update({"id":group_id, "name":group_name})
        return {'subjects':['Math', 'English', 'Programming']}
    
    # def get_value(self, data):
    #     partner_ids = data["partner_ids"]
    #     partners_data = self.get_data(partner_ids)
    #     return{
    #         "partners_data": partners_data
    #     }
        
    


