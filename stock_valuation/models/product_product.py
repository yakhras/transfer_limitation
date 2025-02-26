from odoo import models, fields, api
from odoo.tools import float_is_zero, float_repr
import json




class ProductProduct(models.Model):
    _inherit = 'product.product'


    result = fields.Char('Result')
    

    
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

