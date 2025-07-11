
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


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
                                 domain=[('supplier_rank', '>', 0)], tracking=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    
    # Container Content
    container_line_ids = fields.One2many('logistics.container.line', 'container_id', 
                                        string='Container Lines')
    
    # Financial Information
    currency_id = fields.Many2one('res.currency', string='Currency', 
                                 default=lambda self: self.env.company.currency_id)
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
    
    # Future integration points (commented for now)
    # picking_ids = fields.One2many('stock.picking', 'logistics_container_id', string='Stock Operations')
    # invoice_ids = fields.Many2many('account.move', 'container_invoice_rel', 'container_id', 'invoice_id', string='Related Invoices')
    
    # Company
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                default=lambda self: self.env.company)
    
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
    
    @api.onchange('product_qty', 'volume_per_unit')
    def _onchange_compute_volume(self):
        if self.product_qty and self.volume_per_unit:
            # This could be used to update container volume calculations
            pass


