# -*- coding: utf-8 -*-
import json

from odoo import models, fields, api, _



class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"


    partner_id = fields.Many2one(related='requisition_id.vendor_id', store=True,)
    currency_id = fields.Many2one(related='requisition_id.currency_id', store=True, string='Currency', readonly=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)
    tax_totals_json = fields.Char(compute='_compute_tax_totals_json')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=True)



    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            taxes = line.taxes_id.compute_all(**line._prepare_compute_all_values())
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    def _prepare_compute_all_values(self):
        # Hook method to returns the different argument values for the
        # compute_all method, due to the fact that discounts mechanism
        # is not implemented yet on the purchase orders.
        # This method should disappear as soon as this feature is
        # also introduced like in the sales module.
        self.ensure_one()
        return {
            'price_unit': self.price_unit,
            'currency': self.currency_id,
            'quantity': self.product_qty,
            'product': self.product_id,
            'partner': self.partner_id,
        }
    

    @api.depends('taxes_id', 'price_subtotal', 'amount_total', 'amount_untaxed')
    def  _compute_tax_totals_json(self):
        def compute_taxes(order_line):
            return order_line.taxes_id._origin.compute_all(**order_line._prepare_compute_all_values())

        account_move = self.env['account.move']
        for order in self:
            tax_lines_data = account_move._prepare_tax_lines_data_for_totals_from_object(order, compute_taxes)
            tax_totals = account_move._get_tax_totals(order.partner_id, tax_lines_data, order.amount_total, order.amount_untaxed, order.currency_id)
            order.tax_totals_json = json.dumps(tax_totals)

    
    @api.depends('price_total')
    def _amount_all(self):
        self.ensure_one()
        amount_untaxed = amount_tax = 0.0
        for line in self:
            line._compute_amount()
            amount_untaxed += line.price_subtotal
            amount_tax += line.price_tax
        currency = self.currency_id or self.env.company.currency_id
        self.update({
            'amount_untaxed': currency.round(amount_untaxed),
            'amount_tax': currency.round(amount_tax),
            'amount_total': amount_untaxed + amount_tax,
        })