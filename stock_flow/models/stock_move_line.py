# -*- coding: utf-8 -*-

from odoo import models,fields, api
from odoo.tools.float_utils import float_round
from odoo.osv import expression




class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    balance = fields.Float(string="Balance", store=True, readonly=True)
    
    signed_qty_done = fields.Float(string="Signed Quantity Done",  store=True)
    operation = fields.Char(string="Operation",  store=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', store=True)



    # @api.depends('product_id', 'date')
    # def _compute_balance(self):
    #     for line in self:
    #         if not line.product_id or not line.date:
    #             line.balance = 0.0
    #             continue

    #         qty = self.env['product.product'].browse(line.product_id.id).with_context(
    #             to_date=line.date,
    #         ).qty_available

    #         line.balance = qty
   


    # @api.depends('qty_done', 'location_id.usage', 'location_dest_id.usage')
    # def _compute_signed_qty_done(self):
    #     for line in self:
    #         if line.location_id.usage == 'internal' and line.location_dest_id.usage != 'internal':
    #             # Outgoing
    #             line.signed_qty_done = -line.qty_done
    #             quant = self.env['stock.quant'].search([
    #                 ('product_id', '=', line.product_id.id),
    #                 ('location_id', '=', line.location_id.id),
    #             ], limit=1) 
    #             line.balance = quant.quantity if quant else 0.0
    #         elif line.location_id.usage != 'internal' and line.location_dest_id.usage == 'internal':
    #             # Incoming
    #             line.signed_qty_done = line.qty_done
    #             quant = self.env['stock.quant'].search([
    #                 ('product_id', '=', line.product_id.id),
    #                 ('location_id', '=', line.location_dest_id.id),
    #             ], limit=1) 
    #             line.balance = quant.quantity if quant else 0.0

    # @api.depends('location_id', 'location_dest_id')
    # def _compute_operation(self):
    #     for line in self:
    #         # Skip if already set during duplication (e.g., "Transfer In"/"Transfer Out")
    #         if line.operation in ('Transfer In', 'Transfer Out'):
    #             continue

    #         from_usage = line.location_id.usage
    #         to_usage = line.location_dest_id.usage
    #         from_name = line.location_id.display_name or ''
    #         to_name = line.location_dest_id.display_name or ''

    #         if from_usage == 'supplier' and to_usage == 'internal':
    #             line.operation = f"Buy → {to_name}"
    #             line.warehouse_id = line.location_dest_id.warehouse_id
    #         elif from_usage == 'internal' and to_usage == 'supplier':
    #             line.operation = f"Return Buy → {from_name}"
    #             line.warehouse_id = line.location_id.warehouse_id
    #         elif from_usage == 'internal' and to_usage == 'customer':
    #             line.operation = f"Sell → {from_name}"
    #             line.warehouse_id = line.location_id.warehouse_id
    #         elif from_usage == 'customer' and to_usage == 'internal':
    #             line.operation = f"Return Sell → {to_name}"
    #             line.warehouse_id = line.location_dest_id.warehouse_id
    #         elif from_usage == 'internal' and to_usage == 'inventory':
    #             line.operation = f"Scrap → {from_name}"
    #             line.warehouse_id = line.location_id.warehouse_id
    #         elif from_usage == 'inventory' and to_usage == 'internal':
    #             line.operation = f"Adjastment → {to_name}"
    #             line.warehouse_id = line.location_dest_id.warehouse_id
   


from odoo import fields, models, api

class StockMoveLineReport(models.Model):
    _name = 'stock.move.line.report'
    _description = 'Stock Move Line Report'
    _auto = False
    _rec_name = 'move_line_id'
    _order = 'date asc'


    move_line_id = fields.Many2one('stock.move.line', string="Original Move Line")
    product_id = fields.Many2one('product.product', string="Product")
    date = fields.Datetime(string="Date")
    location_id = fields.Many2one('stock.location', string="Source Location")
    location_dest_id = fields.Many2one('stock.location', string="Destination Location")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    qty_done = fields.Float(string="Qty Done")
    signed_qty_done = fields.Float(string="Signed Qty")
    operation = fields.Char(string="Operation")
    direction = fields.Selection([('in', 'In'), ('out', 'Out')], string="Direction")

    @api.model
    def init(self):
        self.env.cr.execute("""DROP VIEW IF EXISTS stock_move_line_report""")
        self.env.cr.execute("""
            CREATE VIEW stock_move_line_report AS (
                SELECT
                    sml.id AS id,
                    sml.id AS move_line_id,
                    sml.product_id,
                    sml.date,
                    sml.location_id,
                    sml.location_dest_id,
                    sw.id AS warehouse_id,
                    sml.qty_done,
                    CASE
                        WHEN sl.usage = 'internal' AND sld.usage != 'internal' THEN -sml.qty_done
                        WHEN sl.usage != 'internal' AND sld.usage = 'internal' THEN sml.qty_done
                        ELSE 0
                    END AS signed_qty_done,
                    sm.name AS operation,
                    CASE
                        WHEN sl.usage = 'internal' AND sld.usage != 'internal' THEN 'out'
                        WHEN sl.usage != 'internal' AND sld.usage = 'internal' THEN 'in'
                        ELSE NULL
                    END AS direction
                FROM stock_move_line sml
                JOIN stock_move sm ON sm.id = sml.move_id
                LEFT JOIN stock_location sl ON sml.location_id = sl.id
                LEFT JOIN stock_location sld ON sml.location_dest_id = sld.id
                LEFT JOIN stock_picking sp ON sm.picking_id = sp.id
                LEFT JOIN stock_warehouse sw ON sp.picking_type_id = sw.int_type_id
                WHERE
                    sml.product_id = 33196 AND
                    sl.usage = 'internal' AND sld.usage = 'internal'
            )
        """)


    