# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)


class LogisticsContainer(models.Model):
    _name = 'logistics.container'
    _description = 'Shipping Container'
    _order = 'arrival_date desc, name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information - Modified to auto-generate reference
    name = fields.Char('Container Reference', required=True, copy=False, readonly=True, 
                      default=lambda self: _('New'), tracking=True)
    container_number = fields.Char('Container Number', tracking=True, 
                                  help="Physical container number from shipping line")
    container_type = fields.Selection([
        ('20ft', '20ft Standard'),
        ('40ft', '40ft Standard'),
        ('40hc', '40ft High Cube'),
        ('45hc', '45ft High Cube'),
        ('20rf', '20ft Refrigerated'),
        ('40rf', '40ft Refrigerated'),
        ('20ot', '20ft Open Top'),
        ('40ot', '40ft Open Top'),
    ], string='Container Type', required=True, tracking=True)
    
    # Master Relations - Following hierarchy: Requisition > Purchase Order > Container > Bill of Lading
    requisition_id = fields.Many2one('purchase.requisition', string='Purchase Requisition', 
                                    required=True, tracking=True, ondelete='cascade')
    purchase_order_ids = fields.Many2many(
        'purchase.order', 
        string='Purchase Orders',
        domain="[('requisition_id', '=', requisition_id)]",
        tracking=True
    )
    
    # Compatibility field for migration - remove after fixing all references
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order (Deprecated)', 
                                       help='Deprecated field for compatibility. Use purchase_order_ids instead.')
    bill_lading_id = fields.Many2one('logistics.bill.lading', string='Bill of Lading', 
                                    tracking=True, ondelete='set null')
    
    # Physical Properties
    seal_number = fields.Char('Seal Number', tracking=True)
    weight_kg = fields.Float('Weight (KG)', digits=(12, 2))
    volume_m3 = fields.Float('Volume (M³)', digits=(10, 2))
    
    # Logistics Information
    forwarder_id = fields.Many2one('res.partner', string='Forwarding Agent', tracking=True, readonly=True)
    shipping_line_id = fields.Many2one('res.partner', string='Shipping Line', tracking=True, readonly=True)
    incoterm_id = fields.Many2one('account.incoterms', string='Incoterm', tracking=True, readonly=True)
    arrival_date = fields.Date('Arrival Date', tracking=True, readonly=True)
    departure_date = fields.Date('Departure Date', tracking=True, readonly=True)
    country_id = fields.Many2one('res.country', string='Country', related='supplier_id.country_id', store=True, tracking=True)
    tracking_number = fields.Char('Tracking Number')
    vessel_name = fields.Char('Vessel Name', readonly=True)
    voyage_number = fields.Char('Voyage Number', readonly=True)
    port_of_loading = fields.Many2one('res.country.state', string='Port of Loading', domain="[('country_id', '=', country_id)]", tracking=True, readonly=True)
    port_of_discharge = fields.Many2one('res.country.state', string='Port of Discharge', tracking=True, readonly=True)
    
    # Status Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('shipped', 'Shipped'),
        ('in_transit', 'In Transit'),
        ('arrived', 'Arrived'),
        ('antrepo', 'Antrepo'),
        ('released', 'Released'),
        ('unloading', 'Unloading'),
        ('unloaded', 'Unloaded'),
        ('at_port', 'At Port'),
        ('purchasing', 'Purchasing'),
    ], string='Status', default='draft', tracking=True, required=True)
    
    # Business Relations
    supplier_id = fields.Many2one('res.partner', string='Supplier', related='requisition_id.vendor_id', store=True, tracking=True)
    supplier_ref = fields.Char('Supplier Reference', related='requisition_id.supplier_ref', store=True, tracking=True)
    
    # Container Content
    container_line_ids = fields.One2many('logistics.container.line', 'container_id', string='Container Lines')
    
    # Financial Information
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency', store=True)
    total_value = fields.Monetary('Total Value', compute='_compute_totals', store=True, currency_field='currency_id')
    freight_cost = fields.Monetary('Freight Cost', currency_field='currency_id')
    insurance_cost = fields.Monetary('Insurance Cost', currency_field='currency_id')
    customs_duty = fields.Monetary('Customs Duty', currency_field='currency_id')
    other_charges = fields.Monetary('Other Charges', currency_field='currency_id')
    total_cost = fields.Monetary('Total Cost', compute='_compute_total_cost', store=True, currency_field='currency_id')
    
    # Computed Fields
    total_qty = fields.Float('Total Quantity', compute='_compute_totals', store=True)
    product_count = fields.Integer('Product Count', compute='_compute_totals', store=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', compute='_compute_company', store=True)
    
    @api.model
    def create(self, vals):
        """Override create to generate sequence number and set supplier"""
        if not vals.get('name') or vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('logistics.container') or _('New')
        
        # If requisition is provided, ensure supplier is set from requisition
        if vals.get('requisition_id'):
            requisition = self.env['purchase.requisition'].browse(vals['requisition_id'])
            if requisition.vendor_id and not vals.get('supplier_id'):
                vals['supplier_id'] = requisition.vendor_id.id
        
        # Remove any old field references that might cause issues
        if 'purchase_order_id' in vals:
            _logger.warning("Deprecated field 'purchase_order_id' found in vals. Use 'purchase_order_ids' instead.")
            vals.pop('purchase_order_id', None)
        
        # Create the record
        record = super(LogisticsContainer, self).create(vals)
        
        # Force recompute related fields if needed (fallback)
        if record.requisition_id and not record.supplier_id:
            record.invalidate_cache(['supplier_id'])
            record._compute_field('supplier_id')
        
        return record
    

    @api.depends('container_line_ids.product_qty', 'container_line_ids.price_subtotal')
    def _compute_totals(self):
        for container in self:
            container.total_qty = sum(container.container_line_ids.mapped('product_qty'))
            container.total_value = sum(container.container_line_ids.mapped('price_subtotal'))
            container.product_count = len(container.container_line_ids)
    

    @api.depends('total_value', 'freight_cost', 'insurance_cost', 'customs_duty', 'other_charges')
    def _compute_total_cost(self):
        for container in self:
            container.total_cost = (container.total_value + container.freight_cost + 
                                  container.insurance_cost + container.customs_duty + 
                                  container.other_charges)
    

    @api.constrains('requisition_id', 'purchase_order_ids')
    def _check_purchase_order_requisition_consistency(self):
        for container in self:
            for purchase_order in container.purchase_order_ids:
                if purchase_order.requisition_id not in container.requisition_id:
                    raise ValidationError(_(
                        'Container %s: Purchase Order %s must belong to the same requisition (%s).'
                    ) % (container.name, purchase_order.name, container.requisition_id.name))
    
    @api.constrains('bill_lading_id', 'requisition_id')
    def _check_bill_lading_requisition_consistency(self):
        for container in self:
            if container.bill_lading_id and container.requisition_id:
                if container.requisition_id not in container.bill_lading_id.requisition_id:
                    raise ValidationError(_(
                        "Container %s is linked to requisition %s, "
                        "which is not among the requisitions of Bill of Lading %s."
                    ) % (
                        container.name,
                        container.requisition_id.display_name,
                        container.bill_lading_id.name
                    ))

    

    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        if self.requisition_id:
            # Filter purchase orders by requisition
            return {
                'domain': {
                    'purchase_order_ids': [('requisition_id', '=', self.requisition_id.id)],
                    'bill_lading_id': [('requisition_id', '=', self.requisition_id.id)]
                }
            }
    

    @api.onchange('purchase_order_ids')
    def _onchange_purchase_order_ids(self):
        if self.purchase_order_ids:
            # Auto-set requisition from first purchase order if not set
            if not self.requisition_id and self.purchase_order_ids[0].requisition_id:
                self.requisition_id = self.purchase_order_ids[0].requisition_id
    

    @api.onchange('country_id')
    def _onchange_country_id(self):
        """Reset port of loading when country changes"""
        if self.country_id:
            # Clear port of loading if it doesn't belong to the new country
            if self.port_of_loading and self.port_of_loading.country_id != self.country_id:
                self.port_of_loading = False
            
            # Return domain to filter states by country for port of loading
            return {
                'domain': {
                    'port_of_loading': [('country_id', '=', self.country_id.id)]
                }
            }
        else:
            # If no country, clear port of loading
            self.port_of_loading = False
            return {
                'domain': {
                    'port_of_loading': []
                }
            }
    

    # State Management Methods
    def action_ship(self):
        for record in self:
            record.write({
                'state': 'shipped',
                'departure_date': fields.Date.context_today(record)
            })
        return True
    

    def action_in_transit(self):
        for record in self:
            record.write({'state': 'in_transit'})
        return True
    

    def action_arrived(self):
        for record in self:
            vals = {'state': 'arrived'}
            if not record.arrival_date:
                vals['arrival_date'] = fields.Date.context_today(record)
            record.write(vals)
        return True
    

    def action_antrepo(self):
        for record in self:
            record.write({'state': 'antrepo'})
        return True
    

    def action_released(self):
        for record in self:
            record.write({'state': 'released'})
        return True
    

    def action_start_unloading(self):
        for record in self:
            record.write({'state': 'unloading'})
        return True
    

    def action_unloaded(self):
        for record in self:
            record.write({'state': 'unloaded'})
        return True
    

    def action_at_port(self):
        for record in self:
            record.write({'state': 'at_port'})
        return True
    

    def action_purchasing(self):
        for record in self:
            record.write({'state': 'purchasing'})
        return True
    

    def action_reset_to_draft(self):
        for record in self:
            record.write({'state': 'draft'})
        return True
    

    @api.constrains('arrival_date', 'departure_date')
    def _check_dates(self):
        for container in self:
            if container.arrival_date and container.departure_date:
                if container.arrival_date < container.departure_date:
                    raise ValidationError(_('Arrival date cannot be before departure date.'))


    @api.onchange('requisition_id')
    def _onchange_requisition_id_details(self):
        """Filter domains when requisition is selected"""
        if self.requisition_id:
            # Filter purchase orders and bill of lading by requisition
            return {
                'domain': {
                    'purchase_order_ids': [('requisition_id', '=', self.requisition_id.id)],
                    'bill_lading_id': [('requisition_id', '=', self.requisition_id.id)]
                }
            }


    purchase_order_count = fields.Integer(
        'Purchase Order Count', 
        compute='_compute_related_counts', 
        store=True
    )
    
    @api.depends('purchase_order_ids', 'requisition_id')
    def _compute_related_counts(self):
        for container in self:
            # Count purchase orders - direct POs plus any from requisition
            po_count = len(container.purchase_order_ids)
            if container.requisition_id:
                po_count += len(container.requisition_id.purchase_ids - container.purchase_order_ids)
            container.purchase_order_count = po_count
    

    def action_view_purchase_requisition(self):
        """Smart button to view related purchase requisition"""
        self.ensure_one()
        if not self.requisition_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.requisition',
            'res_id': self.requisition_id.id,  # Single record - no .ids needed
            'view_mode': 'form',
            'target': 'current',
        }
    

    def action_view_purchase_orders(self):
        """Smart button to view related purchase orders"""
        self.ensure_one()
        
        # Collect purchase orders
        purchase_orders = self.purchase_order_ids
        
        # Add purchase orders from requisition if any
        if self.requisition_id:
            purchase_orders |= self.requisition_id.purchase_ids
        
        if not purchase_orders:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Purchase Orders'),
                    'message': _('No purchase orders found for this container.'),
                    'type': 'warning',
                }
            }
        
        # Try different possible action references
        action_ref = None
        possible_actions = [
            'purchase.purchase_rfq',
            'purchase.purchase_order_action_generic',
            'purchase.action_purchase_order_report_all',
            'purchase.purchase_order_action'
        ]
        
        for action_name in possible_actions:
            try:
                action_ref = self.env.ref(action_name)
                break
            except ValueError:
                continue
        
        # Fallback to manual action definition if no reference found
        if not action_ref:
            action = {
                'name': _('Purchase Orders'),
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'tree,form',
                'target': 'current',
                'context': self.env.context,
            }
        else:
            action = action_ref.read()[0]
        
        if len(purchase_orders) > 1:
            action['domain'] = [('id', 'in', purchase_orders.ids)]
            action['view_mode'] = 'tree,form'
        else:
            action['view_mode'] = 'form'
            action['res_id'] = purchase_orders.id
            action['views'] = [(False, 'form')]
        
        return action
    
    