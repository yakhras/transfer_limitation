# -*- coding: utf-8 -*-
from odoo import models, fields, api

class PartnerStatement(models.Model):
    _name = 'partner.statement'
    _description = 'Partner Statement Analysis'
    _rec_name = 'partner_id'
    
    # Basic Fields
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    
    # ==========================================
    # RECORDSET METHODS (DATA SOURCES)
    # ==========================================
    
    def get_active_sales_orders(self):
        """Get confirmed sales orders recordset for this partner"""
        return self.partner_id.sale_order_ids.filtered(
            lambda order: order.state in ['sale', 'done']
        )
    
    def get_posted_invoices(self):
        """Get posted invoices recordset for this partner"""
        return self.partner_id.invoice_ids.filtered(
            lambda invoice: invoice.state == 'posted' and invoice.move_type not in ['entry']
        )
    
    def get_non_cancelled_invoices(self):
        """Get invoices that are not cancelled (posted or draft)"""
        return self.partner_id.invoice_ids.filtered(
            lambda invoice: invoice.state != 'cancel' and invoice.move_type not in ['entry']
        )
    
    def get_unpaid_invoices(self):
        """Get posted invoices that are not paid"""
        return self.get_posted_invoices().filtered(
            lambda inv: inv.payment_state == 'not_paid'
        )
    
    def get_invoices_from_orders(self, orders):
        """Get all invoices related to given sale orders"""
        invoices = orders.mapped('invoice_ids').filtered(
            lambda invoice: invoice.state != 'cancel' and invoice.move_type not in ['entry']
        )
        invoices_data = []
        for invoice in invoices:
            invoices_data.append(self._format_invoice_data(invoice))
        return invoices_data
    
    def _format_invoice_data(self, invoice):
        """Format invoice data for output"""
        if invoice:
            return {
                'invoice_id': invoice.id,
                'invoice_name': invoice.name,
                'invoice_state': invoice.state,
                'amount_total': invoice.amount_total,
                'payment_state': invoice.payment_state,
                'invoice_date': invoice.invoice_date,
            }
        return {}
    
    # ==========================================
    # PRODUCT METHODS (BUSINESS LOGIC)
    # ==========================================
    
    def get_products(self, sale_orders):
        """Get uninvoiced products from given sale orders"""
        all_lines = sale_orders.mapped('order_line')
        return self._build_product_object(sale_orders, all_lines, 'sale_orders')
    
    
    def get_manual_invoice_products(self):
        """Get products from non-cancelled manual invoices"""
        non_cancelled_invoices = self.get_non_cancelled_invoices()
        manual_invoices = non_cancelled_invoices.filtered(lambda inv: not inv.sale_ids)
        
        all_lines = manual_invoices.mapped('invoice_line_ids')
        return self._build_product_object(manual_invoices, all_lines, 'invoices')
    
    # ==========================================
    # PAYMENT METHODS
    # ==========================================
    
    def get_invoice_payment_mapping(self):
        """Get all credit moves (payments) related to debit moves (invoices)"""
        posted_invoices = self.get_posted_invoices()
        paid_invoices = posted_invoices.filtered(
            lambda inv: inv.payment_state != 'not_paid'
        )
        
        invoice_debit_lines = paid_invoices.mapped('line_ids').filtered(
            lambda line: line.account_id.user_type_id.type == 'receivable'
        )
        
        partial_reconciles = self.env['account.partial.reconcile'].search([
            ('debit_move_id', 'in', invoice_debit_lines.ids)
        ])
        
        payment_credit_lines = partial_reconciles.mapped('credit_move_id')
        
        return {
            'invoices': paid_invoices,
            'invoice_lines': invoice_debit_lines,
            'payment_lines': payment_credit_lines,
            'reconcile_records': partial_reconciles,
            'mapping': sorted([{
                'invoice': rec.debit_move_id.move_id.name,
                'payment': rec.credit_move_id.move_id.name,
                'amount': rec.credit_amount_currency,
                'date': rec.max_date
            } for rec in partial_reconciles], key=lambda x: x['date'])
        }
    
    # ==========================================
    # HELPER METHODS
    # ==========================================
    
    def _build_product_object(self, records, lines, record_type):
        """Build product object for any record type (orders/invoices)"""
        records_data = {}
        
        for line in lines:
            if record_type == 'sale_orders':
                parent_id = line.order_id.id
                parent_record = line.order_id
                quantity_field = line.product_uom_qty
                tax_field = line.tax_id.amount
                date_field = line.order_id.date_order
            else:  # invoices
                parent_id = line.move_id.id
                parent_record = line.move_id
                quantity_field = line.quantity
                tax_field = line.tax_ids.amount
                date_field = line.move_id.date
                
            if parent_id not in records_data:
                records_data[parent_id] = {
                    'record_id': parent_id,
                    'record_name': parent_record.name,
                    'record_date': date_field,
                    'record_state': parent_record.state,
                    'record_total': parent_record.amount_total,
                    'products': []
                }
            
            records_data[parent_id]['products'].append({
                'product_id': line.product_id.id,
                'product_name': line.product_id.name,
                'quantity': quantity_field,
                'price_unit': line.price_unit,
                'tax_amount': tax_field,
                'subtotal': line.price_subtotal,
            })
        
        return {
            'partner_id': self.partner_id.id,
            'partner_name': self.partner_id.name,
            'total_records': len(records),
            record_type: sorted(records_data.values(), key=lambda x: x['record_date']),
            'has_products': bool(lines)
        }
    
    # ==========================================
    # MASTER COMBINED STATEMENT METHOD
    # ==========================================
    
    def get_complete_partner_statement(self):
        """
        Master method to get complete partner statement
        Combines all scenarios from Excel template
        """
        result = {
            'partner_id': self.partner_id.id,
            'partner_name': self.partner_id.name,
            'statement_sections': [],
            'summary': {
                'total_orders': 0,
                'total_invoices': 0,
                'total_payments': 0,
                'total_unpaid_invoices': 0,
                'has_uninvoiced_products': False,
                'has_invoiced_products': False,
                'has_manual_invoices': False,
                'has_payments': False,
                'has_unpaid_invoices': False
            }
        }
        
        # Step 1: Get active sales orders
        active_orders = self.get_active_sales_orders()
        
        if active_orders:
            result['summary']['total_orders'] = len(active_orders)
            
            # Process each order based on invoice_status
            for order in active_orders:
                section = self._process_single_order(order)
                if section:
                    result['statement_sections'].append(section)
                    
                    # Update summary flags
                    if section.get('section_type') == 'uninvoiced':
                        result['summary']['has_uninvoiced_products'] = True
                    elif section.get('section_type') in ['invoiced_paid', 'invoiced_unpaid', 'invoiced_mixed']:
                        result['summary']['has_invoiced_products'] = True
                        if section.get('has_payments'):
                            result['summary']['has_payments'] = True
        
        # Step 2: Handle manual invoices (not from sale orders)
        manual_section = self._process_manual_invoices()
        if manual_section:
            result['statement_sections'].append(manual_section)
            result['summary']['has_manual_invoices'] = True
            result['summary']['total_invoices'] += manual_section.get('total_records', 0)
            if manual_section.get('has_payments'):
                result['summary']['has_payments'] = True
            if manual_section.get('has_unpaid_invoices'):
                result['summary']['has_unpaid_invoices'] = True
        
        # Step 3: Calculate totals
        self._calculate_statement_totals(result)

        # Step 4: Calculate running balances for each section
        running_balance = 0
    
        for section in result['statement_sections']:
            section = self._calculate_section_balances(section)
        
        return result
    
    def _process_single_order(self, order):
        """Process a single sale order based on its invoice status"""
        section = {
            'order_id': order.id,
            'order_name': order.name,
            'order_state': order.state,
            'order_total': order.amount_total,
            'invoice_status': order.invoice_status,
            'products': [],
            'invoices': [],
            'payments': [],
            'unpaid_invoices': [],
            'section_type': '',
            'has_payments': False,
            'has_unpaid_invoices': False
        }
        
        if order.invoice_status == 'to invoice':
            # Get uninvoiced products only
            uninvoiced_data = self.get_products(order)
            section['products'] = uninvoiced_data.get('sale_orders', [])
            section['section_type'] = 'uninvoiced'
            
            # Check if there are existing invoices for this order
            if order.invoice_ids:
                invoices = self.get_invoices_from_orders(order)
                section['invoices'] = invoices
                posted_invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
                if posted_invoices:
                    # Get payment details
                    payment_data = self._get_order_payments(order)
                    section['payments'] = payment_data
                    section['has_payments'] = bool(payment_data)
                    
                    # Get unpaid invoices
                    unpaid_data = self._get_order_unpaid_invoices(order)
                    section['unpaid_invoices'] = unpaid_data
                    section['has_unpaid_invoices'] = bool(unpaid_data)
                    
                    section['section_type'] = 'partially_invoiced'
        
        elif order.invoice_status == 'invoiced':
            # Get all invoiced products
            invoiced_data = self.get_products(order)
            section['products'] = invoiced_data.get('sale_orders', [])

            invoices = self.get_invoices_from_orders(order)
            section['invoices'] = invoices
            
            # Get payment details
            payment_data = self._get_order_payments(order)
            section['payments'] = payment_data
            section['has_payments'] = bool(payment_data)
            
            # Get unpaid invoices
            unpaid_data = self._get_order_unpaid_invoices(order)
            section['unpaid_invoices'] = unpaid_data
            section['has_unpaid_invoices'] = bool(unpaid_data)
            
            if payment_data and unpaid_data:
                section['section_type'] = 'invoiced_mixed'  # Both paid and unpaid
            elif payment_data:
                section['section_type'] = 'invoiced_paid'   # Fully paid
            else:
                section['section_type'] = 'invoiced_unpaid' # Fully unpaid
        
        elif order.invoice_status == 'no':
            if order.invoice_ids:
                # Case: Had invoices, now zero balance (credit notes)
                invoiced_data = self.get_products(order)
                section['products'] = invoiced_data.get('sale_orders', [])

                invoices = self.get_invoices_from_orders(order)
                section['invoices'] = invoices
                
                payment_data = self._get_order_payments(order)
                section['payments'] = payment_data
                section['has_payments'] = bool(payment_data)
                
                unpaid_data = self._get_order_unpaid_invoices(order)
                section['unpaid_invoices'] = unpaid_data
                section['has_unpaid_invoices'] = bool(unpaid_data)
                
                section['section_type'] = 'credit_note_case'
            else:
                # Case: Never invoiced
                uninvoiced_data = self.get_products(order)
                section['products'] = uninvoiced_data.get('sale_orders', [])
                section['section_type'] = 'never_invoiced'
        
        return section #if section['products'] or section['payments'] or section['unpaid_invoices'] else None
    
    def _process_manual_invoices(self):
        """Process manual invoices (not from sale orders)"""
        manual_data = self.get_manual_invoice_products()
        
        if not manual_data.get('has_products'):
            return None
        
        # Get payment details for manual invoices
        manual_invoices = self.get_non_cancelled_invoices().filtered(lambda inv: not inv.sale_ids)
        payment_data = []
        unpaid_data = []
        
        if manual_invoices:
            posted_manual = manual_invoices.filtered(lambda inv: inv.state == 'posted')
            if posted_manual:
                # Get payments for manual invoices
                payment_mapping = self.get_invoice_payment_mapping()
                manual_payments = [
                    mapping for mapping in payment_mapping.get('mapping', [])
                    if any(inv.name == mapping['invoice'] for inv in posted_manual)
                ]
                payment_data = manual_payments
                
                # Get unpaid manual invoices
                unpaid_manual_invoices = posted_manual.filtered(
                    lambda inv: inv.payment_state == 'not_paid'
                )
                unpaid_data = [{
                    'invoice_id': inv.id,
                    'invoice_name': inv.name,
                    'invoice_state': inv.state,
                    'amount_total': inv.amount_total,
                    'payment_state': inv.payment_state
                } for inv in unpaid_manual_invoices]
        
        return {
            'section_type': 'manual_invoices',
            'section_name': 'Manual Invoices',
            'products': manual_data.get('invoices', []),
            'payments': payment_data,
            'unpaid_invoices': unpaid_data,
            'total_records': manual_data.get('total_records', 0),
            'has_payments': bool(payment_data),
            'has_unpaid_invoices': bool(unpaid_data)
        }
    
    def _get_order_payments(self, order):
        """Get payment details for a specific order"""
        if not order.invoice_ids:
            return []
        
        posted_invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
        if not posted_invoices:
            return []
        
        # Get all payment mappings
        payment_mapping = self.get_invoice_payment_mapping()
        
        # Filter payments for this order's invoices
        order_payments = [
            mapping for mapping in payment_mapping.get('mapping', [])
            if any(inv.name == mapping['invoice'] for inv in posted_invoices)
        ]
        
        return order_payments
    
    def _get_order_unpaid_invoices(self, order):
        """Get unpaid invoice details for a specific order"""
        if not order.invoice_ids:
            return []
        
        posted_invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
        if not posted_invoices:
            return []
        
        # Get unpaid invoices only
        unpaid_invoices = posted_invoices.filtered(
            lambda inv: inv.payment_state == 'not_paid'
        )
        
        # Format unpaid invoice details
        unpaid_data = [{
            'invoice_id': inv.id,
            'invoice_name': inv.name,
            'invoice_state': inv.state,
            'amount_total': inv.amount_total,
            'payment_state': inv.payment_state,
            'due_date': inv.invoice_date_due
        } for inv in unpaid_invoices]
        
        return unpaid_data
    
    def _calculate_statement_totals(self, result):
        """Calculate summary totals for the statement"""
        total_invoices = 0
        total_payments = 0
        total_unpaid_invoices = 0
        
        for section in result['statement_sections']:
            if section.get('section_type') in ['invoiced_paid', 'invoiced_unpaid', 'invoiced_mixed', 'credit_note_case']:
                total_invoices += len(section.get('products', []))
            elif section.get('section_type') == 'manual_invoices':
                total_invoices += section.get('total_records', 0)
            
            total_payments += len(section.get('payments', []))
            total_unpaid_invoices += len(section.get('unpaid_invoices', []))
            
            # Update unpaid invoices flag
            if section.get('has_unpaid_invoices'):
                result['summary']['has_unpaid_invoices'] = True
        
        result['summary']['total_invoices'] = total_invoices
        result['summary']['total_payments'] = total_payments
        result['summary']['total_unpaid_invoices'] = total_unpaid_invoices

    def _calculate_section_balances(self, section):
        """Calculate balance within this section only"""
        current_balance = 0
        
        if section.get('invoices'):
            for record in section['invoices']:
                current_balance += record.get('amount_total', 0)
                record['balance_after_invoice'] = round(current_balance, 2)  # Add rounding
                
                if section.get('payments'):
                    for payment in section['payments']:
                        if payment.get('invoice', '') == record.get('record_name', ''):
                            current_balance -= payment.get('amount', 0)
                            # Fix negative zero issue
                            if abs(current_balance) < 0.01:  # If very close to zero
                                current_balance = 0.00
                            payment['balance_after_payment'] = round(current_balance, 2)
        
        return section
    

    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    @api.model
    def create_for_partner(self, partner_id):
        """Create partner statement instance for given partner"""
        return self.create({'partner_id': partner_id})
    
    def refresh_data(self):
        """Refresh and return updated statement data"""
        return self.get_complete_partner_statement()
    
    # ==========================================
    # COMPUTED FIELDS (Optional - for UI display)
    # ==========================================
    
    has_active_orders = fields.Boolean(
        string='Has Active Orders', 
        compute='_compute_statement_flags'
    )
    has_unpaid_invoices = fields.Boolean(
        string='Has Unpaid Invoices', 
        compute='_compute_statement_flags'
    )
    total_orders_count = fields.Integer(
        string='Total Orders', 
        compute='_compute_statement_counts'
    )
    total_invoices_count = fields.Integer(
        string='Total Invoices', 
        compute='_compute_statement_counts'
    )
    
    @api.depends('partner_id')
    def _compute_statement_flags(self):
        """Compute boolean flags for quick status check"""
        for record in self:
            record.has_active_orders = bool(record.get_active_sales_orders())
            record.has_unpaid_invoices = bool(record.get_unpaid_invoices())
    
    @api.depends('partner_id')
    def _compute_statement_counts(self):
        """Compute counts for display"""
        for record in self:
            record.total_orders_count = len(record.get_active_sales_orders())
            record.total_invoices_count = len(record.get_posted_invoices())

