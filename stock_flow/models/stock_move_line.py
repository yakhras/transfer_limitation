# -*- coding: utf-8 -*-

from odoo import models,fields, api




class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    balance = fields.Float(string="Balance", store=True)
    signed_qty_done = fields.Float(string="Signed Quantity Done", compute="_compute_signed_qty_done", store=True)
    operation = fields.Char(string="Operation", compute="_compute_operation", store=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', store=True)
   


    @api.depends('qty_done', 'location_id.usage', 'location_dest_id.usage')
    def _compute_signed_qty_done(self):
        for line in self:
            if line.location_id.usage == 'internal' and line.location_dest_id.usage != 'internal':
                # Outgoing
                line.signed_qty_done = -line.qty_done
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.location_id.id),
                ], limit=1) 
                line.balance = quant.quantity if quant else 0.0
            elif line.location_id.usage != 'internal' and line.location_dest_id.usage == 'internal':
                # Incoming
                line.signed_qty_done = line.qty_done
                quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.location_dest_id.id),
                ], limit=1) 
                line.balance = quant.quantity if quant else 0.0

    @api.depends('location_id', 'location_dest_id')
    def _compute_operation(self):
        for line in self:
            # Skip if already set during duplication (e.g., "Transfer In"/"Transfer Out")
            if line.operation in ('Transfer In', 'Transfer Out'):
                continue

            from_usage = line.location_id.usage
            to_usage = line.location_dest_id.usage
            from_name = line.location_id.display_name or ''
            to_name = line.location_dest_id.display_name or ''

            if from_usage == 'supplier' and to_usage == 'internal':
                line.operation = f"Buy → {to_name}"
                line.warehouse_id = line.location_dest_id.warehouse_id
            elif from_usage == 'internal' and to_usage == 'supplier':
                line.operation = f"Return Buy → {from_name}"
                line.warehouse_id = line.location_id.warehouse_id
            elif from_usage == 'internal' and to_usage == 'customer':
                line.operation = f"Sell → {from_name}"
                line.warehouse_id = line.location_id.warehouse_id
            elif from_usage == 'customer' and to_usage == 'internal':
                line.operation = f"Return Sell → {to_name}"
                line.warehouse_id = line.location_dest_id.warehouse_id
            elif from_usage == 'internal' and to_usage == 'inventory':
                line.operation = f"Scrap → {from_name}"
                line.warehouse_id = line.location_id.warehouse_id
            elif from_usage == 'inventory' and to_usage == 'internal':
                line.operation = f"Adjastment → {to_name}"
                line.warehouse_id = line.location_dest_id.warehouse_id
   