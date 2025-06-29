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
        header_format = workbook.add_format({'bold': True, 'font_size': 10, 'bg_color': '#D9E1F2'})
        wrap_format = workbook.add_format({**font10, 'text_wrap': True, 'align': 'left', 'valign': 'top'})
        title_format = workbook.add_format({'font_size': 16, 'align': 'center', 'valign': 'center', 'bold': True, 'border': 1})
        label_format = workbook.add_format({'align': 'left', 'valign': 'center', 'font_size': 10, 'bold': True})
        date_format = workbook.add_format({'valign': 'left', 'align': 'center','font_size': 10 })
        name_format = workbook.add_format({'align': 'left', 'valign': 'center','font_size': 11 })
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
        worksheet.set_row(17, 15.25)
        worksheet.set_row(18, 45)
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

        company_name = sale_order.company_id.name
        address_line_1 = sale_order.company_id.street2 or ''
        address_line_2 = ", ".join(filter(None, [
            sale_order.company_id.street,
            sale_order.company_id.city,
            sale_order.company_id.zip,
            sale_order.company_id.state_id.name if sale_order.company_id.state_id else None,
        ]))
        address_line_3 = sale_order.company_id.country_id.name if sale_order.company_id.country_id else ''
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
        
        worksheet.merge_range('A7:I7', "PACKING LIST", title_format)

        # # Order Information
        date = sale_order.date_order.strftime('%Y-%m-%d') if sale_order.date_order else ""
        worksheet.write('A8', "Date:", label_format)
        worksheet.write('B8', date, date_format)
        worksheet.write('G8', "Order No:", label_format)
        worksheet.write('H8', sale_order.name, date_format)

        # # Seller and Buyer Information
        worksheet.write('A10', "Seller:", label_format)
        worksheet.merge_range('B10:F10', company_name or "", name_format)
        worksheet.write('G10' , "Buyer:", label_format)
        worksheet.merge_range('H10:I10', sale_order.partner_id.name or "", name_format)
        
        full_address = ", ".join(filter(None, [address_line_1, address_line_2, address_line_3]))
        worksheet.write('A12', "Address:", label_format)
        worksheet.write('B12', address_line_1, date_format)
        worksheet.write('B13', address_line_2, date_format)
        worksheet.write('B14', address_line_3, date_format)

        # buyer_address_parts = filter(None, [
        #     sale_order.partner_shipping_id.street,
        #     sale_order.partner_shipping_id.street2,
        #     sale_order.partner_shipping_id.city,
        #     sale_order.partner_shipping_id.state_id.name if sale_order.partner_shipping_id.state_id else None,
        #     sale_order.partner_shipping_id.zip,
        #     sale_order.partner_shipping_id.country_id.name if sale_order.partner_shipping_id.country_id else None,
        # ])
        # # 
        buyer_address_2 = ", ".join(filter(None, [
            sale_order.partner_shipping_id.street,
            sale_order.partner_shipping_id.city,
            sale_order.partner_shipping_id.state_id.name if sale_order.partner_shipping_id.state_id else None,
        ]))
        worksheet.write('G12', "Address:", label_format)
        worksheet.write('H12', sale_order.partner_shipping_id.street2 or '', date_format)
        worksheet.write('H13', buyer_address_2, date_format)
        worksheet.write('H14', sale_order.partner_shipping_id.country_id.name or '', date_format)

        if sale_order.company_id.phone:
            worksheet.write('A15', "Phone:", label_format)
            worksheet.write('B15', sale_order.company_id.phone or '', date_format)

        if sale_order.partner_id.phone:
            worksheet.write('G15', "Phone:", label_format)
            worksheet.write('H15', sale_order.partner_id.phone or '', date_format)
        


        # # Order Lines Table
        order_lines = sale_order.order_line
        headers = ["Product", "Quantity", "Type", "Net Weight KG", "Gross Weight KG"]
        worksheet.merge_range('A18:E18', headers[0], header_format)
        worksheet.write_row(17, 5, headers[1:], header_format)

        row = 18
        for line in order_lines:
            product_name = line.product_id.display_name or ""
            product_qty = str(line.product_uom_qty)
            packaging_name = line.product_packaging_id.name or ""
            net_weight = str(line.net_weight)
            gross_weight = str(line.gross_weight)

            row_data = [
                product_name,
                product_qty,
                packaging_name,
                net_weight,
                gross_weight
            ]
            worksheet.merge_range(row, 0, row, 4, row_data[0])
            worksheet.write_row(row, 5, row_data[1:])
            row += 1
        # Track max widths (based on header lengths)
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
