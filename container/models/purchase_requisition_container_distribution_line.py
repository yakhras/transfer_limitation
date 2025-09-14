# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# NEW MODEL: Manual Distribution Lines (for future enhancement)
class PurchaseRequisitionContainerDistributionLine(models.Model):
    _name = 'purchase.requisition.container.distribution.line'
    _description = 'Manual Container Distribution Line'
    _order = 'sequence, id'

    distribution_id = fields.Many2one(
        'purchase.requisition.container.distribution',
        string='Distribution',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer('Sequence', default=10)
    container_name = fields.Char('Container Name')
    qty = fields.Float('Quantity', required=True, digits='Product Unit of Measure')
    
    
    @api.constrains('qty')
    def _check_qty(self):
        for line in self:
            if line.qty <= 0:
                raise ValidationError(_('Quantity must be greater than 0.'))
