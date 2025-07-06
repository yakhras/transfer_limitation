from odoo import models, fields


class ReportVendorInvoice(models.Model):
    _name = 'report.vendor.invoice'
    _description = 'Vendor Invoice Report'
    _auto = False

    invoice_number = fields.Char(string='Invoice Number')
    invoice_date = fields.Date(string='Invoice Date')
    product_name = fields.Char(string='Product')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Monetary(string='Price Unit', currency_field='currency_id')
    subtotal = fields.Monetary(string='Subtotal', currency_field='currency_id')
    vendor_name = fields.Char(string='Vendor')
    purchase_order_ref = fields.Char(string='PO Reference')
    currency_id = fields.Many2one('res.currency', string='Currency')

    def init(self):
        # Drop the view if it already exists
        self.env.cr.execute("""
            DROP VIEW IF EXISTS report_vendor_invoice CASCADE;
        """)

        # Create the new view
        self.env.cr.execute("""
            CREATE VIEW report_vendor_invoice AS (
                SELECT
                    aml.id AS id,
                    am.name AS invoice_number,
                    am.invoice_date AS invoice_date,
                    pt.name AS product_name,
                    aml.quantity AS quantity,
                    aml.price_unit AS price_unit,
                    aml.price_subtotal AS subtotal,
                    rp.name AS vendor_name,
                    am.invoice_origin AS purchase_order_ref,
                    am.currency_id AS currency_id
                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                JOIN res_partner rp ON am.partner_id = rp.id
                JOIN product_product pp ON aml.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE am.move_type = 'in_invoice'
                AND aml.display_type IS NULL
            );
        """)
