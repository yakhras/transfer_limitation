from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class ProductInfo(models.Model):
    _name = 'product.info'   # Inherit the model



    product_id = fields.Many2one('product.product', string='Product', required=True)
    default_code = fields.Char(related='product_id.default_code', string='Internal Reference', store=True)
    categ_id = fields.Many2one(related='product_id.categ_id', string='Product Category', store=True)
    attachment_ids = fields.Many2many('ir.attachment', 'res_id',compute='_compute_attachments')
    attachment_count = fields.Integer(string='Attachment Count', compute='_compute_attachment_count')


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

    def _compute_attachment_count(self):
        """Compute the number of attachments linked to the selected product."""
        for record in self:
            if record.product_id:
                record.attachment_count = self.env['ir.attachment'].search_count([
                    ('res_model', '=', 'product.product'),  # Ensure it's an attachment for a product
                    ('res_id', '=', record.product_id.id)  # Match the selected product
                ])
            else:
                record.attachment_count = 0