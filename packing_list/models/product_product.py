from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    
    gross_weight = fields.Float('Gross Weight', digits='Stock Weight')


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    
    gross_weight = fields.Float('Gross Weight', digits='Stock Weight')