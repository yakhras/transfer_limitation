# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# Extend Purchase Requisition

# Add these methods to the PurchaseRequisition class in your Python file

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'
    
    # Direct relations
    container_ids = fields.One2many('logistics.container', 'requisition_id', string='Containers')
    bill_lading_ids = fields.One2many('logistics.bill.lading', 'requisition_id', string='Bills of Lading')
    
    # Computed fields
    container_count = fields.Integer('Container Count', compute='_compute_counts', store=True)
    bill_lading_count = fields.Integer('B/L Count', compute='_compute_counts', store=True)
    
    
    
    
    
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
    
    container_distribution_ids = fields.One2many(
        'purchase.requisition.container.distribution', 
        'requisition_id', 
        string='Container Distribution'
    )
    has_container_distribution = fields.Boolean(
        'Has Container Distribution', 
        compute='_compute_has_container_distribution'
    )
    
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
                'name': f"{self.name}-CONT-{container_sequence:03d}",
                'requisition_id': self.id,
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
        
        # Show notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'{len(created_containers)} containers created successfully.',
                'type': 'success',
                'sticky': False,
            }
        }
    
# Extend Purchase Order
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    # Direct relations
    container_ids = fields.One2many('logistics.container', 'purchase_order_id', string='Containers')
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


class LogisticsBillLading(models.Model):
    _name = 'logistics.bill.lading'
    _description = 'Bill of Lading'
    _order = 'bl_date desc, name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char('B/L Number', required=True, copy=False, tracking=True)
    bl_type = fields.Selection([
        ('master', 'Master B/L'),
        ('house', 'House B/L'),
        ('express', 'Express B/L'),
        ('seaway', 'Seaway B/L'),
    ], string='B/L Type', default='master', required=True, tracking=True)
    bl_date = fields.Date('B/L Date', required=True, default=fields.Date.context_today, tracking=True)
    
    # Master Relation - One B/L belongs to one Requisition
    requisition_id = fields.Many2one('purchase.requisition', string='Purchase Requisition', 
                                    required=True, tracking=True, ondelete='cascade')
    
    # Related Purchase Orders (from the requisition)
    purchase_order_ids = fields.One2many('purchase.order', 'bill_lading_id', string='Purchase Orders')
    
    # Direct container relation
    container_ids = fields.One2many('logistics.container', 'bill_lading_id', string='Containers')
    
    # Parties Information
    shipper_id = fields.Many2one('res.partner', string='Shipper', required=True,
                                domain=[('is_company', '=', True)], tracking=True)
    consignee_id = fields.Many2one('res.partner', string='Consignee', required=True,
                                  domain=[('is_company', '=', True)], tracking=True)
    notify_party_id = fields.Many2one('res.partner', string='Notify Party',
                                     domain=[('is_company', '=', True)], tracking=True)
    
    # Shipping Information
    vessel_name = fields.Char('Vessel Name', tracking=True)
    voyage_number = fields.Char('Voyage Number', tracking=True)
    port_of_loading_id = fields.Many2one('logistics.port', string='Port of Loading', tracking=True)
    port_of_discharge_id = fields.Many2one('logistics.port', string='Port of Discharge', tracking=True)
    place_of_receipt = fields.Char('Place of Receipt')
    place_of_delivery = fields.Char('Place of Delivery')
    
    # Dates
    etd = fields.Date('ETD (Estimated Time of Departure)', tracking=True)
    eta = fields.Date('ETA (Estimated Time of Arrival)', tracking=True)
    actual_departure_date = fields.Date('Actual Departure Date', tracking=True)
    actual_arrival_date = fields.Date('Actual Arrival Date', tracking=True)
    
    # Terms and Conditions
    freight_terms = fields.Selection([
        ('prepaid', 'Freight Prepaid'),
        ('collect', 'Freight Collect'),
    ], string='Freight Terms', default='prepaid', tracking=True)
    payment_terms = fields.Text('Payment Terms')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('in_transit', 'In Transit'),
        ('arrived', 'Arrived'),
        ('delivered', 'Delivered'),
        ('closed', 'Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True)
    
    # Computed counts
    container_count = fields.Integer('Container Count', compute='_compute_counts', store=True)
    purchase_order_count = fields.Integer('Purchase Order Count', compute='_compute_counts', store=True)
    
    # Additional Information
    marks_and_numbers = fields.Text('Marks and Numbers')
    description_of_goods = fields.Text('Description of Goods')
    gross_weight = fields.Float('Gross Weight (KG)', digits=(12, 2))
    net_weight = fields.Float('Net Weight (KG)', digits=(12, 2))
    measurement = fields.Float('Measurement (CBM)', digits=(10, 3))
    
    # Financial
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id)
    freight_amount = fields.Monetary('Freight Amount', currency_field='currency_id')
    total_charges = fields.Monetary('Total Charges', currency_field='currency_id')
    
    # Document References
    booking_reference = fields.Char('Booking Reference')
    export_reference = fields.Char('Export Reference')
    forwarding_agent_reference = fields.Char('Forwarding Agent Reference')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.company)
    
    @api.depends('container_ids', 'purchase_order_ids')
    def _compute_counts(self):
        for bl in self:
            bl.container_count = len(bl.container_ids)
            bl.purchase_order_count = len(bl.purchase_order_ids)
    
    @api.onchange('container_ids')
    def _onchange_container_ids(self):
        if self.container_ids:
            # Auto-populate vessel and voyage from first container
            first_container = self.container_ids[0]
            if first_container.vessel_name and not self.vessel_name:
                self.vessel_name = first_container.vessel_name
            if first_container.voyage_number and not self.voyage_number:
                self.voyage_number = first_container.voyage_number
            
            # Calculate totals from containers
            self.gross_weight = sum(self.container_ids.mapped('weight_kg'))
            self.measurement = sum(self.container_ids.mapped('volume_m3'))
    
    @api.constrains('container_ids')
    def _check_container_requisition_consistency(self):
        for bl in self:
            if bl.container_ids:
                for container in bl.container_ids:
                    if container.requisition_id != bl.requisition_id:
                        raise ValidationError(_(
                            'Container %s must belong to the same requisition (%s) as the Bill of Lading.'
                        ) % (container.name, bl.requisition_id.name))
    
    @api.constrains('purchase_order_ids')
    def _check_purchase_order_requisition_consistency(self):
        for bl in self:
            if bl.purchase_order_ids:
                for po in bl.purchase_order_ids:
                    if po.requisition_id != bl.requisition_id:
                        raise ValidationError(_(
                            'Purchase Order %s must belong to the same requisition (%s) as the Bill of Lading.'
                        ) % (po.name, bl.requisition_id.name))
    
    # State Management Methods
    def action_confirm(self):
        self.state = 'confirmed'
    
    def action_ship(self):
        self.state = 'shipped'
        if not self.actual_departure_date:
            self.actual_departure_date = fields.Date.context_today(self)
        # Update related containers
        self.container_ids.filtered(lambda c: c.state in ['draft', 'shipped']).action_in_transit()
    
    def action_in_transit(self):
        self.state = 'in_transit'
    
    def action_arrived(self):
        self.state = 'arrived'
        if not self.actual_arrival_date:
            self.actual_arrival_date = fields.Date.context_today(self)
        # Update related containers
        self.container_ids.filtered(lambda c: c.state == 'in_transit').action_arrived()
    
    def action_delivered(self):
        self.state = 'delivered'
    
    def action_close(self):
        self.state = 'closed'
    
    def action_cancel(self):
        self.state = 'cancelled'
    
    def action_reset_to_draft(self):
        self.state = 'draft'
    
    @api.constrains('eta', 'etd')
    def _check_dates(self):
        for bl in self:
            if bl.eta and bl.etd:
                if bl.eta < bl.etd:
                    raise ValidationError(_('ETA cannot be before ETD.'))
                
    @api.onchange('requisition_id')
    def _onchange_requisition_id_details(self):
        """Auto-populate fields when requisition is selected"""
        if self.requisition_id:
            # Set default shipper from requisition vendor
            if self.requisition_id.vendor_id and not self.shipper_id:
                self.shipper_id = self.requisition_id.vendor_id
            
            # Set default consignee as company
            if not self.consignee_id:
                self.consignee_id = self.env.company.partner_id
            
            # Auto-populate description from requisition lines
            if self.requisition_id.line_ids and not self.description_of_goods:
                products = self.requisition_id.line_ids.mapped('product_id.name')
                self.description_of_goods = ', '.join(products[:5])  # First 5 products
                if len(products) > 5:
                    self.description_of_goods += f' and {len(products) - 5} more items'

    @api.onchange('purchase_order_ids')
    def _onchange_purchase_order_ids(self):
        """Auto-populate vessel info and cargo details from purchase orders"""
        if self.purchase_order_ids:
            # Get unique suppliers from purchase orders
            suppliers = self.purchase_order_ids.mapped('partner_id')
            if len(suppliers) == 1 and not self.shipper_id:
                self.shipper_id = suppliers[0]
            
            # Calculate total values
            total_amount = sum(self.purchase_order_ids.mapped('amount_total'))
            if total_amount and not self.total_charges:
                self.total_charges = total_amount

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
        
        # Get purchase orders from requisition or direct relationship
        purchase_orders = self.purchase_order_ids
        
        if self.requisition_id and not purchase_orders:
            purchase_orders = self.requisition_id.purchase_ids
        
        if not purchase_orders:
            return
        
        action = self.env.ref('purchase.purchase_order_action_generic').read()[0]
        
        if len(purchase_orders) > 1:
            action['domain'] = [('id', 'in', purchase_orders.ids)]
        else:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = purchase_orders.id
        
        return action


