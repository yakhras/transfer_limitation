# -*- coding: utf-8 -*-
# Part of Creyox Technologies

from odoo import api, fields, models
from io import BytesIO
import xlsxwriter
import base64

class ResPartnerSaleReport(models.TransientModel):
    _name = "res.partner.wizard"
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
        values = []
        products = []
        fp = BytesIO()
        file_name = "sale.xlsx"
        workbook = xlsxwriter.Workbook(fp, {"in_memory": True})
        worksheet = workbook.add_worksheet()
        order_line_header = ["SR NO.", "Product", "Quantity", "Sub Total"]
        center_format1 = workbook.add_format(
            {"align": "center", "valign": "vcenter", "bold": True}
        )
        center_format1.set_bg_color("#D3D3D3")
        center_format2 = workbook.add_format(
            {"align": "center", "valign": "vcenter", "bold": True}
        )
        center_format2.set_bg_color("#48AAAD")
        center_format3 = workbook.add_format(
            {"align": "center", "valign": "vcenter", "bold": True}
        )
        date = workbook.add_format(
            {"align": "center", "valign": "vcenter", "bold": True}
        )
        date.set_bg_color("#ADD8E6")
        bold = workbook.add_format({"bold": True})
        worksheet.set_column(1, 1, 20)
        worksheet.set_column(1, 3, 10)
        for order_line in order_lines:
            if order_line.product_id.id not in products:
                products.append(order_line.product_id.id)
                product_order_lines = order_lines.filtered(
                    lambda line: line.product_id.id == order_line.product_id.id
                )
                total_qty = sum(product_order_lines.mapped("product_uom_qty"))
                subtotal = sum(product_order_lines.mapped("price_subtotal"))
                order_line_data = {
                    "product": order_line.product_template_id.name,
                    "quantity": total_qty,
                    "subtotal": subtotal,
                }
                values.append(order_line_data)

        worksheet.merge_range(
            "A1:G3", "Sale Report: %s" % order_ids.company_id.name, center_format1
        )
        worksheet.merge_range(
            "A6:F7", "Time Period: %s -- %s" % (self.start_date, self.end_date), date
        )
        worksheet.merge_range("A9:C10", order_ids.partner_id.name, center_format2)
        worksheet.write_row(11, 0, order_line_header, center_format3)
        row = 12
        index = 1
        for val in values:
            worksheet.write(row, 0, index)
            worksheet.write(row, 1, val.get("product"))
            worksheet.write(row, 2, val.get("quantity"))
            worksheet.write(row, 3, val.get("subtotal"))
            row += 1
            index += 1

        worksheet.write_formula("C17", "{=SUM(C13:C15)}", bold)
        worksheet.write_formula("D17", "{=SUM(D13:D14)}", bold)

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
