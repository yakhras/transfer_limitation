# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase Orders', 
                                         tracking=True)
    bill_lading_id = fields.Many2one('logistics.bill.lading', string='Bill of Lading', 
                                    tracking=True, ondelete='set null')
    
    # Physical Properties
    seal_number = fields.Char('Seal Number', tracking=True)
    weight_kg = fields.Float('Weight (KG)', digits=(12, 2))
    volume_m3 = fields.Float('Volume (M³)', digits=(10, 2))
    
    # Logistics Information
    arrival_date = fields.Date('Arrival Date', tracking=True)
    departure_date = fields.Date('Departure Date', tracking=True)
    location = fields.Char('Current Location', tracking=True)
    tracking_number = fields.Char('Tracking Number')
    vessel_name = fields.Char('Vessel Name')
    voyage_number = fields.Char('Voyage Number')
    port_of_loading = fields.Char('Port of Loading')
    port_of_discharge = fields.Char('Port of Discharge')
    
    # Status Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('shipped', 'Shipped'),
        ('in_transit', 'In Transit'),
        ('arrived', 'Arrived'),
        ('customs', 'In Customs'),
        ('released', 'Released'),
        ('unloading', 'Unloading'),
        ('unloaded', 'Unloaded'),
        ('empty', 'Empty'),
        ('returned', 'Returned'),
    ], string='Status', default='draft', tracking=True, required=True)
    
    # Business Relations
    supplier_id = fields.Many2one('res.partner', string='Supplier', 
                                 related='requisition_id.vendor_id', store=True, tracking=True)
    
    # Container Content
    container_line_ids = fields.One2many('logistics.container.line', 'container_id', 
                                        string='Container Lines')
    
    # Financial Information
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 compute='_compute_currency', store=True)
    total_value = fields.Monetary('Total Value', compute='_compute_totals', 
                                 store=True, currency_field='currency_id')
    freight_cost = fields.Monetary('Freight Cost', currency_field='currency_id')
    insurance_cost = fields.Monetary('Insurance Cost', currency_field='currency_id')
    customs_duty = fields.Monetary('Customs Duty', currency_field='currency_id')
    other_charges = fields.Monetary('Other Charges', currency_field='currency_id')
    total_cost = fields.Monetary('Total Cost', compute='_compute_total_cost', 
                                store=True, currency_field='currency_id')
    
    # Computed Fields
    total_qty = fields.Float('Total Quantity', compute='_compute_totals', store=True)
    product_count = fields.Integer('Product Count', compute='_compute_totals', store=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', 
                                compute='_compute_company', store=True)
    
    @api.model
    def create(self, vals):
        """Override create to generate sequence number"""
        if not vals.get('name') or vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('logistics.container') or _('New')
        
        return super(LogisticsContainer, self).create(vals)
    
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
    
    # @api.constrains('requisition_id', 'purchase_order_id')
    # def _check_purchase_order_requisition_consistency(self):
    #     for container in self:
    #         if container.purchase_order_id.requisition_id != container.requisition_id:
    #             raise ValidationError(_(
    #                 'Container %s: Purchase Order must belong to the same requisition (%s).'
    #             ) % (container.name, container.requisition_id.name))
    
    @api.constrains('bill_lading_id', 'requisition_id')
    def _check_bill_lading_requisition_consistency(self):
        for container in self:
            if container.bill_lading_id and container.bill_lading_id.requisition_id != container.requisition_id:
                raise ValidationError(_(
                    'Container %s: Bill of Lading must belong to the same requisition (%s).'
                ) % (container.name, container.requisition_id.name))
    
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
    
    # State Management Methods
    def action_ship(self):
        self.state = 'shipped'
        self.departure_date = fields.Date.context_today(self)
    
    def action_in_transit(self):
        self.state = 'in_transit'
    
    def action_arrived(self):
        self.state = 'arrived'
        if not self.arrival_date:
            self.arrival_date = fields.Date.context_today(self)
    
    def action_customs(self):
        self.state = 'customs'
    
    def action_released(self):
        self.state = 'released'
    
    def action_start_unloading(self):
        self.state = 'unloading'
    
    def action_unloaded(self):
        self.state = 'unloaded'
    
    def action_empty(self):
        self.state = 'empty'
    
    def action_returned(self):
        self.state = 'returned'
    
    def action_reset_to_draft(self):
        self.state = 'draft'
    
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
            # Filter purchase orders by requisition
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
            'res_id': self.requisition_id.id,
            'view_mode': 'form',
            'view_type': 'form',
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
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', 
                                       tracking=True, ondelete='cascade')
    bill_lading_id = fields.Many2one('logistics.bill.lading', string='Bill of Lading', 
                                    tracking=True, ondelete='set null')
    
    # Physical Properties
    seal_number = fields.Char('Seal Number', tracking=True)
    weight_kg = fields.Float('Weight (KG)', digits=(12, 2))
    volume_m3 = fields.Float('Volume (M³)', digits=(10, 2))
    
    # Logistics Information
    arrival_date = fields.Date('Arrival Date', tracking=True)
    departure_date = fields.Date('Departure Date', tracking=True)
    location = fields.Char('Current Location', tracking=True)
    tracking_number = fields.Char('Tracking Number')
    vessel_name = fields.Char('Vessel Name')
    voyage_number = fields.Char('Voyage Number')
    port_of_loading = fields.Char('Port of Loading')
    port_of_discharge = fields.Char('Port of Discharge')
    
    # Status Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('shipped', 'Shipped'),
        ('in_transit', 'In Transit'),
        ('arrived', 'Arrived'),
        ('customs', 'In Customs'),
        ('released', 'Released'),
        ('unloading', 'Unloading'),
        ('unloaded', 'Unloaded'),
        ('empty', 'Empty'),
        ('returned', 'Returned'),
    ], string='Status', default='draft', tracking=True, required=True)
    
    # Business Relations
    supplier_id = fields.Many2one('res.partner', string='Supplier', 
                                 related='purchase_order_id.partner_id', store=True)
    
    # Container Content
    container_line_ids = fields.One2many('logistics.container.line', 'container_id', 
                                        string='Container Lines')
    
    # Financial Information
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 related='purchase_order_id.currency_id', store=True)
    total_value = fields.Monetary('Total Value', compute='_compute_totals', 
                                 store=True, currency_field='currency_id')
    freight_cost = fields.Monetary('Freight Cost', currency_field='currency_id')
    insurance_cost = fields.Monetary('Insurance Cost', currency_field='currency_id')
    customs_duty = fields.Monetary('Customs Duty', currency_field='currency_id')
    other_charges = fields.Monetary('Other Charges', currency_field='currency_id')
    total_cost = fields.Monetary('Total Cost', compute='_compute_total_cost', 
                                store=True, currency_field='currency_id')
    
    # Computed Fields
    total_qty = fields.Float('Total Quantity', compute='_compute_totals', store=True)
    product_count = fields.Integer('Product Count', compute='_compute_totals', store=True)
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', 
                                related='purchase_order_id.company_id', store=True)
    
    @api.onchange('requisition_id')
    def _onchange_requisition_id_details(self):
        """Auto-populate fields when requisition is selected"""
        if self.requisition_id:
            # Set supplier from requisition vendor
            if self.requisition_id.vendor_id:
                self.supplier_id = self.requisition_id.vendor_id
            
            # Filter purchase orders by requisition
            return {
                'domain': {
                    'purchase_order_id': [('requisition_id', '=', self.requisition_id.id)],
                    'bill_lading_id': [('requisition_id', '=', self.requisition_id.id)]
                }
            }


    
    @api.model
    def create(self, vals):
        """Override create to generate sequence number"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('logistics.container') or _('New')
        return super(LogisticsContainer, self).create(vals)
    
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
    
    # @api.constrains('requisition_id', 'purchase_order_id')
    # def _check_purchase_order_requisition_consistency(self):
    #     for container in self:
    #         if container.purchase_order_id.requisition_id != container.requisition_id:
    #             raise ValidationError(_(
    #                 'Container %s: Purchase Order must belong to the same requisition (%s).'
    #             ) % (container.name, container.requisition_id.name))
    
    @api.constrains('bill_lading_id', 'requisition_id')
    def _check_bill_lading_requisition_consistency(self):
        for container in self:
            if container.bill_lading_id and container.bill_lading_id.requisition_id != container.requisition_id:
                raise ValidationError(_(
                    'Container %s: Bill of Lading must belong to the same requisition (%s).'
                ) % (container.name, container.requisition_id.name))
    
    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        if self.requisition_id:
            # Filter purchase orders by requisition
            return {
                'domain': {
                    'purchase_order_id': [('requisition_id', '=', self.requisition_id.id)],
                    'bill_lading_id': [('requisition_id', '=', self.requisition_id.id)]
                }
            }
    
    @api.onchange('purchase_order_id')
    def _onchange_purchase_order_id(self):
        if self.purchase_order_id:
            # Auto-set requisition from purchase order
            self.requisition_id = self.purchase_order_id.requisition_id
            # Filter bill of lading by requisition
            return {
                'domain': {
                    'bill_lading_id': [('requisition_id', '=', self.requisition_id.id)]
                }
            }
    
    # State Management Methods
    def action_ship(self):
        self.state = 'shipped'
        self.departure_date = fields.Date.context_today(self)
    
    def action_in_transit(self):
        self.state = 'in_transit'
    
    def action_arrived(self):
        self.state = 'arrived'
        if not self.arrival_date:
            self.arrival_date = fields.Date.context_today(self)
    
    def action_customs(self):
        self.state = 'customs'
    
    def action_released(self):
        self.state = 'released'
    
    def action_start_unloading(self):
        self.state = 'unloading'
    
    def action_unloaded(self):
        self.state = 'unloaded'
    
    def action_empty(self):
        self.state = 'empty'
    
    def action_returned(self):
        self.state = 'returned'
    
    def action_reset_to_draft(self):
        self.state = 'draft'
    
    @api.constrains('arrival_date', 'departure_date')
    def _check_dates(self):
        for container in self:
            if container.arrival_date and container.departure_date:
                if container.arrival_date < container.departure_date:
                    raise ValidationError(_('Arrival date cannot be before departure date.'))
                
    @api.onchange('requisition_id')
    def _onchange_requisition_id_details(self):
        """Auto-populate fields when requisition is selected"""
        if self.requisition_id:
            # Set supplier from requisition vendor
            if self.requisition_id.vendor_id:
                self.supplier_id = self.requisition_id.vendor_id
            
            # Filter purchase orders by requisition
            return {
                'domain': {
                    'purchase_order_id': [('requisition_id', '=', self.requisition_id.id)],
                    'bill_lading_id': [('requisition_id', '=', self.requisition_id.id)]
                }
            }

    purchase_order_count = fields.Integer(
        'Purchase Order Count', 
        compute='_compute_related_counts', 
        store=True
    )
    
    @api.depends('purchase_order_id', 'requisition_id')
    def _compute_related_counts(self):
        for container in self:
            # Count purchase orders - either direct PO or all POs from requisition
            if container.purchase_order_id:
                container.purchase_order_count = 1
            elif container.requisition_id:
                container.purchase_order_count = len(container.requisition_id.purchase_ids)
            else:
                container.purchase_order_count = 0
    
    def action_view_purchase_requisition(self):
        """Smart button to view related purchase requisition"""
        self.ensure_one()
        if not self.requisition_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.requisition',
            'res_id': self.requisition_id.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
        }
    
    def action_view_purchase_orders(self):
        """Smart button to view related purchase orders"""
        self.ensure_one()
        
        # Collect purchase orders
        purchase_orders = self.env['purchase.order']
        
        if self.purchase_order_id:
            purchase_orders |= self.purchase_order_id
        
        if self.requisition_id:
            purchase_orders |= self.requisition_id.purchase_ids
        
        if not purchase_orders:
            return
        
        return {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree,form' if len(purchase_orders) > 1 else 'form',
            'res_id': purchase_orders.id if len(purchase_orders) == 1 else False,
            'domain': [('id', 'in', purchase_orders.ids)],
            'target': 'current',
            'context': self.env.context,
        }