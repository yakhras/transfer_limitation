# -*- coding: utf-8 -*-

from odoo import models,fields, api




class StockLocation(models.Model):
    _inherit = 'stock.location'


    result = fields.Text('Result')

    def action_custom_svl_summary(self):
        for location in self:
            result_positive = {}
            result_negative = {}
            result = []
            domain = ['|',("stock_move_id.location_id.id","=",location.id),("stock_move_id.location_dest_id.id","=",location.id)]
            groups = self.env['stock.valuation.layer'].read_group(domain, ['value:sum', 'quantity:sum'], ['product_id'], orderby='id')
            for group in groups:
                product = self.browse(group['product_id'][0])
                value_svl = self.env.company.currency_id.round(group['value'])
                quantity_svl = group['quantity']

                if value_svl > 0 and quantity_svl > 0:
                    # line = (
                    #     f"Location: {location.name} (ID: {location.id})\n"
                    #     f"Product ID: {product.id}\n"
                    #     f"Quantity SVL: {quantity_svl}\n"
                    #     f"Value SVL: {value_svl}\n"
                    #     "-------------------------"
                    # )
                    # result_positive.append(line)
                    location_products = result_positive.setdefault(location.id, {})
                    location_products[product.id] = {
                        'value_svl': value_svl,
                        'quantity_svl': quantity_svl,
                    }

                elif value_svl < 0 and quantity_svl < 0:
                    # line = (
                    #     f"Location: {location.name} (ID: {location.id})\n"
                    #     f"Product ID: {product.id}\n"
                    #     f"Quantity SVL: {quantity_svl}\n"
                    #     f"Value SVL: {value_svl}\n"
                    #     "-------------------------"
                    # )
                    # result_negative.append(line)
                    location_products = result_negative.setdefault(location.id, {})
                    location_products[product.id] = {
                        'value_svl': value_svl,
                        'quantity_svl': quantity_svl,
                    }

                else:
                    line = (
                        f"Location: {location.name} (ID: {location.id})\n"
                        f"Product ID: {product.id}\n"
                        f"Quantity SVL: {quantity_svl}\n"
                        f"Value SVL: {value_svl}\n"
                        "-------------------------"
                    )
                    result.append(line)
            res_po = self.create_po(result_negative)
            res_so = self.create_so(result_positive)
            # self.result = res_so
            action = {
                'name': f'SVL Summary for {location.name}',
                'type': 'ir.actions.act_window',
                'res_model': 'stock.valuation.layer',
                'view_mode': 'tree,form',
                'domain': domain,
                'context': dict(self.env.context),
            }

            # return result_negative, result_positive, result
            return action
        
    def create_po(self, po_line):
        vendor = self.env['res.partner'].browse(25)
        created_pos = []

        for location_id, products in po_line.items():
            order_line = []
            warehouse = self.env['stock.location'].browse(location_id).warehouse_id
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', warehouse.id)
            ], limit=1)

            for product_id, values in products.items():
                product_qty = abs(values['quantity_svl'])
                price_unit = abs(values['value_svl']) / product_qty 

                order_line.append((0, 0, {
                    'product_id': product_id,
                    'product_qty': product_qty,
                    'price_unit': price_unit,
                }))

            # Now create PO with order lines for this location
            po = self.env['purchase.order'].create({
                'partner_id': vendor.id,
                'order_line': order_line,
                'picking_type_id': picking_type.id,
            })
            created_pos.append(po)

        return

    

    def create_so(self, so_line):
        vendor = self.env['res.partner'].browse(25)
        order_line = []
        for location_id, products in so_line.items():
            for product_id, values in products.items():
                unit_cost = values['value_svl'] / values['quantity_svl']
                product_id.standard_price = unit_cost
                product_qty = abs(values['quantity_svl'])
                price_unit = 1.0

                order_line.append((0, 0, {
                    'product_id': product_id,
                    'product_qty': product_qty,
                    'price_unit': price_unit,
                }))
            
        # Create a sale order
        so = self.env['sale.order'].create({
            'partner_id': vendor.id,  # Replace with the actual vendor ID
            'order_line': order_line,
        })
        return so
            