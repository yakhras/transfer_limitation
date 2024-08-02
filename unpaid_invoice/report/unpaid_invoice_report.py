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
        # partner_ids = data["partner_ids"]
        # partners_data = self.get_data(partner_ids)
        now = datetime.now()
        partner = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<', now.strftime('%Y-%m-%d')),
                ('partner_id.property_account_receivable_id.code', '=', '120001')
        ])
        subjects = []
        # for part in partner:
        #     partner_id = part.property_account_receivable_id.code
        #     partner_name = part.name
        subjects.extend(part.payment_reference for part in partner)
        return {
            'subjects': subjects,
        }
        