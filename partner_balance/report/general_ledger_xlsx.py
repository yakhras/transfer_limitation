from odoo import models, api
import base64
from io import BytesIO
import xlsxwriter

class GeneralLedgerXslx(models.AbstractModel):
    _name = "report.partner_balance.xlsx_report"
    _description = "Partner Balance XLSX Report"

    
    def button_export_xlsx(self):
        # Create an in-memory output file
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Sheet1")

        # (Optional) Write a title or header, or leave completely blank
        worksheet.write(0, 0, "This is an empty XLSX file")

        workbook.close()
        output.seek(0)

        xlsx_data = output.read()
        output.close()

        # Encode to base64 and prepare for download
        attachment = self.env['ir.attachment'].create({
            'name': 'partner_balance.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(xlsx_data),
            'res_model': 'ir.ui.view',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        download_url = f'/web/content/{attachment.id}?download=true'

        return {
            'type': 'ir.actions.act_url',
            'url': download_url,
            'target': 'self',
        }
