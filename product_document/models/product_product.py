from odoo import models, fields



class ProductProduct(models.Model):
    _inherit = 'product.product'

    
    def create(self, vals):
        product = super().create(vals)
        self.env['product.info'].create({
            'product_id': product.id})
        return product
    


    def unlink(self):
        for product in self:
            self.env['product.info'].search([('product_id', '=', product.id)]).unlink()
        return super().unlink()
    

    def write(self, vals):
        res = super(ProductProduct, self).write(vals)
        if 'active' in vals:  # 'active' field is used for archiving/unarchiving
            for product in self:
                info_records = self.env['product.info'].search([('product_id', '=', product.id)])
                info_records.write({'active': vals['active']})
        return res

