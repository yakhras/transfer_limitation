from odoo import models, fields

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    label_date = fields.Char(
        default=lambda s: _("Tickets"),
        translate=True,
        )

    def action_unpaid_invoice(self):
         action = self.env["ir.actions.actions"]._for_xml_id(
              "unpaid_invoice.action_report_unpaid_invoice_html")
         return action
    