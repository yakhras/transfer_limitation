        # -*- coding: utf-8 -*-

from odoo import models, api
from datetime import date


class UnpaidInvoice(models.AbstractModel):
    _name = 'report.unpaid_invoice.unpaid_report'
    _description = 'Unpaid Invoices Report'


    def action_send_email(self):
        print('Hello')

    
    def _get_domain_date(self,docids):
        # Define today
        today = date.today()
        # Define code
        code = 0
        if (docids[0] == 1):
            code = 120001
        elif (docids[0] == 7):
            code = 120005
        elif (docids[0] == 3):
            code = 120002
        else:
            code = 120006
        # Define domain for search
        domain = [
            ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '=', today.strftime('%Y-%m-%d')),
                ('partner_id.property_account_receivable_id.code', '=', code)
        ]
        return domain, today
    
    def _get_report_values(self, docids, data=None):
        # Get domain, today values
        domain, today = self._get_domain_date(docids)
        # Define dictionary for partners
        partners = {}
        # Define dictionary for invoices
        invoices = {}
        # Define table will working with
        table = self.env['account.move'].search(domain)
        # Extract data from table to update the dictionaries
        for raw in table:
            partner_id = raw.partner_id #res.partner object
            inv_id = raw.id #account.move id
            inv_pay_ref = raw.payment_reference #payment reference / invoice number
            inv_due_date = raw.invoice_date_due #.strftime('%Y-%m-%d') #invoice due date
            delay = (today - inv_due_date).days #delay duration from due date to now
            part_name = partner_id.name #partner name
            part_team = partner_id.team_id.name #partner team
            amount = raw.amount_residual
            currency = raw.currency_exchange_currency_id.name
            currency_id = raw.currency_exchange_currency_id
            invoices.update({inv_id: {"id":partner_id, "pr":inv_pay_ref, "pn":part_name,
                                      "dt":inv_due_date, "dd":delay, "pt":part_team,
                                      "ar":amount, "ct":currency, "ci":currency_id, "inv_id":inv_id}}) #update dict with value
            partners.update({partner_id:{"id":partner_id, "name":part_name}}) #update dict with value
            # Define a dictionary contains matched values, will return nested dict
        match = {j['id']:
                {
                    z:{"ref":d['pr'], "partner":d['pn'], "date":d['dt'],
                       "delay":d['dd'], "team":d['pt'], "amount":d['ar'],
                       "currency":d['ct'], "cur_id":d['ci'], "inv_id":d['inv_id']}
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
        