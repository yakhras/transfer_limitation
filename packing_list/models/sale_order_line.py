from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'   # Inherit the model


    gross_weight = fields.Float('Cross Weight', digits='Stock Weight')
    net_weight = fields.Float('Net Weight', digits='Stock Weight')