import io
import base64
from odoo import models
import xlsxwriter

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_export_quant_svl(self):
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        worksheet = workbook.add_worksheet("Quant vs SVL")

        headers = ["Product", "Product ID", "Quantity (Quant)", "Quantity (SVL)", "Value (SVL)"]
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        row = 1
        product_ids = self

        if not product_ids:
            product_ids = self.env['product.product'].search([])

        for product in product_ids:
            quant_qty = sum(
                self.env['stock.quant'].search([
                    ('product_id', '=', product.id)
                ]).mapped('quantity')
            )

            svl_records = self.env['stock.valuation.layer'].search([
                ('product_id', '=', product.id)
            ])
            svl_qty = sum(svl_records.mapped('quantity'))
            svl_value = sum(svl_records.mapped('value'))

            worksheet.write(row, 0, product.display_name)
            worksheet.write(row, 1, product.id)
            worksheet.write(row, 2, quant_qty)
            worksheet.write(row, 3, svl_qty)
            worksheet.write(row, 4, svl_value)
            row += 1

        workbook.close()
        buffer.seek(0)
        file_data = buffer.read()
        buffer.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'product_quant_svl.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(file_data),
            'res_model': self._name,
            'res_id': self.ids[0] if self else False,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
