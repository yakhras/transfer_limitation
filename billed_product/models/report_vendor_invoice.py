from odoo import models, fields


class ReportVendorInvoice(models.Model):
    _name = 'report.vendor.invoice'
    _description = 'Vendor Invoice Report'
    _auto = False

    invoice_number = fields.Char(string='Invoice Number')
    invoice_date = fields.Date(string='Invoice Date')
    product_name = fields.Char(string='Product')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Price Unit', currency_field='currency_id', digits=(16, 4))
    subtotal = fields.Float(string='Subtotal', currency_field='currency_id', digits=(16, 4))
    vendor_name = fields.Char(string='Vendor')
    purchase_order_ref = fields.Char(string='PO Reference')
    currency_id = fields.Many2one('res.currency', string='Currency')
    currency_rate = fields.Float(string='Currency Rate', digits=(12, 6))
    warehouse_name = fields.Char(string='Warehouse')



    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS report_vendor_invoice CASCADE;
        """)

        self.env.cr.execute("""
            CREATE VIEW report_vendor_invoice AS (
                SELECT
                    aml.id AS id,
                    am.name AS invoice_number,
                    am.invoice_date AS invoice_date,
                    pt.name AS product_name,
                    aml.product_id AS product_id,
                    aml.quantity AS quantity,
                    aml.price_unit::numeric(16, 6) AS price_unit,
                    aml.price_subtotal::numeric(16, 6) AS subtotal,
                    rp.name AS vendor_name,
                    am.invoice_origin AS purchase_order_ref,
                    am.currency_id AS currency_id,
                    am.currency_rate AS currency_rate,
                    sw.name AS warehouse_name

                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                JOIN res_partner rp ON am.partner_id = rp.id
                JOIN product_product pp ON aml.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id

                LEFT JOIN purchase_order po ON po.name = am.invoice_origin
                LEFT JOIN stock_picking sp ON sp.origin = po.name
                LEFT JOIN stock_picking_type spt ON sp.picking_type_id = spt.id
                LEFT JOIN stock_warehouse sw ON spt.warehouse_id = sw.id

                WHERE am.move_type = 'in_invoice'
                AND aml.display_type IS NULL
            );
        """)

