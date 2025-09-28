from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LogisticsBillLading(models.Model):
    _name = 'logistics.bill.lading'
    _description = 'Bill of Lading'
    _order = 'bl_date desc, name'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information - Modified to auto-generate reference
    name = fields.Char('B/L Number', required=True, copy=False, tracking=True,
                      readonly=True, default=lambda self: _('New'))
    bl_type = fields.Selection([
        ('master', 'Master B/L'),
        ('house', 'House B/L'),
        ('express', 'Express B/L'),
        ('seaway', 'Seaway B/L'),
    ], string='B/L Type', default='master', required=True, tracking=True)
    bl_date = fields.Date('B/L Date', required=True, default=fields.Date.context_today, tracking=True)
    
    # Master Relation - One B/L belongs to one Requisition
    requisition_id = fields.Many2many('purchase.requisition', string='Purchase Requisition', 
                                    required=True, tracking=True, ondelete='cascade')
    
    # Related Purchase Orders (from the requisition)
    purchase_order_ids = fields.One2many('purchase.order', 'bill_lading_id', string='Purchase Orders')
    
    # Direct container relation
    container_ids = fields.Many2many(
        'logistics.container', 
        string='Containers',
        domain="[('requisition_id', 'in', requisition_id)]"  # Only containers from selected requisitions
    )
    
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
    port_of_loading_id = fields.Many2one('res.country.state', string='Port of Loading', tracking=True)
    port_of_loading_country_id = fields.Many2one('res.country', string='Loading Country', 
                                                 related='port_of_loading_id.country_id', readonly=True)
    port_of_discharge_id = fields.Many2one('res.country.state', string='Port of Discharge', tracking=True)
    port_of_discharge_country_id = fields.Many2one('res.country', string='Discharge Country', 
                                                   related='port_of_discharge_id.country_id', readonly=True)
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

    @api.model
    def create(self, vals):
        """Override create to generate sequence number and update containers"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('logistics.bill.lading') or _('New')
        
        record = super(LogisticsBillLading, self).create(vals)
        
        # Update containers' port of discharge after creation
        if record.container_ids and record.port_of_discharge_id:
            record._update_containers_port_of_discharge()
        
        return record
    
    def action_view_containers(self):
        """Smart button to view related containers"""
        if not self.container_ids:
            return
        
        action = self.env.ref('container.action_container_container').read()[0]
        
        if len(self.container_ids) > 1:
            action['domain'] = [('bill_lading_id', 'in', self.id)]
        else:
            action['views'] = [(self.env.ref('container.view_logistics_container_form').id, 'form')]
            action['res_id'] = self.container_ids.id
        
        return action
    

    def write(self, vals):
        """Override write to update containers when needed"""
        result = super(LogisticsBillLading, self).write(vals)
        
        # If containers or port of discharge changed, update containers
        if 'container_ids' in vals or 'port_of_discharge_id' in vals:
            for record in self:
                if record.container_ids and record.port_of_discharge_id:
                    record._update_containers_port_of_discharge()
        
        return result
    

    def _update_containers_port_of_discharge(self):
        """Helper method to update port of discharge in containers"""
        for container in self.container_ids:
            if hasattr(container, 'port_of_discharge'):
                container.sudo().write({
                    'port_of_discharge': self.port_of_discharge_id.id
                })
    

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
            
            # Update port of discharge in all selected containers
            if self.port_of_discharge_id:
                for container in self.container_ids:
                    if hasattr(container, 'port_of_discharge'):
                        container.port_of_discharge = self.port_of_discharge_id
    

    @api.onchange('port_of_discharge_id')
    def _onchange_port_of_discharge_bl(self):
        """Update containers' port of discharge when B/L port changes"""
        if self.port_of_discharge_id and self.container_ids:
            for container in self.container_ids:
                if hasattr(container, 'port_of_discharge'):
                    container.port_of_discharge = self.port_of_discharge_id
        
        # Call the original onchange method for place of delivery
        self._onchange_port_of_discharge()
    

    @api.constrains('container_ids', 'requisition_id')
    def _check_container_requisition_consistency(self):
        for bl in self:
            if bl.container_ids and bl.requisition_id:
                invalid_containers = bl.container_ids.filtered(
                    lambda c: c.requisition_id not in bl.requisition_id
                )
                if invalid_containers:
                    raise ValidationError(_(
                        'These containers must belong to selected requisitions: %s'
                    ) % ', '.join(invalid_containers.mapped('name')))
    

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


    @api.onchange('port_of_loading_id')
    def _onchange_port_of_loading(self):
        """Update place of receipt when port of loading changes"""
        if self.port_of_loading_id:
            if not self.place_of_receipt:
                self.place_of_receipt = f"{self.port_of_loading_id.name}, {self.port_of_loading_id.country_id.name}"
    

    @api.onchange('port_of_discharge_id')
    def _onchange_port_of_discharge(self):
        """Update place of delivery when port of discharge changes"""
        if self.port_of_discharge_id:
            if not self.place_of_delivery:
                self.place_of_delivery = f"{self.port_of_discharge_id.name}, {self.port_of_discharge_id.country_id.name}"


    @api.constrains('port_of_loading_id', 'port_of_discharge_id')
    def _check_ports_different(self):
        """Ensure loading and discharge ports are different"""
        for bl in self:
            if bl.port_of_loading_id and bl.port_of_discharge_id:
                if bl.port_of_loading_id == bl.port_of_discharge_id:
                    raise ValidationError(_('Port of Loading and Port of Discharge must be different.'))


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
    
    