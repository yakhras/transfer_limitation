        # -*- coding: utf-8 -*-

from odoo import models, fields
from datetime import date


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    def action_unpaid_invoice(self):
         action = self.env["ir.actions.actions"]._for_xml_id(
              "unpaid_invoice.action_report_unpaid_invoice_html")
         return action
    
    def _get_active_id(self):
        actv_id = self.env.context.get('active_id')
        return actv_id

class UnpaidInvoice(models.AbstractModel):
    _name = 'report.unpaid_invoice.unpaid_report'
    _description = 'Unpaid Invoices Report'

    
    def _get_report_values(self, docids, data=None):
        # Define today
        today = date.day()
        code = CrmTeam._get_active_id(self)
        # Define domain for search
        domain = []
        if code == 1:
            domain = [
                ('move_type', '=', 'out_invoice'),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ('not_paid', 'partial')),
                    ('invoice_date_due', '<', today.strftime('%Y-%m-%d')),
                    ('partner_id.property_account_receivable_id.code', '=', '120001')
            ]
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
            inv_due_date = raw.invoice_date_due #invoice due date
            delay = today - raw.invoice_date_due #delay duration from due date to now
            part_name = partner_id.name #partner name
            part_team = partner_id.team_id.name #partner team
            invoices.update({inv_id: {"id":partner_id, "pr":inv_pay_ref, "pn":part_name, "dt":inv_due_date, "dd":delay, "pt":part_team}}) #update dict with value
            partners.update({partner_id:{"id":partner_id, "name":part_name}}) #update dict with value
        # Define a dictionary contains matched values, will return nested dict
        match = {j['id']:
                 {
                     z:{"ref":d['pr'], "partner":d['pn'], "date":d['dt'], "delay":d['dd'], "team":d['pt']}
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
        