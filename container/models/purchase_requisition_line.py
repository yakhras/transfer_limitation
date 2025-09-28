# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'
    
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-create distribution record when requisition line is created"""
        lines = super().create(vals_list)
        
        for line in lines:
            # Auto-create container distribution record
            self.env['purchase.requisition.container.distribution'].create({
                'requisition_id': line.requisition_id.id,
                'product_id': line.product_id.id,
                'product_uom_id': line.product_uom_id.id,
                'total_qty': line.product_qty,
                'price_unit': line.price_unit,
                'container_count': 1,  # Default to 1 container
                'distribution_method': 'equal',
            })
        
        return lines
    

    def write(self, vals):
        """Update distribution record when requisition line is updated"""
        result = super().write(vals)
        
        # If product or quantity changed, update distribution
        if 'product_id' in vals or 'product_qty' in vals or 'product_uom_id' in vals:
            for line in self:
                # Find existing distribution record
                distribution = self.env['purchase.requisition.container.distribution'].search([
                    ('requisition_id', '=', line.requisition_id.id),
                    ('product_id', '=', line.product_id.id)
                ], limit=1)
                
                if distribution:
                    # Update existing distribution
                    distribution.write({
                        'total_qty': line.product_qty,
                        'product_uom_id': line.product_uom_id.id,
                    })
                else:
                    # Create new distribution if it doesn't exist
                    self.env['purchase.requisition.container.distribution'].create({
                        'requisition_id': line.requisition_id.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'total_qty': line.product_qty,
                        'price_unit': line.price_unit,
                        'container_count': 1,
                        'distribution_method': 'equal',
                    })
        
        return result
    

    def unlink(self):
        """Remove distribution record when requisition line is deleted"""
        # Store distribution records to delete
        distributions_to_delete = self.env['purchase.requisition.container.distribution']
        
        for line in self:
            distribution = self.env['purchase.requisition.container.distribution'].search([
                ('requisition_id', '=', line.requisition_id.id),
                ('product_id', '=', line.product_id.id)
            ])
            distributions_to_delete |= distribution
        
        result = super().unlink()
        
        # Delete related distribution records
        distributions_to_delete.unlink()
        
        return result

