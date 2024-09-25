# -*- coding: utf-8 -*-

from odoo import fields, models, api
from lxml import etree


        
class ProductProduct(models.Model):
    _inherit = 'product.product'   # Inherit the model

    loc_avail_qty = fields.Float(compute='comp_loc_avail_qty', digits='Product Unit of Measure')

    def comp_loc_avail_qty(self):
        for order in self:
            usr_loc = order.env.user.property_warehouse_id.lot_stock_id
            prd_tmp_stock = order.stock_quant_ids
            location = prd_tmp_stock.filtered(lambda m: m.location_id == usr_loc)
            order.loc_avail_qty = location.available_quantity
            print('Location Quantity',order.loc_avail_qty)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ProductProduct, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            root = etree.fromstring(res['arch'])
            root.set('edit', 'false')
            res['arch'] = etree.tostring(root)
        else:
            pass
        return res

    def action_open_label_layout(self):
        for order in self:
            print (not self.user_has_groups('base.group_partner_manager'))