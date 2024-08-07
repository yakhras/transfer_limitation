        # -*- coding: utf-8 -*-

from odoo import models, fields
from datetime import datetime



class UnpaidInvoice(models.AbstractModel):
    _name = 'report.unpaid_invoice.unpaid_report'
    _description = 'Unpaid Invoices Report'

    
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
            t_name = partner_id.name
            part_id = partner_id.id
            invoices.update({t_id: {"id":part_id, "pr":t_pr, "pn":t_name}})

        match = {}
        for r in records[r]['id']:
            for v in invoices[v]['id']:
                if r == v:
                    match.update({v:{"id":invoices[v]['pr']}})
        
        return {
            'invoices': invoices,
            'records': records,
            'match': match,
        }
        