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
            
            
            valued_move_lines = move._get_in_move_lines()
            

            qty_done = 0
            for valued_move_line in valued_move_lines:
                qty_done += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
                
            qty = forced_qty or qty_done
            if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
                
            elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
                    float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
                new_std_price = move._get_price_unit()
                
            else:
                # Get the standard price
                amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or move.product_id.with_company(move.company_id).standard_price
                
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
            self.result = std_price_update
            
        # adapt standard price on incomming moves if the product cost_method is 'fifo'
        for move in self.filtered(lambda move:
                                  move.with_company(move.company_id).product_id.cost_method == 'fifo'
                                  and float_is_zero(move.product_id.sudo().quantity_svl, precision_rounding=move.product_id.uom_id.rounding)):
            self.result = move.product_id.sudo().quantity_svl
            move.product_id.with_company(move.company_id.id).sudo().write({'standard_price': move._get_price_unit()})

        # end_time = time.time()
        # execution_time = end_time - start_time

        # # Store the result
        # self.result = f"Execution Time: {execution_time:.5f} seconds"




    # def product_price_update_before_done(self, forced_qty=None):
    #     start_time = time.time()
    #     tmpl_dict = defaultdict(float)
    #     std_price_update = {}
        
    #     fifo_moves = []
    #     location_cost_updates = []

    #     # Preload products and locations to avoid repeated lookups
    #     product_cache = {p.id: p for p in self.mapped('product_id')}
    #     location_cache = {l.id: l for l in self.mapped('location_dest_id')}

    #     # Process average cost updates
    #     avg_cost_moves = self.filtered(lambda m: m._is_in() and m.with_company(m.company_id).product_id.cost_method == 'average')

    #     for move in avg_cost_moves:
    #         product = product_cache.get(move.product_id.id)
    #         if not product:
    #             continue

    #         product_tot_qty_available = product.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[product.id]
    #         rounding = product.uom_id.rounding

    #         qty_done = sum(ml.product_uom_id._compute_quantity(ml.qty_done, product.uom_id) for ml in move._get_in_move_lines())
    #         qty = forced_qty or qty_done

    #         if float_is_zero(product_tot_qty_available, precision_rounding=rounding) or \
    #         float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
    #             new_std_price = move._get_price_unit()
    #         else:
    #             prev_std_price = std_price_update.get((move.company_id.id, product.id), product.with_company(move.company_id).standard_price)
    #             new_std_price = ((prev_std_price * product_tot_qty_available) + (move._get_price_unit() * qty)) / (product_tot_qty_available + qty)

    #         tmpl_dict[product.id] += qty_done
    #         std_price_update[(move.company_id.id, product.id, move.location_dest_id.id)] = new_std_price

    #     # Batch update product standard prices
    #     for (company_id, product_id, location_id), new_std_price in std_price_update.items():
    #         product_cache[product_id].with_company(company_id).with_context(disable_auto_svl=True).sudo().write({'standard_price': new_std_price})

    #         location = location_cache.get(location_id)
    #         if location:
    #             location_cost_updates.append({
    #                 'product_id': product_id,
    #                 'location_id': location_id,
    #                 'cost': new_std_price,
    #             })

    #     # Update or create product location cost records
    #     location_cost_model = self.env['product.location.cost']
    #     for update in location_cost_updates:
    #         existing_record = location_cost_model.search([
    #             ('product_id', '=', update['product_id']),
    #             ('location_id', '=', update['location_id'])
    #         ], limit=1)
    #         if existing_record:
    #             existing_record.cost = update['cost']
    #         else:
    #             location_cost_model.create(update)

    #     # Process FIFO cost updates
    #     fifo_moves = self.filtered(lambda m: m.with_company(m.company_id).product_id.cost_method == 'fifo' and 
    #                                     float_is_zero(m.product_id.sudo().quantity_svl, precision_rounding=m.product_id.uom_id.rounding))
    #     for move in fifo_moves:
    #         move.product_id.with_company(move.company_id).sudo().write({'standard_price': move._get_price_unit()})

    #     end_time = time.time()
    #     execution_time = end_time - start_time

    #     # Store the result
    #     self.result = f"Execution Time: {execution_time:.5f} seconds"
