from odoo import models, fields

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    def action_unpaid_invoice(self):
         action = self.env["ir.actions.actions"]._for_xml_id(
              "unpaid_invoice.action_report_unpaid_invoice_html")
         return action
    
    def _get_active_id(self):
         actv_id = self.env.context.get('active_id')
         if self.action_unpaid_invoice():
              return actv_id