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
        if any(rec.company_id.id != 5 for rec in self):
            return super(StockMove, self).product_price_update_before_done(forced_qty=forced_qty)

        tmpl_dict = defaultdict(lambda: 0.0)
        std_price_update = {}

        def update_product_location_cost(product_id, location_id, cost):
            Product = self.env['product.product']
            Location = self.env['stock.location']
            ProductLocationCost = self.env['product.location.cost']

            product = Product.browse(product_id)
            location = Location.browse(location_id)

            if product and location:
                existing = ProductLocationCost.search([
                    ('product_id', '=', product_id),
                    ('location_id', '=', location_id)
                ], limit=1)
                if existing:
                    existing.cost = cost
                else:
                    ProductLocationCost.create({
                        'product_id': product_id,
                        'location_id': location_id,
                        'cost': cost,
                    })

        for move in self.filtered(lambda m: m._is_in()):
            product = move.product_id
            company = move.company_id
            cost_method = product.with_company(company).cost_method

            if cost_method == 'average':
                rounding = product.uom_id.rounding
                qty_available = product.sudo().with_company(company).quantity_svl + tmpl_dict[product.id]
                qty_done = sum(
                    line.product_uom_id._compute_quantity(line.qty_done, product.uom_id)
                    for line in move._get_in_move_lines()
                )
                qty = forced_qty or qty_done
                price_unit = move._get_price_unit()

                location_id = move.location_dest_id.id
                product_id = product.id

                location_cost = self.env['product.location.cost'].search([
                    ('product_id', '=', product_id),
                    ('location_id', '=', location_id)
                ], order='id desc', limit=1)

                cost_value = location_cost.cost if location_cost else 0.0

                if float_is_zero(qty_available, precision_rounding=rounding) or \
                float_is_zero(qty_available + qty, precision_rounding=rounding):
                    new_price = price_unit
                else:
                    existing_price = std_price_update.get((company.id, product_id)) or cost_value
                    new_price = ((existing_price * qty_available) + (price_unit * qty)) / (qty_available + qty)

                tmpl_dict[product_id] += qty_done
                std_price_update[(company.id, product_id, location_id)] = new_price

                product.with_company(company.id).with_context(disable_auto_svl=True).sudo().write({
                    'standard_price': new_price
                })

            elif cost_method == 'fifo':
                price_unit = move._get_price_unit()
                std_price_update[(move.company_id.id, move.product_id.id, move.location_dest_id.id)] = price_unit

        # Update product.location.cost records
        for (company_id, product_id, location_id), cost in std_price_update.items():
            update_product_location_cost(product_id, location_id, cost)


    

    # def product_price_update_before_done(self, forced_qty=None):
    #     # start_time = time.time()
    #     tmpl_dict = defaultdict(lambda: 0.0)
    #     # adapt standard price on incomming moves if the product cost_method is 'average'
    #     std_price_update = {}
    #     for rec in self:
    #         if rec.company_id.id == 5:
    #             for move in self.filtered(lambda move: move._is_in() and move.with_company(move.company_id).product_id.cost_method == 'average'):
    #                 product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
    #                 rounding = move.product_id.uom_id.rounding
                    
    #                 valued_move_lines = move._get_in_move_lines()
                    
    #                 qty_done = 0
    #                 for valued_move_line in valued_move_lines:
    #                     qty_done += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
                        
    #                 qty = forced_qty or qty_done
    #                 product_id = move.product_id.id  # Assuming this method runs in the product.product model
    #                 location_id = move.location_dest_id.id

    #                 if location_id and product_id:
    #                     location_cost = self.env['product.location.cost'].search([
    #                         ('product_id', '=', product_id),
    #                         ('location_id', '=', location_id)
    #                     ], order='id desc', limit=1)  # Get the most recent record

    #                     cost_value = location_cost.cost if location_cost else 0.0

    #                 if float_is_zero(product_tot_qty_available, precision_rounding=rounding):
    #                     new_std_price = move._get_price_unit()
                        
    #                 elif float_is_zero(product_tot_qty_available + move.product_qty, precision_rounding=rounding) or \
    #                         float_is_zero(product_tot_qty_available + qty, precision_rounding=rounding):
    #                     new_std_price = move._get_price_unit()
                        
    #                 else:
    #                     # Get the standard price
    #                     amount_unit = std_price_update.get((move.company_id.id, move.product_id.id)) or cost_value
                        
    #                     new_std_price = ((amount_unit * product_tot_qty_available) + (move._get_price_unit() * qty)) / (product_tot_qty_available + qty)
                        
    #                 tmpl_dict[move.product_id.id] += qty_done
                    
    #                 # Write the standard price, as SUPERUSER_ID because a warehouse manager may not have the right to write on products
    #                 std_price_update[move.company_id.id, move.product_id.id, move.location_dest_id.id] = new_std_price
    #                 move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write({'standard_price': new_std_price})
                    
    #                 for key, cost in std_price_update.items():
    #                     company_id, product_id, location_id = key
    #                     product = self.env['product.product'].browse(product_id)
    #                     location = self.env['stock.location'].browse(location_id)

    #                     if product and location:
    #                         # Check if a record already exists
    #                         existing_record = self.env['product.location.cost'].search([
    #                             ('product_id', '=', product.id),
    #                             ('location_id', '=', location.id)
    #                         ], limit=1)

    #                         if existing_record:
    #                             existing_record.cost = cost
    #                         else:
    #                             self.env['product.location.cost'].create({
    #                                 'product_id': product.id,
    #                                 'location_id': location.id,
    #                                 'cost': cost,
    #                             })
                    
                
    #             # adapt standard price on incomming moves if the product cost_method is 'fifo'
    #             for move in self.filtered(lambda move:
    #                                     move.with_company(move.company_id).product_id.cost_method == 'fifo'):
                    
    #                 std_price_update[move.company_id.id, move.product_id.id, move.location_dest_id.id] = move._get_price_unit()
    #                 for key, cost in std_price_update.items():
    #                     company_id, product_id, location_id = key
    #                     product = self.env['product.product'].browse(product_id)
    #                     location = self.env['stock.location'].browse(location_id)

    #                     if product and location:
    #                         self.env['product.location.cost'].create({
    #                             'product_id': product.id,
    #                             'location_id': location.id,
    #                             'cost': cost,
    #                         })
    #         else:
    #             return super(StockMove, self).product_price_update_before_done(forced_qty=forced_qty)
                


    def _create_out_svl(self, forced_quantity=None):
            """Create a `stock.valuation.layer` from `self`.

            :param forced_quantity: under some circunstances, the quantity to value is different than
                the initial demand of the move (Default value = None)
            """
            svl_vals_list = []
            for move in self:
                move = move.with_company(move.company_id)
                valued_move_lines = move._get_out_move_lines()
                valued_quantity = 0
                for valued_move_line in valued_move_lines:
                    valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
                if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                    continue
                svl_vals = move.product_id.with_context(location_id = self.location_id.id)._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id)
                svl_vals.update(move._prepare_common_svl_vals())
                if forced_quantity:
                    svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
                svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
                svl_vals_list.append(svl_vals)
            return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
    


    
class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    balance = fields.Float(string="Balance", compute="_compute_balance", store=True)


    @api.depends('state')
    def _compute_balance(self):
        for line in self:
            
            if line.location_dest_id.usage == 'internal':
                # Get the current quant for the product and destination location
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.location_dest_id.id),
                    ('company_id', '=', line.company_id.id),
                ], limit=1)

                existing_quantity = quant.quantity if quant else 0.0
                if line.state == 'done':

                # Simulate the new balance as existing + qty_done
                    line.balance = existing_quantity


    
