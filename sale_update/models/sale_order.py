# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import UserError
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
            
            # Show error notification only - don't reload for failures
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
            
            # Force refresh by returning a window action to the same record
            return {
                'name': 'Sale Order',
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': self.id,
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'current',
                'context': {
                    **self.env.context,
                    'show_sale': True,
                    'default_type': 'sale',
                },
                'flags': {
                    'initial_mode': 'edit',
                    'form': {'action_buttons': True, 'options': {'mode': 'edit'}},
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
        
        # Filter out any records that might have been deleted
        existing_pos = self.env['purchase.order']
        for po in purchase_orders:
            try:
                # Test if record still exists by accessing a basic field
                po_exists = po.exists()
                if po_exists:
                    existing_pos |= po_exists
            except Exception as e:
                _logger.warning(f"Purchase Order {po.id} no longer exists: {str(e)}")
                continue
        
        return existing_pos

    def _check_po_goods_received(self, purchase_orders):
        """Check all related POs - any goods received?"""
        for po in purchase_orders:
            try:
                # Verify PO still exists before checking pickings
                if not po.exists():
                    _logger.warning(f"Purchase Order {po.id} no longer exists, skipping")
                    continue
                    
                for picking in po.picking_ids:
                    try:
                        if picking.exists() and picking.state == 'done':
                            return True
                    except Exception as e:
                        _logger.warning(f"Error checking picking {picking.id}: {str(e)}")
                        continue
            except Exception as e:
                _logger.warning(f"Error checking PO {po.id}: {str(e)}")
                continue
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
            try:
                # Verify PO still exists before trying to cancel
                if not po.exists():
                    _logger.warning(f"Purchase Order {po.id} no longer exists, skipping cancellation")
                    continue
                
                # Refresh the record to get latest state
                po = po.with_context(active_test=False).browse(po.id)
                if not po.exists():
                    _logger.warning(f"Purchase Order {po.id} was deleted during process")
                    continue
                
                current_state = po.state
                if current_state in ['draft', 'sent', 'to approve']:
                    po.button_cancel()
                elif current_state == 'purchase':
                    po.button_cancel()
                elif current_state == 'cancel':
                    _logger.info(f"Purchase Order {po.name} already cancelled")
                else:
                    _logger.warning(f"Cannot cancel Purchase Order {po.name} in state {current_state}")
                    
            except Exception as e:
                _logger.error(f"Error cancelling Purchase Order {po.id}: {str(e)}")
                # Continue with other POs instead of failing completely
                continue

    def _delete_purchase_orders(self, purchase_orders):
        """Delete cancelled purchase orders"""
        for po in purchase_orders:
            try:
                # Verify PO still exists before trying to delete
                if not po.exists():
                    _logger.warning(f"Purchase Order {po.id} no longer exists, skipping deletion")
                    continue
                
                # Refresh the record to get latest state
                po = po.with_context(active_test=False).browse(po.id)
                if not po.exists():
                    _logger.warning(f"Purchase Order {po.id} was already deleted")
                    continue
                
                if po.state != 'cancel':
                    _logger.warning(f"Cannot delete Purchase Order {po.name} - not in cancelled state (current: {po.state})")
                    continue
                
                # Delete related records first (if they exist)
                try:
                    if po.order_line.exists():
                        po.order_line.unlink()
                except Exception as e:
                    _logger.warning(f"Error deleting PO lines for {po.name}: {str(e)}")
                
                # Delete the PO
                po_name = po.name  # Store name before deletion for logging
                po.unlink()
                _logger.info(f"Successfully deleted Purchase Order {po_name}")
                
            except Exception as e:
                _logger.error(f"Error deleting Purchase Order {po.id}: {str(e)}")
                # Continue with other POs instead of failing completely
                continue

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
        
        # Reset sale order lines - only update fields that exist on sale.order.line
        for line in self.order_line:
            # Only update fields that actually exist on sale.order.line
            update_vals = {}
            # Most sale order line fields are automatically handled when the SO state changes
            # We don't need to manually update procurement_group_id on lines
            if update_vals:  # Only write if there are actual fields to update
                line.write(update_vals)
        
        # Send cancellation email using the same logic as your automated actions
        self._send_conversion_canceled_email()

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
            try:
                if po.exists():
                    po_data = {
                        'name': po.name,
                        'partner': po.partner_id.name if po.partner_id else 'Unknown',
                        'amount_total': po.amount_total,
                        'state': po.state,
                        'goods_received': any(p.state == 'done' for p in po.picking_ids if p.exists()),
                    }
                else:
                    po_data = {
                        'name': f'PO-{po.id}',
                        'partner': 'Record Deleted',
                        'amount_total': 0,
                        'state': 'deleted',
                        'goods_received': False,
                    }
                po_info.append(po_data)
            except Exception as e:
                _logger.warning(f"Error getting info for PO {po.id}: {str(e)}")
                po_info.append({
                    'name': f'PO-{po.id}',
                    'partner': 'Error accessing record',
                    'amount_total': 0,
                    'state': 'error',
                    'goods_received': False,
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

    def _send_conversion_canceled_email(self):
        """Send canceled email using the same logic as your automated actions"""
        try:
            # Find the email template by searching for it
            email_template = self.env['mail.template'].search([
                ('name', '=', 'Afkar Canceled Order')
            ], limit=1)
            
            if not email_template:
                # Try searching with different variations
                email_template = self.env['mail.template'].search([
                    ('name', 'ilike', 'Afkar'),
                    ('name', 'ilike', 'Cancel'),
                    ('model', '=', 'sale.order')
                ], limit=1)
            
            if not email_template:
                _logger.warning("Canceled email template not found. Available templates:")
                # Log available templates for debugging
                all_templates = self.env['mail.template'].search([('model', '=', 'sale.order')])
                for template in all_templates:
                    _logger.warning(f"Available template: '{template.name}'")
                return
            
            _logger.info(f"Found email template: '{email_template.name}'")
            
            # Check if this order matches the conditions from your automated actions
            should_send_email = self._check_canceled_email_conditions()
            _logger.info(f"Should send email for order {self.name}: {should_send_email}")
            
            if should_send_email:
                # Send the email using the same template
                try:
                    email_template.send_mail(self.id, force_send=True)
                    _logger.info(f"Sent canceled email for converted order {self.name} using template '{email_template.name}'")
                except Exception as send_error:
                    _logger.error(f"Failed to send email: {str(send_error)}")
            else:
                _logger.info(f"Order {self.name} doesn't match email conditions, skipping email")
                
        except Exception as e:
            _logger.error(f"Error in canceled email process for order {self.name}: {str(e)}")

    def _check_canceled_email_conditions(self):
        """Check if this order matches the conditions from your automated actions"""
        try:
            _logger.info(f"Checking email conditions for order {self.name}")
            
            # Condition 1: Afkar Orders Canceled - Email
            # Order Lines > Warehouse = "Afkar Transit Deposu" 
            afkar_warehouse = self.env['stock.warehouse'].search([
                ('name', '=', 'Afkar Transit Deposu')
            ], limit=1)
            
            _logger.info(f"Afkar warehouse found: {afkar_warehouse.name if afkar_warehouse else 'Not found'}")
            
            if afkar_warehouse:
                for line in self.order_line:
                    _logger.info(f"Checking line: {line.product_id.name if line.product_id else 'No product'}")
                    
                    # Check if any line is from Afkar Transit Deposu warehouse
                    if hasattr(line, 'warehouse_id') and line.warehouse_id == afkar_warehouse:
                        _logger.info(f"Found matching warehouse on line: {line.warehouse_id.name}")
                        return True
                    
                    # Alternative: check picking warehouse
                    for picking in self.picking_ids:
                        if picking.location_id and picking.location_id.warehouse_id == afkar_warehouse:
                            _logger.info(f"Found matching warehouse in picking: {picking.location_id.warehouse_id.name}")
                            return True
                        
                        # Also check destination warehouse
                        if picking.location_dest_id and picking.location_dest_id.warehouse_id == afkar_warehouse:
                            _logger.info(f"Found matching destination warehouse in picking: {picking.location_dest_id.warehouse_id.name}")
                            return True
            
            # Condition 2: Afkar Export Orders Canceled - Email
            # Order Lines > Warehouse = "İhracat Deposu" AND Product Category contains "Enjeksiyon"
            ihracat_warehouse = self.env['stock.warehouse'].search([
                ('name', '=', 'İhracat Deposu')
            ], limit=1)
            
            _logger.info(f"İhracat warehouse found: {ihracat_warehouse.name if ihracat_warehouse else 'Not found'}")
            
            if ihracat_warehouse:
                for line in self.order_line:
                    if line.product_id and line.product_id.categ_id:
                        # Check warehouse condition
                        warehouse_match = False
                        if hasattr(line, 'warehouse_id') and line.warehouse_id == ihracat_warehouse:
                            warehouse_match = True
                            _logger.info(f"Found İhracat warehouse on line: {line.warehouse_id.name}")
                        else:
                            # Check picking warehouse
                            for picking in self.picking_ids:
                                if (picking.location_id and picking.location_id.warehouse_id == ihracat_warehouse) or \
                                   (picking.location_dest_id and picking.location_dest_id.warehouse_id == ihracat_warehouse):
                                    warehouse_match = True
                                    _logger.info(f"Found İhracat warehouse in picking")
                                    break
                        
                        # Check product category condition
                        if warehouse_match:
                            category = line.product_id.categ_id
                            _logger.info(f"Checking product category: {category.name}")
                            # Check current category and parent categories for "Enjeksiyon"
                            while category:
                                _logger.info(f"Checking category: {category.name}")
                                if 'Enjeksiyon' in category.name:
                                    _logger.info(f"Found Enjeksiyon category: {category.name}")
                                    return True
                                category = category.parent_id
            
            _logger.info("No matching conditions found")
            return False
            
        except Exception as e:
            _logger.error(f"Error checking email conditions: {str(e)}")
            return False