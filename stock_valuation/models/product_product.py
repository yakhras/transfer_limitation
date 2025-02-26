from odoo import models, fields, api
from odoo.tools import float_is_zero, float_repr
import json




class ProductProduct(models.Model):
    _inherit = 'product.product'


    result = fields.Char('Result')
    location_cost_ids = fields.One2many('product.location.cost', 'product_id', string='Location Costs')
    

    
    # def _prepare_out_svl_vals(self, quantity, company):
    #     """Prepare the values for a stock valuation layer created by a delivery,
    #     using list_price instead of standard_price.

    #     :param quantity: the quantity to value, expressed in `self.uom_id`
    #     :return: values to use in a call to create
    #     :rtype: dict
    #     """
    #     self.ensure_one()
    #     company_id = self.env.context.get('force_company', self.env.company.id)
    #     company = self.env['res.company'].browse(company_id)
    #     currency = company.currency_id
    #     # Quantity is negative for out valuation layers.
    #     quantity = -1 * quantity
    #     vals = {
    #         'product_id': self.id,
    #         'value': currency.round(quantity * self.list_price),  # Replaced standard_price with list_price
    #         'unit_cost': self.list_price,  # Replaced standard_price with list_price
    #         'quantity': quantity,
    #     }
    #     if self.product_tmpl_id.cost_method in ('average', 'fifo'):
    #         fifo_vals = self._run_fifo(abs(quantity), company)
    #         vals['remaining_qty'] = fifo_vals.get('remaining_qty')
    #         # In case of AVCO, fix rounding issue of list_price when needed.
    #         if self.product_tmpl_id.cost_method == 'average' and not float_is_zero(self.quantity_svl, precision_rounding=self.uom_id.rounding):
    #             rounding_error = currency.round(
    #                 (self.list_price * self.quantity_svl - self.value_svl) * abs(quantity / self.quantity_svl)
    #             )
    #             if rounding_error:
    #                 # If it is bigger than the (smallest number of the currency * quantity) / 2,
    #                 # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
    #                 if abs(rounding_error) <= max((abs(quantity) * currency.rounding) / 2, currency.rounding):
    #                     vals['value'] += rounding_error
    #                     vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
    #                         '+' if rounding_error > 0 else '',
    #                         float_repr(rounding_error, precision_digits=currency.decimal_places),
    #                         currency.symbol
    #                     )
    #         if self.product_tmpl_id.cost_method == 'fifo':
    #             vals.update(fifo_vals)
    #     self.result = json.dumps(vals)
    #     return vals


    
        


    @api.depends('stock_valuation_layer_ids')
    @api.depends_context('to_date', 'company')
    def _compute_value_svl(self):
        """Compute `value_svl` and `quantity_svl`."""
        company_id = self.env.company.id
        domain = [
            ('product_id', 'in', self.ids),
            ('company_id', '=', company_id),
        ]
        if self.env.context.get('to_date'):
            to_date = fields.Datetime.to_datetime(self.env.context['to_date'])
            domain.append(('create_date', '<=', to_date))
        id = self.env.context.get('location_dest_id')
        domain.append(('stock_move_id.location_dest_id.id', '=', id))
        groups = self.env['stock.valuation.layer'].read_group(domain, ['value:sum', 'quantity:sum'], ['product_id'], orderby='id')
        
        products = self.browse()
        for group in groups:
            product = self.browse(group['product_id'][0])
            product.value_svl = self.env.company.currency_id.round(group['value'])
            product.quantity_svl = group['quantity']
            products |= product
        remaining = (self - products)
        remaining.value_svl = 0
        remaining.quantity_svl = 0

    
    def _prepare_out_svl_vals(self, quantity, company):
        """Prepare the values for a stock valuation layer created by a delivery.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        company_id = self.env.context.get('force_company', self.env.company.id)
        company = self.env['res.company'].browse(company_id)
        currency = company.currency_id
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        vals = {
            'product_id': self.id,
            'value': currency.round(quantity * self.standard_price),
            'unit_cost': self.standard_price,
            'quantity': quantity,
        }
        if self.product_tmpl_id.cost_method in ('average', 'fifo'):
            fifo_vals = self._run_fifo(abs(quantity), company)
            vals['remaining_qty'] = fifo_vals.get('remaining_qty')
            # In case of AVCO, fix rounding issue of standard price when needed.
            if self.product_tmpl_id.cost_method == 'average' and not float_is_zero(self.quantity_svl, precision_rounding=self.uom_id.rounding):
                rounding_error = currency.round(
                    (self.standard_price * self.quantity_svl - self.value_svl) * abs(quantity / self.quantity_svl)
                )
                if rounding_error:
                    # If it is bigger than the (smallest number of the currency * quantity) / 2,
                    # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                    if abs(rounding_error) <= max((abs(quantity) * currency.rounding) / 2, currency.rounding):
                        vals['value'] += rounding_error
                        vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                            '+' if rounding_error > 0 else '',
                            float_repr(rounding_error, precision_digits=currency.decimal_places),
                            currency.symbol
                        )
            if self.product_tmpl_id.cost_method == 'fifo':
                vals.update(fifo_vals)
        self.result = self.env.context
        return vals



class ProductLocationCost(models.Model):
    _name = 'product.location.cost'
    _description = 'Product Location Cost'

    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Location', required=True)
    cost = fields.Float('Cost', digits='Product Price')





    {'lang': 'en_GB', 
     'tz': 'Europe/Istanbul', 
     'system': None, 
     'subsystem': None, 
     'uid': 17, 
     'allowed_company_ids': [1, 5], 
     'params': {'menu_id': 616, 'action': 838}, 
     'action': 838, 
     'active_model': 'sale.order', 
     'active_id': 10246, 
     'active_ids': [10246], 
     'search_default_my_quotation': 1, 
     'default_partner_id': 54487, 
     'default_picking_type_id': 2, 
     'default_origin': 'S10245', 
     'default_group_id': 9276, 
     'button_validate_picking_ids': [59279], 
     'default_show_transfers': False, 
     'default_pick_ids': [[4, 59279]], 
     'location_dest_id': 5, 
     'skip_immediate': True, 
     'cancel_backorder': False, 
     'advance_accounting_pick_type_id': 2}