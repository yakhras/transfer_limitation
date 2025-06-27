# -*- coding: utf-8 -*-

from odoo import fields, models
from io import BytesIO
import xlsxwriter
import base64
import tempfile
from PIL import Image

class ResPartnerSaleReport(models.TransientModel):
    _name = "sale.order.wizard"
    _description = "Sale Report Wizard for Res Partner"

    start_date = fields.Date(string="Start Date:")
    end_date = fields.Date(string="End Date:")

    def action_generate_pdf_report(self):
        self.env['res.partner'].action_view_move_line_report()
        # partner_id = self.env.context.get("active_ids")
        # order_ids = self.env["sale.order"].search(
        #     [
        #         ("partner_id", "in", partner_id),
        #         ("date_order", ">=", self.start_date),
        #         ("date_order", "<", self.end_date),
        #     ]
        # )
        # order_lines = self.env["sale.order.line"].search(
        #     [("order_id", "in", order_ids.ids)]
        # )
        # products = []
        # values = []
        # total_quantity = 0
        # total_amount = 0

        # index = 1
        # for order_line in order_lines:
        #     if order_line.product_id.id not in products:
        #         products.append(order_line.product_id.id)
        #         product_order_lines = order_lines.filtered(
        #             lambda line: line.product_id.id == order_line.product_id.id
        #         )
        #         total_qty = sum(product_order_lines.mapped("product_uom_qty"))
        #         subtotal = sum(product_order_lines.mapped("price_subtotal"))
        #         order_line_data = {
        #             "srno": index,
        #             "product": order_line.product_template_id.name,
        #             "quantity": total_qty,
        #             "subtotal": subtotal,
        #         }
        #         index += 1
        #         values.append(order_line_data)
        #         total_quantity = sum([value["quantity"] for value in values])
        #         total_amount = sum([value["subtotal"] for value in values])
        # return self.env.ref(
        #     "cr_partner_sale_excel_report.action_report_partner"
        # ).report_action(
        #     self,
        #     data={
        #         "product_lines": values,
        #         "date_start": self.start_date,
        #         "date_end": self.end_date,
        #         "partner": order_ids.partner_id.name,
        #         "q_total": total_quantity,
        #         "s_total": total_amount,
        #     },
        # )

    def action_generate_excel_report(self):
        ctx = self.env.context.get("active_ids")
        id = int(str(ctx[0]))
        sale_order = self.env["sale.order"].browse(id)
        fp = BytesIO()
        file_name = "Packing List.xlsx"

        # Create an Excel workbook and worksheet
        workbook = xlsxwriter.Workbook(fp, {"in_memory": True})
        worksheet = workbook.add_worksheet(sale_order.name)
        worksheet.set_paper(9)
        worksheet.set_margins(left=0.7, right=0.7, top=0.75, bottom=0.75)
        worksheet.fit_to_pages(1, 0)

        # Styles
        font10 = {'font_size': 18}
        font10_format = workbook.add_format(font10)
        bold_format = workbook.add_format({'align': 'left', 'valign': 'top', 'bold': True, **font10})
        border_format = workbook.add_format({'border': 1, **font10})
        header_format = workbook.add_format({'border': 1, 'bold': True, **font10})
        wrap_format = workbook.add_format({**font10, 'text_wrap': True, 'align': 'left', 'valign': 'top'})
        title_format = workbook.add_format({'font_size': 16, 'align': 'center', 'valign': 'center', 'bold': True, 'border': 1})
        date_format = workbook.add_format({'align': 'left', 'valign': 'center', **font10})
        worksheet.set_column('A:A', 8.43)
        worksheet.set_column('B:B', 8.43)
        worksheet.set_column('C:C', 8.43)
        worksheet.set_column('D:D', 8.43)
        worksheet.set_column('E:E', 10.71)
        worksheet.set_column('F:F', 8.43)
        worksheet.set_column('G:G', 10.29)
        worksheet.set_column('H:H', 14.29)
        worksheet.set_column('I:I', 14.29)  
        worksheet.set_row(6, 21.5)
        worksheet.set_row(7, 17)
        worksheet.set_row(8, 9.5)
        worksheet.set_row(9, 27.5)
        worksheet.set_row(10, 9.5)
        worksheet.set_row(11, 15.25)
        worksheet.set_row(12, 15.25)
        worksheet.set_row(13, 15.25)
        worksheet.set_row(14, 15.25)
        worksheet.set_row(16, 15.25)
        worksheet.set_row(17, 9.5)
        worksheet.set_row(18, 15.25)
        worksheet.set_row(19, 45)
        worksheet.set_row(20, 45)
        worksheet.set_row(21, 45)
        worksheet.set_row(22, 45)
        worksheet.set_row(23, 45)



        # # Header and Footer
        # logo_path = sale_order.company_id.logo
        # logo_data = base64.b64decode(logo_path)
        # tmp_logo_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        # tmp_logo_file.write(logo_data)
        # tmp_logo_file.close()

        # company_name = sale_order.company_id.name
        # address_line_1 = sale_order.company_id.street2 or ''
        # address_line_2 = ", ".join(filter(None, [
        #     sale_order.company_id.street,
        #     sale_order.company_id.city,
        #     sale_order.company_id.zip,
        #     sale_order.company_id.state_id.name if sale_order.company_id.state_id else None,
        # ]))
        # address_line_3 = sale_order.company_id.country_id.name if sale_order.company_id.country_id else ''
        # left_header_content = f"&B&16{company_name}&B0&11\n{address_line_1}\n{address_line_2}\n{address_line_3}"

        # worksheet.set_header(
        #     '&L%s&R&G' % left_header_content,
        #     {
        #         'image_right': tmp_logo_file.name,
        #     }
        # )

        # footer_address = sale_order.company_id.website
        # worksheet.set_footer(
        #     '&LPage &P'
        #     '&C%s'
        #     '&R%s' % (footer_address, sale_order.company_id.vat or '')
        # )

        # # Title
        
        worksheet.merge_range('A9:I9', "PACKING LIST", title_format)

        # # Order Information
        # date = sale_order.date_order.strftime('%Y-%m-%d') if sale_order.date_order else ""
        # worksheet.write('A12', "Date:", bold_format)
        # worksheet.write('B12', date, date_format)
        # worksheet.write('G12', "Order No:", bold_format)
        # worksheet.write('H12', sale_order.name, date_format)

        # # Seller and Buyer Information
        # row = 14 
        # col_buyer = 6 
        # col_seller = 0 
        # worksheet.write(row, col_seller, "Seller:", bold_format)
        # worksheet.write(row, col_seller + 1, company_name or "", font10_format)
        # worksheet.write(row, col_buyer , "Buyer:", bold_format)
        # worksheet.write(row, col_buyer + 1, sale_order.partner_id.name or "", font10_format)
        # row += 1
        
        # full_address = ", ".join(filter(None, [address_line_3, address_line_2, address_line_1]))
        # worksheet.write(row, col_seller, "Address:", bold_format)
        # worksheet.write(row, col_seller + 1, full_address, wrap_format)

        # buyer_address_parts = filter(None, [
        #     sale_order.partner_shipping_id.street,
        #     sale_order.partner_shipping_id.street2,
        #     sale_order.partner_shipping_id.city,
        #     sale_order.partner_shipping_id.state_id.name if sale_order.partner_shipping_id.state_id else None,
        #     sale_order.partner_shipping_id.zip,
        #     sale_order.partner_shipping_id.country_id.name if sale_order.partner_shipping_id.country_id else None,
        # ])
        # # 
        # worksheet.write(row, col_buyer, "Address:", bold_format)
        # # worksheet.write(row, col_buyer+1, ", ".join(buyer_address_parts), wrap_format)
        # buyer_address = ", ".join(buyer_address_parts)
        # worksheet.merge_range('D16:F16', buyer_address, wrap_format)

        # row += 1
        # if sale_order.company_id.phone:
        #     worksheet.write(row, col_seller, "Phone:", bold_format)
        #     worksheet.write(row, col_seller + 1, sale_order.company_id.phone or '', font10_format)

        # if sale_order.partner_id.phone:
        #     worksheet.write(row, col_buyer, "Phone:", bold_format)
        #     worksheet.write(row, col_buyer+1, sale_order.partner_id.phone or '', font10_format)
        


        # # Order Lines Table
        # order_lines = sale_order.order_line
        # headers = ["#", "Product", "Quantity", "Type", "Net Weight KG", "Gross Weight KG"]
        # worksheet.write_row(19, 0, headers, header_format)

        # # Track max widths (based on header lengths)
        # col_widths = [len(h) for h in headers]
        # start_row = 20
        # for i, line in enumerate(order_lines, start=1):
        #     data = [
        #         str(i),  # start numbering from 1
        #         line.product_id.display_name or "",
        #         str(line.product_uom_qty),
        #         line.product_packaging_id.name or "",
        #         str(line.net_weight),
        #         str(line.gross_weight)
        #     ]
        #     row_num = start_row + i - 1
        #     for col, val in enumerate(data):
        #         worksheet.write(row_num, col, val, border_format)
        #         col_widths[col - 1] = max(col_widths[col - 1], len(val))

        # # Set column widths with padding
        # for i, width in enumerate(col_widths, start=1):
        #     worksheet.set_column(i, i, width + 2)

        workbook.close()

        attachment_id = self.env["ir.attachment"].create(
            {
                "name": file_name,
                "type": "binary",
                "datas": base64.encodebytes(fp.getvalue()),
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s/%s/datas/%s"
                % ("ir.attachment", attachment_id.id, file_name),
            "target": "self",
        }
