from odoo import models, fields
from datetime import date

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    label_date = fields.Char(
        default=lambda s: "Today",
        translate=True,
        ) 
    total_count = fields.Integer(compute="_count_records", store=True)
    
    def _count_records(self):
          today = date.today()
          domain = [
            ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '=', today.strftime('%Y-%m-%d')),
                ('partner_id.property_account_receivable_id.code', '=', 120001)
        ]
          self.total_count = self.env['account.move'].search_count(domain)
                
    def action_unpaid_invoice(self):
         action = self.env["ir.actions.actions"]._for_xml_id(
              "unpaid_invoice.action_report_unpaid_invoice_html")
         return action
    