from odoo import models, fields, api

class AttributeAssignmentWizard(models.TransientModel):
    _name = 'attribute.assignment.wizard'
    _description = 'Product Attribute Assignment Wizard'

    category_id = fields.Many2one(
        'product.category',
        string='Product Category', 
        required=True,
        help="Select the category to assign attributes to"
    )
    
    attribute_ids = fields.Many2many(
        'product.attribute',
        string='Attributes to Assign',
        help="Select attributes to assign to all products in the category"
    )
    
    preview_results = fields.Html(
        string='Preview Results',
        readonly=True
    )
    
    execution_results = fields.Html(
        string='Execution Results', 
        readonly=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('preview', 'Preview Done'),
        ('batch_processing', 'Batch Processing'),
        ('executed', 'Executed')
    ], default='draft')
    
    # Summary fields
    products_found = fields.Integer('Total Products Found', readonly=True)
    products_to_process = fields.Integer('Products to Process', readonly=True)
    attributes_selected = fields.Integer('Attributes Selected', readonly=True)
    total_operations = fields.Integer('Total Operations', readonly=True)
    
    # Batch processing fields
    batch_size = fields.Integer('Batch Size', default=10, help="Number of products to process per batch (recommended: 5-15)")
    current_batch = fields.Integer('Current Batch', readonly=True, default=0)
    total_batches = fields.Integer('Total Batches', readonly=True, default=0)
    products_processed = fields.Integer('Products Processed', readonly=True, default=0)
    
    # Accumulated results across all batches
    total_success = fields.Integer('Total Successful', readonly=True, default=0)
    total_errors = fields.Integer('Total Errors', readonly=True, default=0)
    total_attribute_lines_created = fields.Integer('Total Attribute Lines Created', readonly=True, default=0)
    total_values_assigned = fields.Integer('Total Values Assigned', readonly=True, default=0)
    
    # Store product IDs to process (as text field to persist across requests)
    products_to_process_ids = fields.Text('Products To Process IDs', readonly=True)
    products_processed_ids = fields.Text('Products Processed IDs', readonly=True)
    
    def action_preview_assignment(self):
        """Preview what attributes will be assigned"""
        self.ensure_one()
        
        if not self.category_id:
            self.preview_results = "<div class='alert alert-warning'>Please select a category first!</div>"
            return self._reload_wizard()
            
        if not self.attribute_ids:
            self.preview_results = "<div class='alert alert-warning'>Please select at least one attribute to assign!</div>"
            return self._reload_wizard()
        
        try:
            # Get preview data
            preview = self.env['product.template'].get_assignment_preview(self.category_id.id, self.attribute_ids.ids)
            
            if 'error' in preview:
                self.preview_results = f"<div class='alert alert-danger'>Error: {preview['error']}</div>"
            else:
                # Calculate batch information
                products_to_process = preview['products_without_selected_attributes']
                batch_size = self.batch_size or 10
                total_batches = (products_to_process + batch_size - 1) // batch_size if products_to_process > 0 else 0
                total_operations = products_to_process * len(self.attribute_ids)
                
                # Enhanced preview with assignment information
                html_content = f"""
                <div class='alert alert-info'>
                    <h4>Assignment Preview for: {preview['category_name']}</h4>
                    <table class='table table-sm'>
                        <tr><td><strong>Total Products in Category:</strong></td><td>{preview['total_products']}</td></tr>
                        <tr><td><strong>Products to Process:</strong></td><td style='color: #d68910;'>{preview['products_without_selected_attributes']}</td></tr>
                        <tr><td><strong>Products Already Have Attributes:</strong></td><td style='color: #28b463;'>{preview['products_with_selected_attributes']}</td></tr>
                        <tr><td><strong>Selected Attributes:</strong></td><td>{len(self.attribute_ids)}</td></tr>
                        <tr><td><strong>Total Attribute Lines to Create:</strong></td><td>{total_operations}</td></tr>
                        <tr><td><strong>Total Values to Assign:</strong></td><td>{preview['total_values_to_assign']}</td></tr>
                    </table>
                    <hr>
                    <h5>📋 Selected Attributes & Values</h5>
                    <table class='table table-sm'>
                """
                
                for attr_info in preview['attribute_details']:
                    values_list = ', '.join(attr_info['values'][:5])  # Show first 5 values
                    if len(attr_info['values']) > 5:
                        values_list += f" (and {len(attr_info['values']) - 5} more)"
                    
                    html_content += f"""
                    <tr>
                        <td><strong>{attr_info['name']}:</strong></td>
                        <td>{values_list} <span style='color: #666;'>({attr_info['value_count']} values)</span></td>
                    </tr>
                    """
                
                html_content += f"""
                    </table>
                    <hr>
                    <h5>📦 Processing Plan</h5>
                    <table class='table table-sm'>
                        <tr><td><strong>Will be processed in:</strong></td><td><span style='color: #2874f0; font-weight: bold;'>{total_batches} batches</span></td></tr>
                        <tr><td><strong>Batch size:</strong></td><td>{batch_size} products per batch</td></tr>
                        <tr><td><strong>Estimated time:</strong></td><td>~{total_batches * 2}-{total_batches * 5} minutes total</td></tr>
                    </table>
                    <p style='color: #28a745;'><strong>✅ Each batch is processed separately to prevent timeouts!</strong></p>
                    <p style='color: #17a2b8;'><strong>🔄 Odoo will automatically generate product variants from attribute combinations!</strong></p>
                </div>
                """
                
                self.preview_results = html_content
                
                # Update summary fields
                self.write({
                    'state': 'preview',
                    'products_found': preview['total_products'],
                    'products_to_process': preview['products_without_selected_attributes'],
                    'attributes_selected': len(self.attribute_ids),
                    'total_operations': total_operations,
                    'total_batches': total_batches,
                    'current_batch': 0,
                    'products_processed': 0,
                    'total_success': 0,
                    'total_errors': 0,
                    'total_attribute_lines_created': 0,
                    'total_values_assigned': 0,
                    'products_to_process_ids': '',
                    'products_processed_ids': ''
                })
            
            return self._reload_wizard()
            
        except Exception as e:
            self.preview_results = f"<div class='alert alert-danger'>Error: {str(e)}</div>"
            return self._reload_wizard()

    def action_start_batch_processing(self):
        """Initialize batch processing for attribute assignment"""
        self.ensure_one()
        
        if self.state != 'preview':
            return self._reload_wizard()
        
        try:
            # Find products to process (those that don't have ALL selected attributes)
            target_products = self.env['product.template'].search([
                ('categ_id', '=', self.category_id.id),
            ])
            
            # Filter to products that need attribute assignment
            products_to_process = []
            for product in target_products:
                existing_attribute_ids = product.attribute_line_ids.mapped('attribute_id.id')
                selected_attribute_ids = self.attribute_ids.ids
                
                # If product doesn't have ALL selected attributes, it needs processing
                if not all(attr_id in existing_attribute_ids for attr_id in selected_attribute_ids):
                    products_to_process.append(product.id)
            
            if not products_to_process:
                self.execution_results = "<div class='alert alert-info'>All products already have the selected attributes.</div>"
                self.write({'state': 'executed'})
                return self._reload_wizard()
            
            # Store product IDs for processing across multiple requests
            product_ids_str = ','.join(str(id) for id in products_to_process)
            
            self.write({
                'state': 'batch_processing',
                'products_to_process_ids': product_ids_str,
                'products_processed_ids': '',
                'current_batch': 0,
                'execution_results': self._get_batch_status_html()
            })
            
            return self._reload_wizard()
            
        except Exception as e:
            self.execution_results = f"<div class='alert alert-danger'>Error starting batch processing: {str(e)}</div>"
            return self._reload_wizard()

    def action_process_next_batch(self):
        """Process the next batch of products for attribute assignment"""
        self.ensure_one()
        
        if self.state != 'batch_processing':
            return self._reload_wizard()
        
        try:
            # Get products still to process
            remaining_product_ids = self._get_remaining_product_ids()
            
            if not remaining_product_ids:
                # No more products to process - we're done!
                self._finalize_processing()
                return self._reload_wizard()
            
            # Get next batch
            batch_size = self.batch_size or 10
            current_batch_ids = remaining_product_ids[:batch_size]
            batch_products = self.env['product.template'].browse(current_batch_ids)
            
            # Process this batch
            batch_results = self._assign_attributes_to_batch(batch_products)
            
            # Update processed IDs
            processed_ids_str = self.products_processed_ids or ''
            if processed_ids_str:
                processed_ids_str += ','
            processed_ids_str += ','.join(str(id) for id in current_batch_ids)
            
            # Update totals
            new_current_batch = self.current_batch + 1
            new_products_processed = self.products_processed + len(current_batch_ids)
            new_total_success = self.total_success + batch_results['success_count']
            new_total_errors = self.total_errors + batch_results['error_count']
            new_total_attribute_lines_created = self.total_attribute_lines_created + batch_results['attribute_lines_created']
            new_total_values_assigned = self.total_values_assigned + batch_results['values_assigned']
            
            self.write({
                'current_batch': new_current_batch,
                'products_processed': new_products_processed,
                'products_processed_ids': processed_ids_str,
                'total_success': new_total_success,
                'total_errors': new_total_errors,
                'total_attribute_lines_created': new_total_attribute_lines_created,
                'total_values_assigned': new_total_values_assigned,
                'execution_results': self._get_batch_status_html()
            })
            
            # Check if we're done
            if len(remaining_product_ids) <= batch_size:
                self._finalize_processing()
            
            return self._reload_wizard()
            
        except Exception as e:
            self.execution_results = f"<div class='alert alert-danger'>Batch processing error: {str(e)}</div>"
            return self._reload_wizard()

    def _get_remaining_product_ids(self):
        """Get list of product IDs still to be processed"""
        if not self.products_to_process_ids:
            return []
        
        all_product_ids = [int(id_str) for id_str in self.products_to_process_ids.split(',') if id_str.strip()]
        
        if not self.products_processed_ids:
            return all_product_ids
        
        processed_ids = [int(id_str) for id_str in self.products_processed_ids.split(',') if id_str.strip()]
        return [id for id in all_product_ids if id not in processed_ids]

    def _assign_attributes_to_batch(self, batch_products):
        """Assign selected attributes to a batch of products"""
        results = {
            'success_count': 0,
            'error_count': 0,
            'attribute_lines_created': 0,
            'values_assigned': 0
        }
        
        selected_attributes = self.attribute_ids
        
        for product in batch_products:
            try:
                product_lines_created = 0
                product_values_assigned = 0
                
                for attribute in selected_attributes:
                    # Check if product already has this attribute
                    existing_line = product.attribute_line_ids.filtered(lambda l: l.attribute_id.id == attribute.id)
                    
                    if not existing_line:
                        # Create new attribute line
                        attribute_line = self.env['product.template.attribute.line'].create({
                            'product_tmpl_id': product.id,
                            'attribute_id': attribute.id,
                            'value_ids': [(6, 0, attribute.value_ids.ids)]  # Assign ALL values
                        })
                        product_lines_created += 1
                        product_values_assigned += len(attribute.value_ids)
                    else:
                        # Update existing line to include all values
                        all_value_ids = set(existing_line.value_ids.ids + attribute.value_ids.ids)
                        existing_line.write({
                            'value_ids': [(6, 0, list(all_value_ids))]
                        })
                        # Count only newly added values
                        new_values = len(all_value_ids) - len(existing_line.value_ids.ids)
                        product_values_assigned += max(0, new_values)
                
                results['attribute_lines_created'] += product_lines_created
                results['values_assigned'] += product_values_assigned
                results['success_count'] += 1
                
            except Exception as e:
                results['error_count'] += 1
                continue
        
        return results

    def _get_batch_status_html(self):
        """Generate HTML showing current batch processing status"""
        remaining_count = len(self._get_remaining_product_ids())
        
        if remaining_count == 0:
            # All done
            return f"""
            <div class='alert alert-success'>
                <h4>🎉 All Batches Completed!</h4>
                <table class='table table-sm'>
                    <tr><td><strong>Total Batches Processed:</strong></td><td>{self.current_batch}</td></tr>
                    <tr><td><strong>Products Processed:</strong></td><td>{self.products_processed}</td></tr>
                    <tr><td><strong>Successful:</strong></td><td style='color: green;'>{self.total_success}</td></tr>
                    <tr><td><strong>Errors:</strong></td><td style='color: red;'>{self.total_errors}</td></tr>
                    <tr><td><strong>Attribute Lines Created:</strong></td><td>{self.total_attribute_lines_created}</td></tr>
                    <tr><td><strong>Values Assigned:</strong></td><td>{self.total_values_assigned}</td></tr>
                </table>
                <p style='color: #17a2b8;'><strong>🔄 Odoo will now automatically generate product variants!</strong></p>
            </div>
            """
        else:
            # Still processing
            progress_percent = (self.products_processed / self.products_to_process) * 100 if self.products_to_process > 0 else 0
            
            return f"""
            <div class='alert alert-info'>
                <h4>🔄 Batch Processing in Progress</h4>
                <div style='background-color: #f0f0f0; border-radius: 10px; overflow: hidden; margin: 10px 0;'>
                    <div style='background-color: #28a745; height: 25px; width: {progress_percent:.1f}%; 
                                display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;'>
                        {progress_percent:.1f}%
                    </div>
                </div>
                <table class='table table-sm'>
                    <tr><td><strong>Current Batch:</strong></td><td>{self.current_batch + 1} of {self.total_batches}</td></tr>
                    <tr><td><strong>Products Processed:</strong></td><td>{self.products_processed} of {self.products_to_process}</td></tr>
                    <tr><td><strong>Products Remaining:</strong></td><td>{remaining_count}</td></tr>
                    <tr><td><strong>Successful So Far:</strong></td><td style='color: green;'>{self.total_success}</td></tr>
                    <tr><td><strong>Errors So Far:</strong></td><td style='color: red;'>{self.total_errors}</td></tr>
                    <tr><td><strong>Attribute Lines Created:</strong></td><td>{self.total_attribute_lines_created}</td></tr>
                    <tr><td><strong>Values Assigned:</strong></td><td>{self.total_values_assigned}</td></tr>
                </table>
                <p><strong>Next:</strong> Click "Process Next Batch" to continue with the next {min(remaining_count, self.batch_size)} products.</p>
            </div>
            """

    def _finalize_processing(self):
        """Mark processing as completed"""
        success_color = 'green' if self.total_errors == 0 else 'orange'
        
        final_html = f"""
        <div class='alert alert-success'>
            <h4>✅ Attribute Assignment Completed Successfully!</h4>
            <table class='table table-sm'>
                <tr><td><strong>Total Batches:</strong></td><td>{self.current_batch}</td></tr>
                <tr><td><strong>Products Processed:</strong></td><td>{self.products_processed}</td></tr>
                <tr><td><strong>Successful:</strong></td><td style='color: {success_color};'>{self.total_success}</td></tr>
                <tr><td><strong>Errors:</strong></td><td style='color: red;'>{self.total_errors}</td></tr>
                <tr><td><strong>Attribute Lines Created:</strong></td><td>{self.total_attribute_lines_created}</td></tr>
                <tr><td><strong>Values Assigned:</strong></td><td>{self.total_values_assigned}</td></tr>
            </table>
            <hr>
            <p style='color: #17a2b8;'><strong>🔄 Odoo has automatically generated product variants from the assigned attributes!</strong></p>
            <p style='color: #28a745;'><strong>✅ You can now check your products to see the new variants.</strong></p>
        </div>
        """
        
        self.write({
            'state': 'executed',
            'execution_results': final_html
        })

    def _reload_wizard(self):
        """Reload the wizard window"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'attribute.assignment.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context
        }