class LogisticsPort(models.Model):
    _name = 'logistics.port'
    _description = 'Port'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char('Port Name', required=True)
    code = fields.Char('Port Code', size=5)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    city = fields.Char('City')
    timezone = fields.Selection([
        ('UTC', 'UTC'),
        ('UTC+1', 'UTC+1'), ('UTC+2', 'UTC+2'), ('UTC+3', 'UTC+3'), ('UTC+4', 'UTC+4'),
        ('UTC+5', 'UTC+5'), ('UTC+6', 'UTC+6'), ('UTC+7', 'UTC+7'), ('UTC+8', 'UTC+8'),
        ('UTC+9', 'UTC+9'), ('UTC+10', 'UTC+10'), ('UTC+11', 'UTC+11'), ('UTC+12', 'UTC+12'),
        ('UTC-1', 'UTC-1'), ('UTC-2', 'UTC-2'), ('UTC-3', 'UTC-3'), ('UTC-4', 'UTC-4'),
        ('UTC-5', 'UTC-5'), ('UTC-6', 'UTC-6'), ('UTC-7', 'UTC-7'), ('UTC-8', 'UTC-8'),
        ('UTC-9', 'UTC-9'), ('UTC-10', 'UTC-10'), ('UTC-11', 'UTC-11'), ('UTC-12', 'UTC-12'),
    ], string='Timezone', default='UTC')
    is_active = fields.Boolean('Active', default=True)
    notes = fields.Text('Notes')

    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for port in self:
            name = port.name
            if port.code:
                name = f"[{port.code}] {name}"
            result.append((port.id, name))
        return result


