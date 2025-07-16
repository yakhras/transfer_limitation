# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LogisticsContainerLine(models.Model):
    _name = 'logistics.container.line'
    _description = 'Container Product Line'
    _order = 'sequence, id'

    # Relations
    container_id = fields.Many2one('logistics.container', string='Container', 
                                  required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    
    # Product Information
    product_qty = fields.Float('Quantity', required=True, digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    price_unit = fields.Float('Unit Price', digits='Product Price')
    price_subtotal = fields.Monetary('Subtotal', compute='_compute_price_subtotal', 
                                    store=True, currency_field='currency_id')
    
    # Additional Product Details
    lot_number = fields.Char('Lot/Batch Number')
    serial_number = fields.Char('Serial Number')
    expiry_date = fields.Date('Expiry Date')
    manufacturing_date = fields.Date('Manufacturing Date')
    country_of_origin = fields.Many2one('res.country', string='Country of Origin')
    
    # Product Physical Properties
    gross_weight = fields.Float('Gross Weight (KG)', digits=(10, 2))
    net_weight = fields.Float('Net Weight (KG)', digits=(10, 2))
    volume_per_unit = fields.Float('Volume per Unit (M³)', digits=(8, 4))
    
    # Organization
    sequence = fields.Integer('Sequence', default=10)
    notes = fields.Text('Notes')
    
    # Related Fields
    currency_id = fields.Many2one('res.currency', related='container_id.currency_id')
    container_state = fields.Selection(related='container_id.state', string='Container Status')
    
    @api.depends('product_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_qty * line.price_unit
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            # self.price_unit = self.product_id.standard_price
            # if self.product_id.country_of_origin:
            #     self.country_of_origin = self.product_id.country_of_origin
