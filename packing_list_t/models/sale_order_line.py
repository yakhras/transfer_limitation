from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'   # Inherit the model


    gross_weight = fields.Float('Gross Weight', 
                                digits='Stock Weight', 
                                related='product_id.gross_weight',
                                store=True,
                                readonly=False
                                )
    net_weight = fields.Float('Net Weight',
                              digits='Stock Weight',
                              related='product_id.weight',
                              store=True,
                              readonly=False
                              )

