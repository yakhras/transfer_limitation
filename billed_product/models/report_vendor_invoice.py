from odoo import models, fields, api


class VendorBillReport(models.Model):
    _name = 'vendor.bill.report'
    _description = 'Vendor Bill Report'
    _auto = False

    invoice_id = fields.Many2one('account.move', string='Vendor Bill')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    currency_id = fields.Many2one('res.currency', string='Currency')


    @api.model
    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS vendor_bill_report CASCADE")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW vendor_bill_report AS (
                SELECT
                    aml.id AS id,
                    am.id AS invoice_id,
                    am.partner_id,
                    aml.product_id,
                    aml.quantity,
                    aml.price_unit,
                    am.currency_id,
                    po.id AS purchase_id,
                    sw.id AS warehouse_id

                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                LEFT JOIN purchase_order_line pol ON aml.purchase_line_id = pol.id
                LEFT JOIN purchase_order po ON pol.order_id = po.id
                LEFT JOIN stock_picking_type pt ON po.picking_type_id = pt.id
                LEFT JOIN stock_warehouse sw ON pt.warehouse_id = sw.id

                WHERE am.move_type = 'in_invoice'
                    AND aml.product_id IS NOT NULL
                    AND am.company_id = 5
            )
        """)
