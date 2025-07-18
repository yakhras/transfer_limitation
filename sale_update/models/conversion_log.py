# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrderConversionLog(models.Model):
    _name = 'sale.order.conversion.log'
    _description = 'Sale Order Conversion Log'
    _order = 'conversion_date desc'

    sale_order_id = fields.Many2one(
        'sale.order', 
        string='Sale Order', 
        required=True, 
        ondelete='cascade'
    )
    conversion_date = fields.Datetime(
        string='Conversion Date', 
        required=True, 
        default=fields.Datetime.now
    )
    user_id = fields.Many2one(
        'res.users', 
        string='Sales Rep', 
        required=True, 
        default=lambda self: self.env.user
    )
    success = fields.Boolean(
        string='Success', 
        default=True
    )
    
    # Comprehensive field tracking as per flowchart
    so_level_changes = fields.Text(
        string='Sales Order Level Changes',
        help='SO Status, State, Invoice Status, Delivery Status, Payment Status, Date fields, Amount fields'
    )
    line_level_changes = fields.Text(
        string='Sales Order Line Level Changes',
        help='Line Status, State, Quantity, price, tax fields, Delivery status per line'
    )
    related_records_changes = fields.Text(
        string='Related Sale Records Changes',
        help='Stock moves/reservations, Accounting entries, Delivery orders, Invoice records'
    )
    purchase_orders_info = fields.Text(
        string='Purchase Orders Info',
        help='Information about related purchase orders and their status'
    )
    notes = fields.Text(
        string='Notes'
    )

    def name_get(self):
        result = []
        for record in self:
            status = "SUCCESS" if record.success else "FAILED"
            name = f"{record.sale_order_id.name} - {status} - {record.conversion_date}"
            result.append((record.id, name))
        return result