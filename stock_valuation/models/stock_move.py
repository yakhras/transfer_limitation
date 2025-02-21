# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, OrderedSet



class StockMove(models.Model):
    _inherit = "stock.move"

    result = fields.Char('Result')


    def _get_in_move_lines(self, location):
        """ Returns the `stock.move.line` records of `self` considered as incoming. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the incoming records
        :rtype: recordset
        """
        self.ensure_one()
        res = OrderedSet()
        for move_line in self.move_line_ids.filtered(lambda ml: ml.location_id == location):
            if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id:
                continue
            if not move_line.location_id._should_be_valued() and move_line.location_dest_id._should_be_valued():
                res.add(move_line.id)
        return self.env['stock.move.line'].browse(res)

    def _get_out_move_lines(self, location):
        """ Returns the `stock.move.line` records of `self` considered as outgoing. It is done thanks
        to the `_should_be_valued` method of their source and destionation location as well as their
        owner.

        :returns: a subset of `self` containing the outgoing records
        :rtype: recordset
        """
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids.filtered(lambda ml: ml.location_id == location):
            if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id:
                continue
            if move_line.location_id._should_be_valued() and not move_line.location_dest_id._should_be_valued():
                res |= move_line
        return res
    
    def _create_in_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_in_move_lines(move.location_id)
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            unit_cost = abs(move._get_price_unit())  # May be negative (i.e. decrease an out move).
            if move.product_id.cost_method == 'standard':
                unit_cost = move.product_id.standard_price
            svl_vals = move.product_id._prepare_in_svl_vals(forced_quantity or valued_quantity, unit_cost)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
    
    def _create_out_svl(self, forced_quantity=None):
        """Create a `stock.valuation.layer` from `self`.

        :param forced_quantity: under some circunstances, the quantity to value is different than
            the initial demand of the move (Default value = None)
        """
        svl_vals_list = []
        for move in self:
            move = move.with_company(move.company_id)
            valued_move_lines = move._get_out_move_lines(move.location_id)
            valued_quantity = 0
            for valued_move_line in valued_move_lines:
                valued_quantity += valued_move_line.product_uom_id._compute_quantity(valued_move_line.qty_done, move.product_id.uom_id)
            if float_is_zero(forced_quantity or valued_quantity, precision_rounding=move.product_id.uom_id.rounding):
                continue
            svl_vals = move.product_id._prepare_out_svl_vals(forced_quantity or valued_quantity, move.company_id)
            svl_vals.update(move._prepare_common_svl_vals())
            if forced_quantity:
                svl_vals['description'] = 'Correction of %s (modification of past move)' % move.picking_id.name or move.name
            svl_vals['description'] += svl_vals.pop('rounding_adjustment', '')
            svl_vals_list.append(svl_vals)
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list)
    
    def _is_in(self):
        """Check if the move should be considered as entering the company so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is entering the company else False
        :rtype: bool
        """
        self.ensure_one()
        if self._get_in_move_lines(self.location_id) and not self._is_dropshipped_returned():
            return True
        return False
    
    def _is_out(self):
        """Check if the move should be considered as leaving the company so that the cost method
        will be able to apply the correct logic.

        :returns: True if the move is leaving the company else False
        :rtype: bool
        """
        self.ensure_one()
        if self._get_out_move_lines(self.location_id) and not self._is_dropshipped():
            return True
        return False
    
    def product_price_update_before_done(self, forced_qty=None):
        tmpl_dict = defaultdict(lambda: 0.0)
        # adapt standard price on incomming moves if the product cost_method is 'average'
        std_price_update = {}
        test = self.filtered(lambda move: move._is_in() and move.with_company(move.company_id).product_id.cost_method == 'average')
        self.result = test
        for move in test:
            
            product_tot_qty_available = move.product_id.sudo().with_company(move.company_id).quantity_svl + tmpl_dict[move.product_id.id]
            
            rounding = move.product_id.uom_id.rounding

            valued_move_lines = move._get_in_move_lines(self.location_id)
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
            move.product_id.with_company(move.company_id.id).with_context(disable_auto_svl=True).sudo().write({'standard_price': new_std_price})
            std_price_update[move.company_id.id, move.product_id.id] = new_std_price

        # adapt standard price on incomming moves if the product cost_method is 'fifo'
        for move in self.filtered(lambda move:
                                  move.with_company(move.company_id).product_id.cost_method == 'fifo'
                                  and float_is_zero(move.product_id.sudo().quantity_svl, precision_rounding=move.product_id.uom_id.rounding)):
            move.product_id.with_company(move.company_id.id).sudo().write({'standard_price': move._get_price_unit()})

    def _action_done(self, cancel_backorder=False):
        # Init a dict that will group the moves by valuation type, according to `move._is_valued_type`.
        valued_moves = {valued_type: self.env['stock.move'] for valued_type in self._get_valued_types()}
        for move in self:
            if float_is_zero(move.quantity_done, precision_rounding=move.product_uom.rounding):
                continue
            for valued_type in self._get_valued_types():
                if getattr(move, '_is_%s' % valued_type)():
                    valued_moves[valued_type] |= move

        # AVCO application
        
        valued_moves['in'].product_price_update_before_done()

        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        

        # '_action_done' might have deleted some exploded stock moves
        valued_moves = {value_type: moves.exists() for value_type, moves in valued_moves.items()}

        # '_action_done' might have created an extra move to be valued
        for move in res - self:
            for valued_type in self._get_valued_types():
                if getattr(move, '_is_%s' % valued_type)():
                    valued_moves[valued_type] |= move

        stock_valuation_layers = self.env['stock.valuation.layer'].sudo()
        # Create the valuation layers in batch by calling `moves._create_valued_type_svl`.
        for valued_type in self._get_valued_types():
            todo_valued_moves = valued_moves[valued_type]
            if todo_valued_moves:
                todo_valued_moves._sanity_check_for_valuation()
                stock_valuation_layers |= getattr(todo_valued_moves, '_create_%s_svl' % valued_type)()

        stock_valuation_layers._validate_accounting_entries()
        stock_valuation_layers._validate_analytic_accounting_entries()

        stock_valuation_layers._check_company()

        # For every in move, run the vacuum for the linked product.
        products_to_vacuum = valued_moves['in'].mapped('product_id')
        company = valued_moves['in'].mapped('company_id') and valued_moves['in'].mapped('company_id')[0] or self.env.company
        for product_to_vacuum in products_to_vacuum:
            product_to_vacuum._run_fifo_vacuum(company)

        return res
    