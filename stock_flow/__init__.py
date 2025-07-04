# -*- coding: utf-8 -*-


from . import models


from odoo.api import Environment, SUPERUSER_ID

def process_existing_internal_transfers(cr, registry):
    env = Environment(cr, SUPERUSER_ID, {})

    MoveLine = env['stock.move.line'].with_context(active_test=False)
    Quant = env['stock.quant']

    domain = [('state', '=', 'done'), ('product_id', '!=', False)]
    lines = MoveLine.search(domain)

    for line in lines:
        from_usage = line.location_id.usage
        to_usage = line.location_dest_id.usage
        from_name = line.location_id.display_name or ''
        to_name = line.location_dest_id.display_name or ''

        signed_qty = 0.0
        balance = 0.0
        warehouse = False
        operation = False

        # Signed qty and balance
        if from_usage == 'internal' and to_usage != 'internal':
            # Outgoing
            signed_qty = -line.qty_done
            quant = Quant.search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_id.id)
            ], limit=1)
            balance = quant.quantity if quant else 0.0
            operation = f"Sell → {from_name}" if to_usage == 'customer' else f"Scrap → {from_name}"
            warehouse = line.location_id.warehouse_id

        elif from_usage != 'internal' and to_usage == 'internal':
            # Incoming
            signed_qty = line.qty_done
            quant = Quant.search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_dest_id.id)
            ], limit=1)
            balance = quant.quantity if quant else 0.0
            operation = f"Buy → {to_name}" if from_usage == 'supplier' else f"Adjastment → {to_name}"
            warehouse = line.location_dest_id.warehouse_id

        elif from_usage == 'internal' and to_usage == 'internal':
            # Transfer between internals — optional
            operation = f"Transfer → {to_name}"
            warehouse = line.location_id.warehouse_id
            signed_qty = line.qty_done  # or 0.0, depends on your intent
            balance = 0.0  # You can also add quant fetch here if needed

        # Bulk update the fields
        line.write({
            'signed_qty_done': signed_qty,
            'balance': balance,
            'operation': operation,
            'warehouse_id': warehouse.id if warehouse else False,
        })

