# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# Extend Purchase Order
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    # Direct relations
    container_ids = fields.One2many('logistics.container', 'purchase_order_ids', string='Containers')
    bill_lading_id = fields.Many2one('logistics.bill.lading', string='Bill of Lading')
    
    # Computed fields
    container_count = fields.Integer('Container Count', compute='_compute_container_count', store=True)
    
    @api.depends('container_ids')
    def _compute_container_count(self):
        for order in self:
            order.container_count = len(order.container_ids)
    
    @api.constrains('requisition_id', 'bill_lading_id')
    def _check_bill_lading_requisition_consistency(self):
        for order in self:
            if order.requisition_id and order.bill_lading_id:
                if order.bill_lading_id.requisition_id != order.requisition_id:
                    raise ValidationError(_(
                        'Purchase Order %s: Bill of Lading must belong to the same requisition (%s) as the purchase order.'
                    ) % (order.name, order.requisition_id.name))
