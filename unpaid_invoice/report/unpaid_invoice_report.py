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
        partner = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<', now.strftime('%Y-%m-%d')),
                ('partner_id.property_account_receivable_id.code', '=', '120001')
        ])
        subjects = {}
        for part in partner:
            subjects.update({"id":part.partner_id.id, "name": part.partner_id.name})
        domain = [
            ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<', now.strftime('%Y-%m-%d')),
                ('partner_id.property_account_receivable_id.code', '=', '120001')
        ]
        invoices = self.env['account.move'].read_group(domain=domain, fields=["partner_id"], groupby=["partner_id"])
        results =[]
        results.extend(inv for inv in invoices)
        return {
            'subjects': subjects,
            'results': results,
        }
        