# -*- coding: utf-8 -*-
import json

from odoo import models, fields, api, _



class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"



    tax_totals_json = fields.Char(compute='_compute_tax_totals_json')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all', tracking=True)


    @api.depends('line_ids.taxes_id', 'line_ids.price_subtotal', 'amount_total', 'amount_untaxed')
    def  _compute_tax_totals_json(self):
        def compute_taxes(order_line):
            return order_line.taxes_id._origin.compute_all(**order_line._prepare_compute_all_values())

        account_move = self.env['account.move']
        for order in self:
            tax_lines_data = account_move._prepare_tax_lines_data_for_totals_from_object(order.line_ids, compute_taxes)
            tax_totals = account_move._get_tax_totals(order.vendor_id, tax_lines_data, order.amount_total, order.amount_untaxed, order.currency_id)
            order.tax_totals_json = json.dumps(tax_totals)

    


    @api.depends('line_ids.price_total')
    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.line_ids:
                line._compute_amount()
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            currency = order.currency_id or order.partner_id.property_purchase_currency_id or self.env.company.currency_id
            order.update({
                'amount_untaxed': currency.round(amount_untaxed),
                'amount_tax': currency.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })
            