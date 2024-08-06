        # -*- coding: utf-8 -*-

from odoo import models, fields
from datetime import datetime



class UnpaidInvoice(models.AbstractModel):
    _name = 'report.unpaid_invoice.unpaid_report'
    _description = 'Unpaid Invoices Report'

    
    # def get_data(self, **kw):
    #     # partners_data = {}
    #     # partner = self.env["res.partner"]
    #     # group_id = partner.id
    #     # group_name = partner.name
    #     # partners_data.update({"id":group_id, "name":group_name})
    #     return {'subjects':['Math', 'English', 'Programming']}
    
    def _get_report_values(self, docids, data=None):
        now = datetime.now()
        domain = [
            ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<', now.strftime('%Y-%m-%d')),
                ('partner_id.property_account_receivable_id.code', '=', '120001')
        ]
        records =[]
        idd = self.env['res.partner'].search([])
        records.extend(i for i in idd)

        invoices = {}
        table = self.env['account.move'].search(domain)
        for t in table:
            t_id = t.id
            t_pr = t.payment_reference
            invoices.update({t_id:{"id":t_id, "pr":t_pr}})

        # match = []
        # for y in records:
        #     for z in invoices:
        #         if y == z:
        #             match.append(z.payment_reference)
        
        return {
            'invoices': invoices,
        }
        