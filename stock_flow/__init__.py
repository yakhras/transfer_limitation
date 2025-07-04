# -*- coding: utf-8 -*-


from . import models


from odoo.api import Environment, SUPERUSER_ID

def process_existing_internal_transfers(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})

    MoveLine = env['stock.move.line'].with_context(active_test=False)
    Warehouse = env['stock.warehouse']
    Quant = env['stock.quant']

    lines = MoveLine.search([
        ('state', '=', 'done'),
        ('location_id.usage', '=', 'internal'),
        ('location_dest_id.usage', '=', 'internal'),
        ('operation', '=', False),
    ])

    for line in lines:
        product = line.product_id
        if not product:
            continue

        # 🟥 Set original line: Transfer Out
        warehouse_from = Warehouse.search([('lot_stock_id', 'child_of', line.location_id.id)], limit=1)
        quant_out = Quant.search([
            ('product_id', '=', product.id),
            ('location_id', '=', line.location_id.id)
        ], limit=1)

        signed_qty_out = -line.qty_done
        balance_out = quant_out.quantity if quant_out else 0.0

        line.write({
            'operation': 'Transfer Out',
            'warehouse_id': warehouse_from.id if warehouse_from else False,
            'signed_qty_done': signed_qty_out,
            'balance': balance_out,
        })

        # 🟩 Create mirrored line: Transfer In
        warehouse_to = Warehouse.search([('lot_stock_id', 'child_of', line.location_dest_id.id)], limit=1)
        quant_in = Quant.search([
            ('product_id', '=', product.id),
            ('location_id', '=', line.location_dest_id.id)
        ], limit=1)

        signed_qty_in = line.qty_done
        balance_in = quant_in.quantity if quant_in else 0.0

        MoveLine.create({
            'product_id': product.id,
            'product_uom_id': line.product_uom_id.id,
            'qty_done': line.qty_done,
            'date': line.date,
            'reference': line.reference,
            'state': 'done',
            'location_id': line.location_dest_id.id,
            'location_dest_id': line.location_id.id,
            'operation': 'Transfer In',
            'warehouse_id': warehouse_to.id if warehouse_to else False,
            'signed_qty_done': signed_qty_in,
            'balance': balance_in,
        })
