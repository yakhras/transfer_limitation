# -*- coding: utf-8 -*-

from odoo import models,fields, api
from odoo.tools.float_utils import float_round
from odoo.osv import expression




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
   


class Product(models.Model):
    _inherit = "product.product"

    quantity = fields.Float(
            'Quantity', compute='_compute_quantities',
            digits='Product Unit of Measure', compute_sudo=False)
    


    @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state')
    @api.depends_context(
        'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
        'location', 'warehouse')
    def _compute_quantities(self):
        products = self.filtered(lambda p: p.type != 'service')
        res = products._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))
        for product in products:
            product.quantity = res[product.id]['quantity']
            product.qty_available = res[product.id]['qty_available']
            product.incoming_qty = res[product.id]['incoming_qty']
            product.outgoing_qty = res[product.id]['outgoing_qty']
            product.virtual_available = res[product.id]['virtual_available']
            product.free_qty = res[product.id]['free_qty']
        # Services need to be set with 0.0 for all quantities
        services = self - products
        services.qty_available = 0.0
        services.quantity = 0.0
        services.incoming_qty = 0.0
        services.outgoing_qty = 0.0
        services.virtual_available = 0.0
        services.free_qty = 0.0


    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
            domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
            domain_quant = [('product_id', 'in', self.ids)] + domain_quant_loc
            dates_in_the_past = False
            # only to_date as to_date will correspond to qty_available
            to_date = fields.Datetime.to_datetime(to_date)
            if to_date and to_date < fields.Datetime.now():
                dates_in_the_past = True

            domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
            domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
            if lot_id is not None:
                domain_quant += [('lot_id', '=', lot_id)]
            if owner_id is not None:
                domain_quant += [('owner_id', '=', owner_id)]
                domain_move_in += [('restrict_partner_id', '=', owner_id)]
                domain_move_out += [('restrict_partner_id', '=', owner_id)]
            if package_id is not None:
                domain_quant += [('package_id', '=', package_id)]
            if dates_in_the_past:
                domain_move_in_done = list(domain_move_in)
                domain_move_out_done = list(domain_move_out)
            if from_date:
                date_date_expected_domain_from = [('date', '>=', from_date)]
                domain_move_in += date_date_expected_domain_from
                domain_move_out += date_date_expected_domain_from
            if to_date:
                date_date_expected_domain_to = [('date', '<=', to_date)]
                domain_move_in += date_date_expected_domain_to
                domain_move_out += date_date_expected_domain_to

            Move = self.env['stock.move'].with_context(active_test=False)
            Quant = self.env['stock.quant'].with_context(active_test=False)
            domain_move_in_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
            domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
            moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
            moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
            quants_res = dict((item['product_id'][0], (item['quantity'], item['reserved_quantity'])) for item in Quant.read_group(domain_quant, ['product_id', 'quantity', 'reserved_quantity'], ['product_id'], orderby='id'))
            if dates_in_the_past:
                # Calculate the moves that were done before now to calculate back in time (as most questions will be recent ones)
                domain_move_in_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_in_done
                domain_move_out_done = [('state', '=', 'done'), ('date', '>', to_date)] + domain_move_out_done
                moves_in_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_done, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
                moves_out_res_past = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_done, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
                

            res = dict()
            for product in self.with_context(prefetch_fields=False):
                origin_product_id = product._origin.id
                product_id = product.id
                if not origin_product_id:
                    res[product_id] = dict.fromkeys(
                        ['qty_available', 'free_qty', 'incoming_qty', 'outgoing_qty', 'virtual_available'],
                        0.0,
                    )
                    continue
                rounding = product.uom_id.rounding
                res[product_id] = {}
                if dates_in_the_past:
                    qty_available = quants_res.get(origin_product_id, [0.0])[0] - moves_in_res_past.get(origin_product_id, 0.0) + moves_out_res_past.get(origin_product_id, 0.0)
                    quantity_now = quants_res.get(product_id, (0.0, 0.0))[0]  # today’s physical qty
                    moves_in_after = moves_in_res_past.get(product_id, 0.0)   # incoming after to_date
                    moves_out_after = moves_out_res_past.get(product_id, 0.0) # outgoing after to_date

                    # Reverse those moves to get the past physical quantity
                    quantity_at_to_date = quants_res.get(product_id, (0.0, 0.0))[0] - moves_in_res_past.get(product_id, 0.0) + moves_out_res_past.get(product_id, 0.0)
                else:
                    qty_available = quants_res.get(origin_product_id, [0.0])[0]
                    quantity_at_to_date = quants_res.get(product_id, (0.0, 0.0))[0]
                reserved_quantity = quants_res.get(origin_product_id, [False, 0.0])[1]
                res[product_id]['quantity'] = float_round(quantity_at_to_date, precision_rounding=rounding)
                res[product_id]['qty_available'] = float_round(qty_available, precision_rounding=rounding)
                res[product_id]['free_qty'] = float_round(qty_available - reserved_quantity, precision_rounding=rounding)
                res[product_id]['incoming_qty'] = float_round(moves_in_res.get(origin_product_id, 0.0), precision_rounding=rounding)
                res[product_id]['outgoing_qty'] = float_round(moves_out_res.get(origin_product_id, 0.0), precision_rounding=rounding)
                res[product_id]['virtual_available'] = float_round(
                    qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'],
                    precision_rounding=rounding)

            return res

