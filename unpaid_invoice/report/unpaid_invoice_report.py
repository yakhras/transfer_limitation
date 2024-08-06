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

        records ={}
        idd = self.env['res.partner'].search([])
        for i in idd:
            i_id = i.id
            i_name = i.name
            records.update({i: {"id":i_id, "name":i_name}})

        invoices = {}
        table = self.env['account.move'].search(domain)
        for t in table:
            partner_id = t.partner_id
            t_id = t.id
            t_pr = t.payment_reference
            invoices.update({partner_id: {"id":t_id, "pr":t_pr}})

        match = {}
        for r in records.keys():
            for v in invoices.keys():
                if r == v:
                    match.update({"dn":r})
        
        return {
            'invoices': invoices,
            'records': records,
            'match': match,
        }
        