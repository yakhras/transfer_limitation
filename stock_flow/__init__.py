# -*- coding: utf-8 -*-


from . import models


# from odoo.api import Environment, SUPERUSER_ID



# def process_existing_internal_transfers(cr, registry):
#     env = Environment(cr, SUPERUSER_ID, {})

#     MoveLine = env['stock.move.line'].with_context(active_test=False)
#     Warehouse = env['stock.warehouse']
#     Quant = env['stock.quant']

#     lines = MoveLine.search([
#         ('state', '=', 'done'),
#         ('product_id', '!=', False),
#     ])

#     for line in lines:
#         from_usage = line.location_id.usage
#         to_usage = line.location_dest_id.usage
#         from_name = line.location_id.display_name or ''
#         to_name = line.location_dest_id.display_name or ''

#         signed_qty = 0.0
#         balance = 0.0
#         warehouse = False
#         operation = False

#         # Outgoing (internal to customer/inventory)
#         if from_usage == 'internal' and to_usage not in ('internal',):
#             signed_qty = -line.qty_done
#             quant = Quant.search([
#                 ('product_id', '=', line.product_id.id),
#                 ('location_id', '=', line.location_id.id)
#             ], limit=1)
#             balance = quant.quantity if quant else 0.0
#             operation = f"Sell → {from_name}" if to_usage == 'customer' else f"Scrap → {from_name}"
#             warehouse = line.location_id.warehouse_id

#         # Incoming (supplier/customer/inventory to internal)
#         elif from_usage not in ('internal',) and to_usage == 'internal':
#             signed_qty = line.qty_done
#             quant = Quant.search([
#                 ('product_id', '=', line.product_id.id),
#                 ('location_id', '=', line.location_dest_id.id)
#             ], limit=1)
#             balance = quant.quantity if quant else 0.0
#             operation = f"Buy → {to_name}" if from_usage == 'supplier' else f"Adjastment → {to_name}"
#             warehouse = line.location_dest_id.warehouse_id

#         # Internal transfer (both sides internal)
#         elif from_usage == 'internal' and to_usage == 'internal':
#             # Process only if operation is not already set (to avoid duplication)
#             if not line.operation:
#                 # Original = Transfer Out
#                 warehouse_from = Warehouse.search([
#                     ('lot_stock_id', 'child_of', line.location_id.id)
#                 ], limit=1)
#                 quant_out = Quant.search([
#                     ('product_id', '=', line.product_id.id),
#                     ('location_id', '=', line.location_id.id)
#                 ], limit=1)

#                 signed_qty_out = -line.qty_done
#                 balance_out = quant_out.quantity if quant_out else 0.0

#                 line.write({
#                     'operation': 'Transfer Out',
#                     'warehouse_id': warehouse_from.id if warehouse_from else False,
#                     'signed_qty_done': signed_qty_out,
#                     'balance': balance_out,
#                 })

#                 # Create mirrored: Transfer In
#                 warehouse_to = Warehouse.search([
#                     ('lot_stock_id', 'child_of', line.location_dest_id.id)
#                 ], limit=1)
#                 quant_in = Quant.search([
#                     ('product_id', '=', line.product_id.id),
#                     ('location_id', '=', line.location_dest_id.id)
#                 ], limit=1)

#                 signed_qty_in = line.qty_done
#                 balance_in = quant_in.quantity if quant_in else 0.0

#                 MoveLine.create({
#                     'product_id': line.product_id.id,
#                     'product_uom_id': line.product_uom_id.id,
#                     'qty_done': line.qty_done,
#                     'date': line.date,
#                     'reference': line.reference,
#                     'state': 'done',
#                     'location_id': line.location_dest_id.id,
#                     'location_dest_id': line.location_id.id,
#                     'operation': 'Transfer In',
#                     'warehouse_id': warehouse_to.id if warehouse_to else False,
#                     'signed_qty_done': signed_qty_in,
#                     'balance': balance_in,
#                     'company_id': line.company_id.id,
#                 })
#             continue  # skip rest of logic for mirrored transfers

#         # Apply computed values to other lines (non-internal transfers)
#         if operation or warehouse:
#             line.write({
#                 'operation': operation,
#                 'warehouse_id': warehouse.id if warehouse else False,
#                 'signed_qty_done': signed_qty,
#                 'balance': balance,
#             })
