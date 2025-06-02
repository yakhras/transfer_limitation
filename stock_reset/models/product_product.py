# -*- coding: utf-8 -*-

from odoo import models, api




class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_export_quant_svl(self):
        return self.env['export.quant.svl.wizard'].create({}).action_export_all_products_quant_svl()
    