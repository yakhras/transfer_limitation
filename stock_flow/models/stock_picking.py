# -*- coding: utf-8 -*-

from odoo import models,fields, api




class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()

        for picking in self:
            for move_line in picking.move_line_ids:
                if (
                    move_line.state == 'done' and
                    move_line.location_id.usage == 'internal' and
                    move_line.location_dest_id.usage == 'internal'
                ):
                    from_name = move_line.location_id.display_name or ''
                    to_name = move_line.location_dest_id.display_name or ''
                    # Get quant for source location (for original move line)
                    source_quant = self.env['stock.quant'].search([
                        ('location_id', '=', move_line.location_id.id),
                        ('product_id', '=', move_line.product_id.id),
                    ], limit=1)

                    # Set signed_qty_done and balance on original move line
                    move_line.signed_qty_done = -move_line.qty_done
                    move_line.balance = source_quant.quantity if source_quant else 0.0
                    move_line.operation = f"Transfer Out → {from_name}"
                    move_line.warehouse_id = move_line.location_id.warehouse_id

                    # Create the copied line
                    copied_line = move_line.copy()

                    # Get quant for destination location (for copied line)
                    dest_quant = self.env['stock.quant'].search([
                        ('location_id', '=', copied_line.location_dest_id.id),
                        ('product_id', '=', copied_line.product_id.id),
                    ], limit=1)

                    # Set signed_qty_done and balance on copied move line
                    copied_line.signed_qty_done = move_line.qty_done
                    copied_line.balance = dest_quant.quantity if dest_quant else 0.0
                    copied_line.operation = f"Transfer In → {to_name}"
                    copied_line.warehouse_id = copied_line.location_dest_id.warehouse_id

        return res
    