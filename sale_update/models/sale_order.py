# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    conversion_log_ids = fields.One2many(
        'sale.order.conversion.log', 
        'sale_order_id', 
        string='Conversion History'
    )

    def action_convert_to_quotation(self):
        """
        Convert Sale Order to Quotation with binary logic following the flowchart:
        1. Check all related POs - any goods received?
        2. Check Sale Order - any deliveries made?
        3. Binary outcome: COMPLETE FAILURE or FULL SUCCESS
        """
        self.ensure_one()
        
        if self.state not in ['sale', 'done']:
            raise UserError("Only confirmed sales orders can be converted to quotations.")
        
        # Get all related purchase orders
        purchase_orders = self._get_related_purchase_orders()
        
        # Store original field values for tracking (capture before any checks)
        original_values = self._capture_comprehensive_field_values()
        
        # STEP 1: Check All Related POs - Any goods received?
        po_goods_received = self._check_po_goods_received(purchase_orders)
        
        # STEP 2: Check Sale Order - Any deliveries made?
        so_deliveries_made = self._check_so_deliveries_made()
        
        # BINARY LOGIC: Any goods received OR deliveries made = COMPLETE FAILURE
        if po_goods_received or so_deliveries_made:
            # COMPLETE FAILURE PATH
            self._handle_complete_failure(original_values, purchase_orders)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Cannot Convert',
                    'message': 'Cannot convert - order has received/delivered items',
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        # FULL SUCCESS PATH
        try:
            # Step 1: Cancel all related purchase orders
            self._cancel_purchase_orders(purchase_orders)
            
            # Step 2: Delete cancelled purchase orders
            self._delete_purchase_orders(purchase_orders)
            
            # Step 3: Cancel Sale Order and return to quotation
            self._convert_to_quotation_state()
            
            # Step 4: Comprehensive logging - track ALL field changes
            new_values = self._capture_comprehensive_field_values()
            self._create_comprehensive_conversion_log(original_values, new_values, purchase_orders, True)
            
            _logger.info(f"Successfully converted Sale Order {self.name} to quotation")
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': f'Successfully converted to quotation',
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            # Complete failure - rollback any changes
            self.env.cr.rollback()
            _logger.error(f"Failed to convert Sale Order {self.name} to quotation: {str(e)}")
            raise UserError(f"Conversion failed: {str(e)}")

    def _get_related_purchase_orders(self):
        """Get all purchase orders related to this sale order"""
        purchase_orders = self.env['purchase.order']
        
        # Get POs from sale order lines
        for line in self.order_line:
            if line.product_id:
                # Find POs that might be related to this sale order line
                related_pos = self.env['purchase.order.line'].search([
                    ('product_id', '=', line.product_id.id),
                    ('order_id.origin', '=', self.name),
                    ('order_id.state', 'in', ['draft', 'sent', 'to approve', 'purchase'])
                ]).mapped('order_id')
                purchase_orders |= related_pos
        
        return purchase_orders

    def _check_po_goods_received(self, purchase_orders):
        """Check all related POs - any goods received?"""
        for po in purchase_orders:
            for picking in po.picking_ids:
                if picking.state == 'done':
                    return True
        return False
    
    def _check_so_deliveries_made(self):
        """Check Sale Order - any deliveries made?"""
        for picking in self.picking_ids:
            if picking.state == 'done':
                return True
        return False
    
    def _handle_complete_failure(self, original_values, purchase_orders):
        """Handle complete failure - log attempt only, no changes made"""
        self._create_comprehensive_conversion_log(
            original_values, 
            original_values,  # No changes made
            purchase_orders, 
            False  # Failed conversion
        )
        _logger.warning(f"Conversion attempt failed for Sale Order {self.name} - goods received/delivered")

    def _cancel_purchase_orders(self, purchase_orders):
        """Cancel all related purchase orders"""
        for po in purchase_orders:
            if po.state in ['draft', 'sent', 'to approve']:
                po.button_cancel()
            elif po.state == 'purchase':
                po.button_cancel()
            else:
                raise UserError(f"Cannot cancel Purchase Order {po.name} in state {po.state}")

    def _delete_purchase_orders(self, purchase_orders):
        """Delete cancelled purchase orders"""
        for po in purchase_orders:
            if po.state != 'cancel':
                raise UserError(f"Cannot delete Purchase Order {po.name} - not in cancelled state")
            
            # Delete related records first
            po.order_line.unlink()
            po.unlink()

    def _convert_to_quotation_state(self):
        """Convert sale order back to quotation state"""
        # Cancel delivery orders if any
        for picking in self.picking_ids:
            if picking.state not in ['done', 'cancel']:
                picking.action_cancel()
        
        # Reset sale order to draft/quotation state
        self.write({
            'state': 'draft',
            'procurement_group_id': False,
        })
        
        # Reset sale order lines
        for line in self.order_line:
            line.write({
                'procurement_group_id': False,
            })

    def _capture_comprehensive_field_values(self):
        """Capture comprehensive field values for tracking ALL changes"""
        try:
            # Sales Order Level Changes
            so_values = {
                'so_status': self.state,
                'so_state': self.state,
                'invoice_status': getattr(self, 'invoice_status', 'N/A'),
                'delivery_status': getattr(self, 'delivery_status', 'N/A'),
                'payment_status': getattr(self, 'payment_state', 'N/A'),
                'date_order': self.date_order,
                'validity_date': self.validity_date,
                'commitment_date': getattr(self, 'commitment_date', None),
                'amount_untaxed': self.amount_untaxed,
                'amount_tax': self.amount_tax,
                'amount_total': self.amount_total,
                'procurement_group_id': self.procurement_group_id.id if self.procurement_group_id else False,
            }
            
            # Sales Order Line Level Changes
            line_values = []
            for line in self.order_line:
                try:
                    line_data = {
                        'line_id': line.id,
                        'product_id': line.product_id.id if line.product_id else False,
                        'product_uom_qty': line.product_uom_qty,
                        'qty_delivered': getattr(line, 'qty_delivered', 0),
                        'qty_invoiced': getattr(line, 'qty_invoiced', 0),
                        'price_unit': line.price_unit,
                        'price_subtotal': line.price_subtotal,
                        'price_total': getattr(line, 'price_total', line.price_subtotal),
                        'state': getattr(line, 'state', 'N/A'),
                        'delivery_status': getattr(line, 'delivery_status', 'N/A'),
                    }
                    line_values.append(line_data)
                except Exception as e:
                    _logger.warning(f"Error capturing line data for line {line.id}: {str(e)}")
                    continue
            
            # Related Sale Records
            try:
                # Try different field names for stock moves based on Odoo version
                stock_moves = []
                if self.picking_ids:
                    for picking in self.picking_ids:
                        if hasattr(picking, 'move_lines'):
                            stock_moves.extend(picking.move_lines.ids)
                        elif hasattr(picking, 'move_ids_without_package'):
                            stock_moves.extend(picking.move_ids_without_package.ids)
                        elif hasattr(picking, 'move_ids'):
                            stock_moves.extend(picking.move_ids.ids)
            except Exception as e:
                _logger.warning(f"Error getting stock moves: {str(e)}")
                stock_moves = []
            
            try:
                payment_ids = []
                for invoice in self.invoice_ids:
                    if hasattr(invoice, 'payment_ids'):
                        payment_ids.extend(invoice.payment_ids.ids)
                    elif hasattr(invoice, 'payment_move_line_ids'):
                        payment_ids.extend(invoice.payment_move_line_ids.ids)
            except Exception as e:
                _logger.warning(f"Error getting payment data: {str(e)}")
                payment_ids = []
            
            related_records = {
                'stock_moves_count': len(stock_moves),
                'picking_ids_count': len(self.picking_ids),
                'picking_states': [p.state for p in self.picking_ids] if self.picking_ids else [],
                'invoice_ids_count': len(self.invoice_ids),
                'invoice_states': [i.state for i in self.invoice_ids] if self.invoice_ids else [],
                'payment_ids_count': len(payment_ids),
            }
            
            return {
                'so_level': so_values,
                'line_level': line_values,
                'related_records': related_records,
                'capture_timestamp': fields.Datetime.now(),
            }
            
        except Exception as e:
            _logger.error(f"Error capturing comprehensive field values: {str(e)}")
            # Return minimal data structure to prevent complete failure
            return {
                'so_level': {
                    'so_status': self.state,
                    'so_state': self.state,
                    'amount_total': self.amount_total,
                },
                'line_level': [],
                'related_records': {
                    'picking_ids_count': 0,
                    'invoice_ids_count': 0,
                },
                'capture_timestamp': fields.Datetime.now(),
            }

    def _create_comprehensive_conversion_log(self, original_values, new_values, purchase_orders, success):
        """Create comprehensive log entry tracking ALL field changes"""
        # Sales Order Level Changes
        so_changes = []
        for field, old_value in original_values['so_level'].items():
            new_value = new_values['so_level'].get(field)
            if old_value != new_value:
                so_changes.append({
                    'field': field,
                    'old_value': str(old_value),
                    'new_value': str(new_value),
                })
        
        # Sales Order Line Level Changes
        line_changes = []
        for i, old_line in enumerate(original_values['line_level']):
            if i < len(new_values['line_level']):
                new_line = new_values['line_level'][i]
                for field, old_value in old_line.items():
                    new_value = new_line.get(field)
                    if old_value != new_value:
                        line_changes.append({
                            'line_id': old_line['line_id'],
                            'field': field,
                            'old_value': str(old_value),
                            'new_value': str(new_value),
                        })
        
        # Related Records Changes
        related_changes = []
        for field, old_value in original_values['related_records'].items():
            new_value = new_values['related_records'].get(field)
            if old_value != new_value:
                related_changes.append({
                    'field': field,
                    'old_value': str(old_value),
                    'new_value': str(new_value),
                })
        
        # Purchase Orders Info
        po_info = []
        for po in purchase_orders:
            po_info.append({
                'name': po.name,
                'partner': po.partner_id.name,
                'amount_total': po.amount_total,
                'state': po.state,
                'goods_received': any(p.state == 'done' for p in po.picking_ids),
            })
        
        # Create comprehensive log
        log_data = {
            'sale_order_id': self.id,
            'conversion_date': fields.Datetime.now(),
            'user_id': self.env.user.id,
            'success': success,
            'so_level_changes': str(so_changes),
            'line_level_changes': str(line_changes),
            'related_records_changes': str(related_changes),
            'purchase_orders_info': str(po_info),
            'notes': 'Attempt only - no changes made' if not success else 'Full conversion completed',
        }
        
        self.env['sale.order.conversion.log'].create(log_data)
        