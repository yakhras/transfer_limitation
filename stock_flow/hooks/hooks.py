# -*- coding: utf-8 -*-


from odoo.api import Environment, SUPERUSER_ID

def process_existing_internal_transfers(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})

    MoveLine = env['stock.move.line']
    Warehouse = env['stock.warehouse']

    lines = MoveLine.search([
        ('state', '=', 'done'),
        ('location_id.usage', '=', 'internal'),
        ('location_dest_id.usage', '=', 'internal'),
        ('operation', '=', False),
    ])

    for line in lines:
        # Set original line as Transfer Out
        warehouse = Warehouse.search([
            ('lot_stock_id', 'child_of', line.location_id.id)
        ], limit=1)

        line.write({
            'operation': 'transfer_out',
            'warehouse_id': warehouse.id if warehouse else False
        })

        # Create Transfer In line
        transfer_in_vals = {
            'product_id': line.product_id.id,
            'product_uom_id': line.product_uom_id.id,
            'qty_done': line.qty_done,
            'date': line.date,
            'reference': line.reference,
            'state': 'done',
            'location_id': line.location_dest_id.id,
            'location_dest_id': line.location_id.id,
            'operation': 'transfer_in',
            'warehouse_id': Warehouse.search([
                ('lot_stock_id', 'child_of', line.location_dest_id.id)
            ], limit=1).id,
        }

        MoveLine.create(transfer_in_vals)
