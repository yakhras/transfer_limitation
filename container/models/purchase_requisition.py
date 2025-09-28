# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# Extend Purchase Requisition
class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'
    
    # Direct relations
    container_ids = fields.One2many('logistics.container', 'requisition_id', string='Containers')
    bill_lading_ids = fields.One2many('logistics.bill.lading', 'requisition_id', string='Bills of Lading')
    
    # Computed fields
    container_count = fields.Integer('Container Count', compute='_compute_counts', store=True)
    bill_lading_count = fields.Integer('B/L Count', compute='_compute_counts', store=True)
    
    supplier_ref = fields.Char('Supplier Reference', copy=False, tracking=True)

    container_distribution_ids = fields.One2many('purchase.requisition.container.distribution', 'requisition_id', string='Container Distribution')
    has_container_distribution = fields.Boolean('Has Container Distribution', compute='_compute_has_container_distribution')
    
    @api.depends('container_ids', 'bill_lading_ids')
    def _compute_counts(self):
        for requisition in self:
            requisition.container_count = len(requisition.container_ids)
            requisition.bill_lading_count = len(requisition.bill_lading_ids)
    

    # Smart button action methods - ADD THESE NEW METHODS
    def action_view_containers(self):
        """Smart button action to view related containers"""
        self.ensure_one()
        action = self.env.ref('container.action_container_container').read()[0]
        
        # Always set the context for auto-population
        action['context'] = {
            'default_requisition_id': self.id,
            'default_supplier_id': self.vendor_id.id if self.vendor_id else False,
            'search_default_group_requisition': 1,
        }
        
        if len(self.container_ids) > 1:
            action['domain'] = [('requisition_id', '=', self.id)]
        elif len(self.container_ids) == 1:
            action['views'] = [(self.env.ref('container.view_logistics_container_form').id, 'form')]
            action['res_id'] = self.container_ids.id
        else:
            # No containers yet, create new one
            action['views'] = [(self.env.ref('container.view_logistics_container_form').id, 'form')]
            action['res_id'] = False
            
        return action
    

    def action_view_bill_ladings(self):
        """Smart button action to view related bills of lading"""
        self.ensure_one()
        action = self.env.ref('container.action_container_bill_lading').read()[0]
        
        # Always set the context for auto-population
        action['context'] = {
            'default_requisition_id': self.id,
            'default_shipper_id': self.vendor_id.id if self.vendor_id else False,
            'default_consignee_id': self.company_id.partner_id.id,
        }
        
        if len(self.bill_lading_ids) > 1:
            action['domain'] = [('requisition_id', '=', self.id)]
        elif len(self.bill_lading_ids) == 1:
            action['views'] = [(self.env.ref('container.view_logistics_bill_lading_form').id, 'form')]
            action['res_id'] = self.bill_lading_ids.id
        else:
            # No B/L yet, create new one
            action['views'] = [(self.env.ref('container.view_logistics_bill_lading_form').id, 'form')]
            action['res_id'] = False
            
        return action
    
    
    @api.depends('container_distribution_ids')
    def _compute_has_container_distribution(self):
        for requisition in self:
            requisition.has_container_distribution = bool(requisition.container_distribution_ids)
    

    def action_create_containers_from_distribution(self):
        """Create actual containers and container lines based on distribution"""
        self.ensure_one()
        
        if not self.container_distribution_ids:
            raise ValidationError(_('No container distribution found. Please add products to requisition first.'))
        
        # Group distribution by container number
        containers_data = {}
        
        for dist_line in self.container_distribution_ids:
            for container_num in range(1, dist_line.container_count + 1):
                container_key = f"container_{container_num}_{dist_line.product_id.id}"
                
                if container_key not in containers_data:
                    containers_data[container_key] = {
                        'container_num': container_num,
                        'products': []
                    }
                
                # Calculate quantity for this container
                if dist_line.distribution_method == 'equal':
                    qty_for_container = dist_line.qty_per_container
                else:
                    # For manual method, use the calculated qty_per_container
                    qty_for_container = dist_line.qty_per_container
                
                containers_data[container_key]['products'].append({
                    'product_id': dist_line.product_id.id,
                    'product_uom_id': dist_line.product_uom_id.id,
                    'product_qty': qty_for_container,
                    'price_unit': dist_line.product_id.standard_price,
                })
        
        # Create containers
        created_containers = []
        container_sequence = len(self.container_ids) + 1
        
        for container_data in containers_data.values():
            # Create container
            container = self.env['logistics.container'].create({
                'requisition_id': self.id,
                'supplier_id': self.vendor_id.id,
                'container_type': '40ft',  # Default, user can change
                'state': 'draft',
            })
            
            # Create container lines
            for product_data in container_data['products']:
                self.env['logistics.container.line'].create({
                    'container_id': container.id,
                    'product_id': product_data['product_id'],
                    'product_uom_id': product_data['product_uom_id'],
                    'product_qty': product_data['product_qty'],
                    'price_unit': product_data['price_unit'],
                })
            
            created_containers.append(container)
            container_sequence += 1
        
        # Force recompute and trigger form refresh
        self._compute_counts()
        
        # Return action that refreshes the current view without reload
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Requisition',
            'res_model': 'purchase.requisition',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
            'context': dict(self.env.context, 
                default_active_tab='containers',
                show_notification=True,
                notification_message=f'{len(created_containers)} containers created successfully.',
                notification_type='success'
            ),
        }
    
