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
        self.ensure_one()
        return {
            'price_unit': self.price_unit,
            'currency': self.currency_id,
            'quantity': self.product_qty,
            'product': self.product_id,
            'partner': self.partner_id,
        }
