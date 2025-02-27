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
        
        product_id = self.id  # Assuming this method runs in the product.product model
        location_id = self.env.context.get('location_id')

        if location_id and product_id:
            location_cost = self.env['product.location.cost'].search([
                ('product_id', '=', product_id),
                ('location_id', '=', location_id)
            ], order='id desc', limit=1)  # Get the most recent record

            cost_value = location_cost.cost if location_cost else 0.0
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        vals = {
            'product_id': product_id,
            'value': currency.round(quantity * cost_value),
            'unit_cost': cost_value,
            'quantity': quantity,
        }
        if self.product_tmpl_id.cost_method in ('average', 'fifo'):
            fifo_vals = self._run_fifo(abs(quantity), company)
            vals['remaining_qty'] = fifo_vals.get('remaining_qty')
            # In case of AVCO, fix rounding issue of standard price when needed.
            if self.product_tmpl_id.cost_method == 'average' and not float_is_zero(self.quantity_svl, precision_rounding=self.uom_id.rounding):
                rounding_error = currency.round(
                    (cost_value * self.quantity_svl - self.value_svl) * abs(quantity / self.quantity_svl)
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
        return vals


    def _run_fifo(self, quantity, company):
            self.ensure_one()

            # Find back incoming stock valuation layers (called candidates here) to value `quantity`.
            qty_to_take_on_candidates = quantity
            id = self.env.context.get('location_dest_id')
            candidates = self.env['stock.valuation.layer'].sudo().search([
                ('product_id', '=', self.id),
                ('remaining_qty', '>', 0),
                ('company_id', '=', company.id),
                ('stock_move_id.location_dest_id.id', '=', id)
            ])
            self.result = candidates
            new_standard_price = 0
            tmp_value = 0  # to accumulate the value taken on the candidates
            for candidate in candidates:
                qty_taken_on_candidate = min(qty_to_take_on_candidates, candidate.remaining_qty)

                candidate_unit_cost = candidate.remaining_value / candidate.remaining_qty
                new_standard_price = candidate_unit_cost
                value_taken_on_candidate = qty_taken_on_candidate * candidate_unit_cost
                value_taken_on_candidate = candidate.currency_id.round(value_taken_on_candidate)
                new_remaining_value = candidate.remaining_value - value_taken_on_candidate

                candidate_vals = {
                    'remaining_qty': candidate.remaining_qty - qty_taken_on_candidate,
                    'remaining_value': new_remaining_value,
                }

                candidate.write(candidate_vals)

                qty_to_take_on_candidates -= qty_taken_on_candidate
                tmp_value += value_taken_on_candidate

                if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                    if float_is_zero(candidate.remaining_qty, precision_rounding=self.uom_id.rounding):
                        next_candidates = candidates.filtered(lambda svl: svl.remaining_qty > 0)
                        new_standard_price = next_candidates and next_candidates[0].unit_cost or new_standard_price
                    break

            # Update the standard price with the price of the last used candidate, if any.
            if new_standard_price and self.cost_method == 'fifo':
                self.sudo().with_company(company.id).with_context(disable_auto_svl=True).standard_price = new_standard_price

            # If there's still quantity to value but we're out of candidates, we fall in the
            # negative stock use case. We chose to value the out move at the price of the
            # last out and a correction entry will be made once `_fifo_vacuum` is called.
            vals = {}
            if float_is_zero(qty_to_take_on_candidates, precision_rounding=self.uom_id.rounding):
                vals = {
                    'value': -tmp_value,
                    'unit_cost': tmp_value / quantity,
                }
            else:
                assert qty_to_take_on_candidates > 0
                last_fifo_price = new_standard_price or self.standard_price
                negative_stock_value = last_fifo_price * -qty_to_take_on_candidates
                tmp_value += abs(negative_stock_value)
                vals = {
                    'remaining_qty': -qty_to_take_on_candidates,
                    'value': -tmp_value,
                    'unit_cost': last_fifo_price,
                }
            return vals


class ProductLocationCost(models.Model):
    _name = 'product.location.cost'
    _description = 'Product Location Cost'

    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Location', required=True)
    cost = fields.Float('Cost', digits='Product Price')

