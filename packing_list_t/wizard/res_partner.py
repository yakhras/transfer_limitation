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
        partner_id = self.env.context.get("active_ids")
        order_ids = self.env["sale.order"].search(
            [
                ("partner_id", "in", partner_id),
                ("date_order", ">=", self.start_date),
                ("date_order", "<", self.end_date),
            ]
        )
        order_lines = self.env["sale.order.line"].search(
            [("order_id", "in", order_ids.ids)]
        )
        products = []
        values = []
        total_quantity = 0
        total_amount = 0

        index = 1
        for order_line in order_lines:
            if order_line.product_id.id not in products:
                products.append(order_line.product_id.id)
                product_order_lines = order_lines.filtered(
                    lambda line: line.product_id.id == order_line.product_id.id
                )
                total_qty = sum(product_order_lines.mapped("product_uom_qty"))
                subtotal = sum(product_order_lines.mapped("price_subtotal"))
                order_line_data = {
                    "srno": index,
                    "product": order_line.product_template_id.name,
                    "quantity": total_qty,
                    "subtotal": subtotal,
                }
                index += 1
                values.append(order_line_data)
                total_quantity = sum([value["quantity"] for value in values])
                total_amount = sum([value["subtotal"] for value in values])
        return self.env.ref(
            "cr_partner_sale_excel_report.action_report_partner"
        ).report_action(
            self,
            data={
                "product_lines": values,
                "date_start": self.start_date,
                "date_end": self.end_date,
                "partner": order_ids.partner_id.name,
                "q_total": total_quantity,
                "s_total": total_amount,
            },
        )

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
        font10 = {'font_size': 11}
        font10_format = workbook.add_format(font10)
        border_format = workbook.add_format({'border': 1, **font10})
        header_format = workbook.add_format({'border': 1, 'bold': True, **font10})
        wrap_format = workbook.add_format({'font_size': 11, 'text_wrap': True, 'align': 'left', 'valign': 'top'})
        merge_format = workbook.add_format({'font_size': 11,'align': 'left','valign': 'top'})


        # Header and Footer
        logo_path = sale_order.company_id.logo
        logo_data = base64.b64decode(logo_path)
        tmp_logo_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp_logo_file.write(logo_data)
        tmp_logo_file.close()
        worksheet.set_header(
            '&L%s&R&G' % left_header_content,
            {
                'image_right': tmp_logo_file.name,
                'image_right_height': 40,
            }
        )

        footer_address = sale_order.company_id.street2 or ''
        if sale_order.company_id.street:
            footer_address += ', ' + sale_order.company_id.street
        if sale_order.company_id.city:
            footer_address += ', ' + sale_order.company_id.city
        if sale_order.company_id.state_id:
            footer_address += ', ' + sale_order.company_id.state_id.name
        if sale_order.company_id.country_id:
            footer_address += ', ' + sale_order.company_id.country_id.name
        worksheet.set_footer(
            '&LPage &P'
            '&C%s'
            '&R%s' % (footer_address, sale_order.company_id.vat or '')
        )

        # Seller and Buyer Information
        row = 13  
        col_seller = 1  
        col_buyer = 4   
        worksheet.write(row, col_seller, "Seller:", font10_format)
        worksheet.write(row, col_buyer, "Buyer:", font10_format)
        row += 1
        worksheet.write(row, col_seller, sale_order.company_id.name or "", font10_format)
        worksheet.write(row, col_buyer, sale_order.partner_id.name or "", font10_format)
        row += 1
        seller_address_parts = filter(None, [
            sale_order.company_id.street,
            sale_order.company_id.street2,
            sale_order.company_id.city,
            sale_order.company_id.state_id.name if sale_order.company_id.state_id else None,
            sale_order.company_id.zip,
            sale_order.company_id.country_id.name if sale_order.company_id.country_id else None,
        ])
        seller_address = ", ".join(seller_address_parts)
        left_header_content = f"&B&14{sale_order.company_id.name}\n{seller_address}"
        buyer_address_parts = filter(None, [
            sale_order.partner_shipping_id.street,
            sale_order.partner_shipping_id.street2,
            sale_order.partner_shipping_id.city,
            sale_order.partner_shipping_id.state_id.name if sale_order.partner_shipping_id.state_id else None,
            sale_order.partner_shipping_id.zip,
            sale_order.partner_shipping_id.country_id.name if sale_order.partner_shipping_id.country_id else None,
        ])
        worksheet.write(row, col_seller, ", ".join(seller_address_parts), wrap_format)
        worksheet.merge_range(row, col_buyer, row, col_buyer + 1, ", ".join(buyer_address_parts), wrap_format)

        # worksheet.write(row, col_buyer, ", ".join(buyer_address_parts), wrap_format)
        row += 1
        worksheet.write(row, col_seller, f"Phone: {sale_order.company_id.phone or ''}", font10_format)
        worksheet.write(row, col_buyer, f"Phone: {sale_order.partner_id.phone or ''}", font10_format)

        # Order Information
        date = sale_order.date_order.strftime('%Y-%m-%d') if sale_order.date_order else ""
        worksheet.write('B11', f"Date: {date}", font10_format)
        worksheet.write('E11', f"Order No: {sale_order.name}", font10_format)

        # Order Lines Table
        order_lines = sale_order.order_line
        headers = ["Product", "Quantity", "Type", "Net Weight KG", "Gross Weight KG"]
        worksheet.write_row(19, 1, headers, header_format)

        # Track max widths (based on header lengths)
        col_widths = [len(h) for h in headers]

        for idx, line in enumerate(order_lines, start=20):
            data = [
                line.product_id.display_name or "",
                str(line.product_uom_qty),
                line.product_packaging_id.name or "",
                str(line.net_weight),
                str(line.gross_weight)
            ]
            for col, val in enumerate(data, start=1):
                worksheet.write(idx, col, val, border_format)
                col_widths[col - 1] = max(col_widths[col - 1], len(val))

        # Set column widths with padding
        for i, width in enumerate(col_widths, start=1):
            worksheet.set_column(i, i, width + 2)

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
