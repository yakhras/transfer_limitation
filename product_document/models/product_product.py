from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class ProductInfo(models.Model):
    _name = 'product.info'   # Inherit the model



    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True)
    default_code = fields.Char(related='product_id.default_code', string='Internal Reference', store=True)
    categ_id = fields.Many2one(related='product_id.categ_id', string='Product Category', store=True, readonly=True)
    attachment_ids = fields.Many2many('ir.attachment', 'res_id',compute='_compute_attachments')
    attachment_count = fields.Integer(string='Attachment Count', compute='_compute_attachment_count')
    attachment_urls = fields.Char(compute='_compute_attachment_urls', string="Attachment URLs")


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


    def _compute_attachment_urls(self):
        for record in self:
            urls = []
            for attachment in record.attachment_ids:
                # Construct the URL for each attachment
                url = f'/web/content/{attachment.id}?download=true'
                urls.append(url)
            # Store the URLs as a comma-separated string
            record.attachment_urls = ', '.join(urls)


    # to display the partner’s name instead of the default object name
    def name_get(self):
        result = []
        for record in self:
            name = record.product_id.name  # Get the partner name
            result.append((record.id, name))  # Return a tuple of (record_id, name)
        return result