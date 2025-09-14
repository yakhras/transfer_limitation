# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseRequisitionContainerDistribution(models.Model):
    _name = 'purchase.requisition.container.distribution'
    _description = 'Purchase Requisition Container Distribution'
    _order = 'product_id, id'

    # Relations
    requisition_id = fields.Many2one(
        'purchase.requisition', 
        string='Purchase Requisition', 
        required=True, 
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', 
        string='Product', 
        required=True
    )
    product_uom_id = fields.Many2one(
        'uom.uom', 
        string='Unit of Measure', 
        required=True
    )
    
    # Quantities
    total_qty = fields.Float(
        'Total Quantity', 
        required=True, 
        digits='Product Unit of Measure'
    )
    container_count = fields.Integer(
        'Number of Containers', 
        required=True, 
        default=1
    )
    distribution_method = fields.Selection([
        ('equal', 'Equal Distribution'),
        ('manual', 'Manual Distribution'),
    ], string='Distribution Method', default='equal', required=True)
    
    qty_per_container = fields.Float(
        'Quantity per Container', 
        compute='_compute_qty_per_container', 
        store=True, 
        digits='Product Unit of Measure'
    )
    
    # Manual distribution fields (for future enhancement)
    manual_distribution_ids = fields.One2many(
        'purchase.requisition.container.distribution.line',
        'distribution_id',
        string='Manual Distribution'
    )
    
    @api.depends('total_qty', 'container_count', 'distribution_method')
    def _compute_qty_per_container(self):
        for line in self:
            if line.distribution_method == 'equal' and line.container_count > 0:
                line.qty_per_container = line.total_qty / line.container_count
            else:
                # For manual method, will be sum of manual lines
                line.qty_per_container = sum(line.manual_distribution_ids.mapped('qty'))
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
    

    @api.constrains('container_count')
    def _check_container_count(self):
        for line in self:
            if line.container_count < 1:
                raise ValidationError(_('Container count must be at least 1.'))
    

    @api.constrains('total_qty', 'qty_per_container', 'container_count')
    def _check_quantities(self):
        for line in self:
            if line.distribution_method == 'equal':
                expected_total = line.qty_per_container * line.container_count
                if abs(expected_total - line.total_qty) > 0.01:  # Small tolerance for floating point
                    raise ValidationError(_(
                        'Total quantity (%(total)s) does not match calculated quantity per container (%(per_container)s × %(count)s = %(calculated)s)'
                    ) % {
                        'total': line.total_qty,
                        'per_container': line.qty_per_container,
                        'count': line.container_count,
                        'calculated': expected_total
                    })

