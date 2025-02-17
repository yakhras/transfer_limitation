# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp


class StockProductionLot(models.Model):
    _inherit = "stock.production.lot"

    real_cost = fields.Float(string="Purchase Costs/Uom", compute='_compute_product_real_landed_cost',
                             digits=dp.get_precision('Lot Costing'))
    real_actual_cost = fields.Monetary(string="Actual Unit Cost")
    landed_cost_amount = fields.Float(string="Landed Costs", digits=dp.get_precision('Lot Costing'),
                                      compute="_compute_product_real_landed_cost")
    total_purchased_qty = fields.Monetary(string="Purchased Quantity", compute="_compute_total_purchase_qty")
    real_cost_available_stock = fields.Monetary(string="Available Stock Cost",
                                                compute="_compute_real_cost_available_stock")
    currency_id = fields.Many2one('res.currency', string="Currency", compute="_compue_currency")
    real_cost_per_unit = fields.Monetary(string="Real Unit Cost", compute="_compute_real_cost_per_unit")
    cost_based_avail_stock = fields.Monetary(string="Total Cost Based On Available Stock",
                                             compute="_compute_avail_stock_unit")

    def _compute_avail_stock_unit(self):
        for line in self:
            line.cost_based_avail_stock = line.real_cost * line.product_qty
            return

    def _compute_real_cost_per_unit(self):

        for line in self:
            if line.total_purchased_qty > 0:
                line.real_cost_per_unit = line.real_cost / line.total_purchased_qty
            else:
                line.real_cost_per_unit = 0
            if line.real_actual_cost:
                line.real_cost_per_unit = line.real_actual_cost
            else:
                line.real_cost_per_unit = 0
        return

    def _compue_currency(self):

        currency_id = self.env['res.users'].browse(self._context.get('uid')).company_id.currency_id

        for line in self:
            line.currency_id = currency_id.id
        return

    def _compute_total_purchase_qty(self):

        for line in self:
            stock_move_line_res = self.env['stock.move.line'].sudo().search([('lot_id', '=', line.id)])
            stock_move_line_obj = False
            for move in stock_move_line_res:
                if move.picking_id.picking_type_id.code == 'incoming':
                    stock_move_line_obj = move
            if stock_move_line_obj != False:
                if stock_move_line_obj.picking_id.picking_type_id.code == 'incoming':
                    line.total_purchased_qty = stock_move_line_obj.qty_done
                else:
                    line.total_purchased_qty = 0
            else:
                line.total_purchased_qty = 0
        return

    @api.depends('real_cost', 'total_purchased_qty')
    def _compute_real_cost_available_stock(self):

        for line in self:
            if line.real_actual_cost > 0:
                cost_per_product = line.real_cost_per_unit * line.product_qty
                line.real_cost_available_stock = cost_per_product
            else:
                if line.total_purchased_qty > 0:
                    cost_per_product = line.real_cost / line.total_purchased_qty
                    line.real_cost_available_stock = cost_per_product * line.product_qty
                else:
                    line.real_cost_available_stock = 0
        return


    @api.depends('total_purchased_qty')
    def _compute_product_real_landed_cost(self):
        quant_obj = self.env['stock.quant'].sudo().search(
            [('lot_id', 'in', self.ids), ('location_id.usage', '=', 'internal')])

        stock_move_line_res = self.env['stock.move.line'].sudo().search([('lot_id', 'in', self.ids)], limit=1)

        stock_move_line_obj = False
        for move in stock_move_line_res:
            if move.picking_id.picking_type_id.code == 'incoming':
                stock_move_line_obj = move

        if stock_move_line_obj != False:
            if stock_move_line_obj.picking_id.picking_type_id.code == 'incoming':

                landed_res = self.env['stock.landed.cost'].sudo().search(
                    [('picking_ids', 'in', [stock_move_line_obj.picking_id.id])])

                landed_res_lines = self.env['stock.valuation.adjustment.lines'].sudo().search(
                    [('product_id', '=', self.product_id.id),
                     ('cost_id', '=', landed_res.id)])

                total = 0
                product_lst = []

                for line in landed_res_lines:
                    if not (line.product_id.id, line.cost_line_id.id) in product_lst:
                        total = total + line.additional_landed_cost
                        product_lst.append((line.product_id.id, line.cost_line_id.id))
            quantity = self.total_purchased_qty

            price = 0
            purchase_order_res = self.env['purchase.order'].search(
                [('name', '=', stock_move_line_obj.picking_id.origin)])
            purchase_currency = purchase_order_res.currency_id
            purchase_company = purchase_order_res.company_id

            for line in purchase_order_res.order_line:
                if line.product_id.id == self.product_id.id:
                    price = (line.price_subtotal / line.product_qty) * quantity

                    price = purchase_currency._convert(price, purchase_company.currency_id, purchase_company,
                                                       purchase_order_res.date_order.date() or fields.Date.today())

            if quantity > 0:
                self.real_cost = price / quantity
                self.landed_cost_amount = total
            else:
                self.real_cost = 0
                self.landed_cost_amount = total
        else:
            self.real_cost = 0
            self.landed_cost_amount = 0
        return

        # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
