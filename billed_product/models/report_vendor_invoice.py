from odoo import models, fields, api, tools


class VendorBillReport(models.Model):
    _name = 'vendor.bill.report'
    _description = 'Vendor Bill Report'
    _auto = False

    invoice_id = fields.Many2one('account.move', string='Vendor Bill')
    invoice_date = fields.Date(string='Invoice Date')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    currency_id = fields.Many2one('res.currency', string='Currency')
    currency_rate = fields.Float(string='Currency Rate')


    @api.model
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY aml.id) AS id,
                    am.id AS invoice_id,
                    am.invoice_date,
                    am.partner_id,
                    aml.product_id,
                    aml.quantity,
                    aml.price_unit,
                    am.currency_id,
                    am.currency_rate,
                    po.name AS purchase_id,
                    sw.id AS warehouse_id

                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                LEFT JOIN purchase_order_line pol ON aml.purchase_line_id = pol.id
                LEFT JOIN purchase_order po ON pol.order_id = po.id
                LEFT JOIN stock_picking_type pt ON po.picking_type_id = pt.id
                LEFT JOIN stock_warehouse sw ON pt.warehouse_id = sw.id

                WHERE am.move_type = 'in_invoice'
                    AND aml.product_id IS NOT NULL
                    AND am.state = 'posted'
                    AND am.company_id = 5
            )
        """ % self._table)




class CustomerInvoiceReport(models.Model):
    _name = 'customer.invoice.report'
    _description = 'Customer Invoice Report'
    _auto = False

    invoice_id = fields.Many2one('account.move', string='Customer Invoice')
    invoice_date = fields.Date(string='Invoice Date')
    partner_id = fields.Many2one('res.partner', string='Customer')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    sale_id = fields.Many2one('sale.order', string='Sale Order')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    currency_id = fields.Many2one('res.currency', string='Currency')
    currency_rate = fields.Float(string='Currency Rate')

    @api.model
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY aml.id) AS id,
                    am.id AS invoice_id,
                    am.invoice_date,
                    am.partner_id,
                    aml.product_id,
                    aml.quantity,
                    aml.price_unit,
                    am.currency_id,
                    am.currency_rate,
                    so.id AS sale_id,
                    sw.id AS warehouse_id

                FROM account_move_line aml
                JOIN account_move am ON aml.move_id = am.id
                LEFT JOIN sale_order_line sol ON aml.sale_line_id = sol.id
                LEFT JOIN sale_order so ON sol.order_id = so.id
                LEFT JOIN stock_warehouse sw ON sol.warehouses_id = sw.id

                WHERE am.move_type = 'out_invoice'
                    AND aml.product_id IS NOT NULL
                    AND am.partner_id IS NOT NULL
                    AND am.state = 'posted'
                    AND am.company_id = 5
            )
        """ % (self._table))
