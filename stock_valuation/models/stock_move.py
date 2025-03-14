# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
import time
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, OrderedSet



class StockMove(models.Model):
    _inherit = "stock.move"

    result = fields.Float('Result')


    

    def product_price_update_before_done(self, forced_qty=None):
        # start_time = time.time()
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        for move in self.filtered(lambda move: move._is_in() and move.with_company(move.company_id).product_id.cost_method == 'average'):
            product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
            rounding = move.product_id.uom_id.rounding
            #self.result = product_tot_qty_available
            
            valued_move_lines = move._get_in_move_lines()
            
            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
                
            qty = forced_qty or qty_done
            product_id = move.product_id.id  # Assuming this method runs in the product.product model
            location_id = move.location_dest_id.id

            if location_id and product_id:
                location_cost = self.env['product.location.cost'].search([
                    ('product_id', '=', product_id),
                    ('location_id', '=', location_id)
                ], order='id desc', limit=1)  # Get the most recent record

                cost_value = location_cost.cost if location_cost else 0.0

            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
                
            elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
                    float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
                
            else:
                # Get the standard price
                amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or cost_value #move.product_id.with_company(move.company_id).standard_price
                
                new_std_price = ((amount_unit * product_tot_qty_available) + (move._get_price_unit() * qty)) / (product_tot_qty_available + qty)
                
            tmpl_dict[move.product_id.id] += qty_done
            
            # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
            std_price_update[move.company_id.id, move.product_id.id, move.location_dest_id.id] = new_std_price
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write({'standard_price': new_std_price})
            
            for key, cost in std_price_update.items():
                company_id, product_id, location_id = key
                product = self.env['product.product'].browse(product_id)
                location = self.env['stock.location'].browse(location_id)

                if product and location:
                    # Check if a record already exists
                    existing_record = self.env['product.location.cost'].search([
                        ('product_id', '=', product.id),
                        ('location_id', '=', location.id)
                    ], limit=1)

                    if existing_record:
                        existing_record.cost = cost
                    else:
                        self.env['product.location.cost'].create({
                            'product_id': product.id,
                            'location_id': location.id,
                            'cost': cost,
                        })
            
        
        # adapt standard price on incomming moves if the product cost_method is 'fifo'
        for move in self.filtered(lambda move:
                                  move.with_company(move.company_id).product_id.cost_method == 'fifo'):
                                  #and float_is_zero(move.product_id.sudo().quantity_svl, precision_rounding=move.product_id.uom_id.rounding)):
            
            #move.product_id.with_company(move.company_id.id).sudo().write({'standard_price': move._get_price_unit()})
            std_price_update[move.company_id.id, move.product_id.id, move.location_dest_id.id] = move._get_price_unit()
            for key, cost in std_price_update.items():
                company_id, product_id, location_id = key
                product = self.env['product.product'].browse(product_id)
                location = self.env['stock.location'].browse(location_id)

                if product and location:
                    self.env['product.location.cost'].create({
                        'product_id': product.id,
                        'location_id': location.id,
                        'cost': cost,
                    })
            

        # end_time = time.time()
        # execution_time = end_time - start_time

        # # Store the result
        # self.result = f"Execution Time: {execution_time:.5f} seconds"