class LogisticsContainer(models.Model):
    _name = 'logistics.container'
    _description = 'Shipping Container'
    _order = 'arrival_date desc, name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char('Container Number', required=True, copy=False, tracking=True)
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
    
    @api.constrains('requisition_id', 'purchase_order_id')
    def _check_purchase_order_requisition_consistency(self):
        for container in self:
            if container.purchase_order_id.requisition_id != container.requisition_id:
                raise ValidationError(_(
                    'Container %s: Purchase Order must belong to the same requisition (%s).'
                ) % (container.name, container.requisition_id.name))
    
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
        
        action = self.env.ref('purchase.purchase_order_action_generic').read()[0]
        
        if len(purchase_orders) > 1:
            action['domain'] = [('id', 'in', purchase_orders.ids)]
        else:
            action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
            action['res_id'] = purchase_orders.id
        
        return action


class LogisticsContainerLine(models.Model):
    _name = 'logistics.container.line'
    _description = 'Container Product Line'
    _order = 'sequence, id'

    # Relations
    container_id = fields.Many2one('logistics.container', string='Container', 
                                  required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    
    # Product Information
    product_qty = fields.Float('Quantity', required=True, digits='Product Unit of Measure')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    price_unit = fields.Float('Unit Price', digits='Product Price')
    price_subtotal = fields.Monetary('Subtotal', compute='_compute_price_subtotal', 
                                    store=True, currency_field='currency_id')
    
    # Additional Product Details
    lot_number = fields.Char('Lot/Batch Number')
    serial_number = fields.Char('Serial Number')
    expiry_date = fields.Date('Expiry Date')
    manufacturing_date = fields.Date('Manufacturing Date')
    country_of_origin = fields.Many2one('res.country', string='Country of Origin')
    
    # Product Physical Properties
    gross_weight = fields.Float('Gross Weight (KG)', digits=(10, 2))
    net_weight = fields.Float('Net Weight (KG)', digits=(10, 2))
    volume_per_unit = fields.Float('Volume per Unit (M³)', digits=(8, 4))
    
    # Organization
    sequence = fields.Integer('Sequence', default=10)
    notes = fields.Text('Notes')
    
    # Related Fields
    currency_id = fields.Many2one('res.currency', related='container_id.currency_id')
    container_state = fields.Selection(related='container_id.state', string='Container Status')
    
    @api.depends('product_qty', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.product_qty * line.price_unit
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            self.price_unit = self.product_id.standard_price
            if self.product_id.country_of_origin:
                self.country_of_origin = self.product_id.country_of_origin


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
# Future integrations with other Odoo modules (commented for now)

# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#     
#     logistics_container_id = fields.Many2one('logistics.container', string='Container')
#     container_operation_type = fields.Selection([
#         ('receiving', 'Container Receiving'),
#         ('unloading', 'Container Unloading'),
#         ('delivery', 'Container Delivery'),
#     ], string='Container Operation')
#     
#     @api.onchange('logistics_container_id')
#     def _onchange_container_id(self):
#         if self.logistics_container_id:
#             self.origin = self.logistics_container_id.name
#             if self.logistics_container_id.purchase_order_id:
#                 self.purchase_id = self.logistics_container_id.purchase_order_id


# class AccountMove(models.Model):
#     _inherit = 'account.move'
#     
#     container_ids = fields.Many2many('logistics.container', 'container_invoice_rel',
#                                     'invoice_id', 'container_id', 
#                                     string='Related Containers')
#     container_reference = fields.Char('Container Reference', 
#                                      compute='_compute_container_reference', store=True)
#     
#     @api.depends('container_ids')
#     def _compute_container_reference(self):
#         for move in self:
#             if move.container_ids:
#                 move.container_reference = ', '.join(move.container_ids.mapped('name'))
#             else:
#                 move.container_reference = ''