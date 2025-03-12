from odoo import models, fields



class ProductInfo(models.Model):
    _name = 'product.info'   # Inherit the model



    product_id = fields.Many2one('product.product', string='Product', required=True)
    display_name = fields.Char(related='product_id.display_name', string='Product', store=True)
    default_code = fields.Char(related='product_id.default_code', string='Internal Reference', store=True)
    categ_id = fields.Many2one(related='product_id.categ_id', string='Category', store=True, readonly=True)
    categ_name = fields.Char(related='categ_id.name', string='Product Category', store=True)
    attachment_ids = fields.Many2many('ir.attachment', 'res_id',compute='_compute_attachments')
    available_qty_location_8 = fields.Float(string="Available Qty", compute="_compute_available_qty", store=True)
    weight = fields.Float(related='product_id.weight', string="Net Weight", store=True, readonly=True)
    gross_weight = fields.Float(related='product_id.gross_weight', string="Gross Weight", store=True, readonly=True, compute='_get_weight')
    uom_name = fields.Char(related='product_id.uom_id.name', string="Unit of Measure", store=True, readonly=True)
    active = fields.Boolean(default=True)
    

    
    def _compute_available_qty(self):
        """ Compute available quantity from stock.quant for location 8 """
        StockQuant = self.env['stock.quant']
        for record in self:
            if record.product_id:
                quant = StockQuant.search([
                    ('product_id.id', '=', record.product_id.id),
                    ('location_id.id', '=', 8)  
                ], limit=1)
                record.available_qty_location_8 = quant.available_quantity if quant else 0.0
            else:
                record.available_qty_location_8 = 0.0


    def _compute_attachments(self):
        """Fetch attachments linked to the selected product."""
        for record in self:
            if record.product_id:
                record.attachment_ids = self.env['ir.attachment'].search([
                    ('res_model', '=', 'product.product'),  # Look for product attachments
                    ('res_id', '=', record.product_id.id)  # Match with selected product
                ])
            else:
                record.attachment_ids = False

    
    def name_get(self):
        result = []
        for record in self:
            name = record.product_id.display_name  # Get the partner name
            result.append((record.id, name))  # Return a tuple of (record_id, name)
        return result
    

    def _get_weight(self):
        for record in self:
            record.gross_weight = self.product_id.gross_weight
