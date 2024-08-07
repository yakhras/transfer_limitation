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
        partners ={}
        invoices = {}
        table = self.env['account.move'].search(domain)

        for raw in table:
            partner_id = raw.partner_id
            inv_id = raw.id
            inv_pay_ref = raw.payment_reference
            part_name = partner_id.name
            part_id = partner_id.id
            invoices.update({inv_id: {"id":part_id, "pr":inv_pay_ref, "pn":part_name}})
            partners.update({partner_id:{"id":part_id, "name":part_name}})
        
        match = {j['id']:
                 {
                     z:{"pay_ref":d['pr'], "part_nm":d['pn']}
                     for (z,d) in invoices.items()
                     if j['id']==d['id']
                 }
                 for (i,j) in partners.items()
                }
        
        return {
            'invoices': invoices,
            'partners': partners,
            'match': match,
        }
        