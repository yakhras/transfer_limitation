from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    
    gross_weight = fields.Float('Cross Weight', digits='Stock Weight')