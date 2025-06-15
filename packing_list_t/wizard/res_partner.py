# -*- coding: utf-8 -*-
# Part of Creyox Technologies

from odoo import api, fields, models
from io import BytesIO
import xlsxwriter
import base64

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
        order_lines = sale_order.order_line
        fp = BytesIO()
        file_name = "Packing List.xlsx"

        workbook = xlsxwriter.Workbook(fp, {"in_memory": True})
        worksheet = workbook.add_worksheet(sale_order.name)
        worksheet.set_paper(9)
        worksheet.set_margins(left=0.7, right=0.7, top=0.75, bottom=0.75)  # Inches
        worksheet.set_landscape()  # Optional: For landscape mode
        worksheet.fit_to_pages(1, 0)  # Fit all columns to one page wide, unlimited tall
        worksheet.center_horizontally()
        worksheet.center_vertically()

        worksheet.write(0, 0, sale_order.name)

        address = str(sale_order.company_id.street +', '
                      + sale_order.company_id.city +', '
                      + sale_order.company_id.state_id.name +', '
                      + sale_order.company_id.country_id.name)

        worksheet.merge_range( "B2:E2", sale_order.company_id.name )
        worksheet.merge_range( "B3:E3", sale_order.company_id.street2 )
        worksheet.merge_range( "B4:E4", address )
        worksheet.merge_range( "B5:E5", sale_order.company_id.vat )


        order_line_header = ["SR NO.", "Product", "Quantity", "Type", "Net Weight KG", "Gross Weight KG"]

        
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
