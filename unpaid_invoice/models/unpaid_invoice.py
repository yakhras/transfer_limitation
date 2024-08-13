from odoo import models, fields

class UnpaidInvoice(models.Model):
    _name = 'unpaid.invoice'
    _inherit = 'crm.team'

    def action_unpaid_invoice(self):
         action = self.env["ir.actions.actions"]._for_xml_id(
              "unpaid_invoice.action_report_unpaid_invoice_html")
         return action