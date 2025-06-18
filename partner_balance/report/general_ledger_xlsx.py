from odoo import _, models


class GeneralLedgerXslx(models.AbstractModel):
    _name = "report.partner_balance_xlsx"
    _description = "Partner Balance XLSL Report"



    def button_export_xlsx(self):
        """
        Export the partner balance report to XLSX format.
        """
        return