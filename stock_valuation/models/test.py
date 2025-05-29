# import io
# import base64
# from odoo import models
# import xlsxwriter

# class ProductProduct(models.Model):
#     _inherit = 'product.product'

#     def action_export_quant_svl(self):
#         buffer = io.BytesIO()
#         workbook = xlsxwriter.Workbook(buffer)
#         worksheet = workbook.add_worksheet("Quant vs SVL")

#         headers = ["Product", "Product ID", "Quantity (Quant)", "Quantity (SVL)", "Value (SVL)"]
#         for col, header in enumerate(headers):
#             worksheet.write(0, col, header)

#         row = 1
#         product_ids = self

#         if not product_ids:
#             product_ids = self.env['product.product'].search([])

#         for product in product_ids:
#             quant_qty = sum(
#                 self.env['stock.quant'].search([
#                     ('product_id', '=', product.id),
#                     ('location_id.usage', '=', 'internal')
#                 ]).mapped('quantity')
#             )


#             svl_records = self.env['stock.valuation.layer'].search([
#                 ('product_id', '=', product.id)
#             ])
#             svl_qty = sum(svl_records.mapped('quantity'))
#             svl_value = sum(svl_records.mapped('value'))

#             worksheet.write(row, 0, product.display_name)
#             worksheet.write(row, 1, product.id)
#             worksheet.write(row, 2, quant_qty)
#             worksheet.write(row, 3, svl_qty)
#             worksheet.write(row, 4, svl_value)
#             row += 1

#         workbook.close()
#         buffer.seek(0)
#         file_data = buffer.read()
#         buffer.close()

#         attachment = self.env['ir.attachment'].create({
#             'name': 'product_quant_svl.xlsx',
#             'type': 'binary',
#             'datas': base64.b64encode(file_data),
#             'res_model': self._name,
#             'res_id': self.ids[0] if self else False,
#             'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         })

#         return {
#             'type': 'ir.actions.act_url',
#             'url': f'/web/content/{attachment.id}?download=true',
#             'target': 'new',
#         }
import io
import base64
from odoo import models, fields
from odoo.tools import date_utils
import xlsxwriter

class ProductExportQuantSVL(models.TransientModel):
    _name = 'export.quant.svl.wizard'
    _description = 'Export Quant and SVL Summary'

    file_data = fields.Binary("File")
    file_name = fields.Char("Filename")

    def action_export_all_products_quant_svl(self):
        # Prepare output stream and workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet("Product Quant & SVL")

        # Headers
        headers = ['Product', 'Internal Quant Qty', 'SVL Qty', 'SVL Value']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # Data rows
        row = 1
        products = self.env['product.product'].search([])
        for product in products:
            # Internal Quant Quantity
            quant_qty = sum(self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal')
            ]).mapped('quantity'))

            # SVL (internal) — filter by location if needed
            domain = ['|',
                      ('stock_move_id.location_id.usage', '=', 'internal'),
                      ('stock_move_id.location_dest_id.usage', '=', 'internal'),
                      ('product_id', '=', product.id)]
            svl_records = self.env['stock.valuation.layer'].search(domain)
            svl_qty = sum(svl_records.mapped('quantity'))
            svl_value = sum(svl_records.mapped('value'))

            # Write data row
            worksheet.write(row, 0, product.display_name)
            worksheet.write(row, 1, quant_qty)
            worksheet.write(row, 2, svl_qty)
            worksheet.write(row, 3, svl_value)
            row += 1

        workbook.close()
        output.seek(0)

        # Prepare wizard file to download
        file_data = base64.b64encode(output.read())
        filename = 'products_quant_svl_report.xlsx'

        wizard = self.create({
            'file_data': file_data,
            'file_name': filename
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{wizard._name}/{wizard.id}/file_data/{filename}?download=true',
            'target': 'new'
        }

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_export_quant_svl(self):
        return self.env['export.quant.svl.wizard'].create({}).action_export_all_products_quant_svl()
