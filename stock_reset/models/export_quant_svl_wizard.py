import io
import base64
from collections import defaultdict
from odoo import models, fields
from odoo.tools import date_utils
import xlsxwriter

class ProductExportQuantSVL(models.TransientModel):
    _name = 'export.quant.svl.wizard'
    _description = 'Export Quant and SVL Summary'

    file_data = fields.Binary("File")
    file_name = fields.Char("Filename")

    def action_export_all_products_quant_svl(self):
        # Prepare output stream and workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet("Product Quant & SVL")

        # Headers
        headers = ['Product', 'Internal Quant Qty', 'SVL Qty', 'SVL Value', 'Match Status', 'Unit Cost', 'Standard Price']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # Data rows
        row = 1
        products = self.env['product.product'].search([('type', '=', 'product')])
        product_data = {}
        for product in products:
            # Internal Quant Quantity
            quant_records = self.env['stock.quant'].search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal'),
            ])

            quant_qty = sum(quant_records.mapped('quantity'))
            warehouse_quantities = {}
            for quant in quant_records:
                warehouse = quant.location_id.warehouse_id
                warehouse_quantities.setdefault(warehouse, 0.0)
                warehouse_quantities[warehouse] += quant.quantity

            

            # SVL (internal) — filter by location if needed
            domain = [('product_id', '=', product.id)]
            svl_records = self.env['stock.valuation.layer'].search(domain)
            svl_qty = sum(svl_records.mapped('quantity'))
            svl_value = round(sum(svl_records.mapped('value')))

            match_status = "Matched" if round(quant_qty, 2) == round(svl_qty, 2) else "Not Matched"
            unit_cost = svl_value / svl_qty if svl_qty else 0.0
            product.standard_price = unit_cost

            product_data[product.id] = {
                'product': product.display_name,
                'quant_qty': quant_qty,
                'svl_qty': svl_qty,
                'svl_value': svl_value,
                'match_status': match_status,
                'unit_cost': unit_cost,
                'standard_price': product.standard_price,
                'warehouse_quantities': warehouse_quantities,
            }
            

            # Write data row
            worksheet.write(row, 0, product.display_name)
            worksheet.write(row, 1, quant_qty)
            worksheet.write(row, 2, svl_qty)
            worksheet.write(row, 3, svl_value)
            worksheet.write(row, 4, match_status)
            worksheet.write(row, 5, unit_cost)
            worksheet.write(row, 6, product.standard_price)
            worksheet.write(row, 7, str(product_data))
            
            row += 1

        workbook.close()
        output.seek(0)

        # Prepare wizard file to download
        file_data = base64.b64encode(output.read())
        filename = 'products_quant_svl_report.xlsx'

        wizard = self.create({
            'file_data': file_data,
            'file_name': filename
        })

        order_line = []
        vendor = self.env['res.partner'].browse(25)
        for product_id, values in product_data.items():
            for warehouse, qty in values['warehouse_quantities'].items():
                if values['svl_qty'] == 0:
                    continue
                product_qty = abs(qty)
                price_unit = 1.0

                order_line.append((0, 0, {
                    'product_id': product_id,
                    'warehouses_id': warehouse.id,
                    'product_uom_qty': product_qty,
                    'price_unit': price_unit,
                }))
        so = self.env['sale.order'].create({
            'partner_id': vendor.id,  # Replace with the actual vendor ID
            'order_line': order_line,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{wizard._name}/{wizard.id}/file_data/{filename}?download=true',
            'target': 'new'
        }


    def action_export_all_locations_quant_svl(self):
        # Prepare output stream and workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet("Location Quant & SVL")

        # Headers
        headers = ['Location', 'Product', 'SVL Qty', 'SVL Value']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # Data rows
        row = 1
        locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        location_data = {}
        for location in locations:
            domain = ['|',("stock_move_id.location_id.id","=",location.id),("stock_move_id.location_dest_id.id","=",location.id)]
            groups = self.env['stock.valuation.layer'].read_group(domain, ['value:sum', 'quantity:sum'], ['product_id'], orderby='id')
            for group in groups:
                product_id = group['product_id'][0]
                product = self.env['product.product'].browse(product_id)
                value_svl = self.env.company.currency_id.round(group['value'])
                quantity_svl = group['quantity']
                location_data.setdefault(location.id, {})[product_id] = {
                'product': product,
                'svl_qty': quantity_svl,
                'svl_value': value_svl,
            }

            # Write data row
            product_locations = {}
            transfer_map = {}
            for location_id, products in location_data.items():
                location = self.env['stock.location'].browse(location_id)
                for product_id, data in products.items():
                    svl_qty = data['svl_qty']
                    if svl_qty < 0:
                        direction = 'sell'
                    elif svl_qty > 0:
                        direction = 'buy'
                    else:
                        continue
                    product_locations.setdefault(product_id, {}).setdefault(direction, {})[location.id] = {
                        'svl_qty': svl_qty,
                    }
                    worksheet.write(row, 0, location.id)
                    worksheet.write(row, 1, data['product'].display_name)
                    worksheet.write(row, 2, data['svl_qty'])
                    worksheet.write(row, 3, data['svl_value'])
                    worksheet.write(row, 4, str(location_data))
                    row += 1
            
            
            for product_id, directions in product_locations.items():
                buy_locations = directions.get('buy', {})
                sell_locations = directions.get('sell', {})

                for buy_loc_id, buy_data in buy_locations.items():
                    buy_qty = buy_data['svl_qty']
                    if buy_qty <= 0:
                        continue

                    for sell_loc_id, sell_data in sell_locations.items():
                        sell_qty = abs(sell_data['svl_qty'])
                        if sell_qty <= 0:
                            continue

                        transfer_qty = min(buy_qty, sell_qty)
                        route_key = (sell_loc_id, buy_loc_id)

                        transfer_map.setdefault(route_key, []).append({
                            'product_id': product_id,
                            'qty_to_transfer': transfer_qty,
                        })

            # location.result = product_locations

        workbook.close()
        output.seek(0)
        

        # Prepare wizard file to download
        file_data = base64.b64encode(output.read())
        filename = 'locations_quant_svl_report.xlsx'

        wizard = self.create({
            'file_data': file_data,
            'file_name': filename
        })

        Picking = self.env['stock.picking']
        picking_type = self.env['stock.picking.type'].search([('sequence_code', '=', 'INT')], limit=1)


        for (buy_loc_id, sell_loc_id), products in transfer_map.items():
            picking = Picking.create({
                'picking_type_id': picking_type.id,
                'location_id': buy_loc_id,
                'location_dest_id': sell_loc_id,
            })

            move_vals = []
            for product in products:
                product_id = product['product_id']
                qty = product['qty_to_transfer']

                move_vals.append((0, 0, {
                    'product_id': product_id,
                    'product_uom_qty': qty,
                    'name': self.env['product.product'].browse(product_id).display_name,
                    'product_uom': self.env['product.product'].browse(product_id).uom_id.id,
                    'location_id': buy_loc_id,
                    'location_dest_id': sell_loc_id,
                }))

            picking.write({
                'move_ids_without_package': move_vals
            })


        # order_line = []
        # vendor = self.env['res.partner'].browse(25)
        # for product_id, values in product_data.items():
        #     for warehouse, qty in values['warehouse_quantities'].items():
        #         if values['svl_qty'] == 0:
        #             continue
        #         product_qty = abs(qty)
        #         price_unit = 1.0

        #         order_line.append((0, 0, {
        #             'product_id': product_id,
        #             'warehouses_id': warehouse.id,
        #             'product_uom_qty': product_qty,
        #             'price_unit': price_unit,
        #         }))
        # so = self.env['sale.order'].create({
        #     'partner_id': vendor.id,  # Replace with the actual vendor ID
        #     'order_line': order_line,
        # })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{wizard._name}/{wizard.id}/file_data/{filename}?download=true',
            'target': 'new'
        }

