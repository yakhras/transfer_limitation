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
        res = super().write(vals)
        for product in self:
            if 'active' in vals:
                info_records = self.env['product.info'].search([('product_id.id', '=', product.id)])
                if info_records:
                    info_records.active = product.active  # Sync the active state
                    product.hs_code = info_records.active
                
        return res


