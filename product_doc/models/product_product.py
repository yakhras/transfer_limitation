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
    

    # def write(self, vals):
    #     res = super().write(vals)
        
    #       # Check if the record is being archived/unarchived
    #     for product in self:
    #         if 'active' in vals:
    #             info_records = self.env['product.info'].search([('product_id.id', '=', product.id)])
    #             if info_records:
    #                 info_records.write({'active': vals.get('active', info_records.active)})  # Sync the active state
                
    #     return res


