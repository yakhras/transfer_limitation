from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class ProductInfo(models.Model):
    _name = 'product.info'   # Inherit the model



    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(related='product_id.name', string='Product Name', store=True)
    default_code = fields.Char(related='product_id.default_code', string='Internal Reference', store=True)
    categ_id = fields.Many2one(related='product_id.categ_id', string='Product Category', store=True)
    document_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'product.product')], string='Documents')
