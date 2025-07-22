from odoo import models, fields, api

class AttributeCleanupWizard(models.TransientModel):
    _name = 'attribute.cleanup.wizard'
    _description = 'Product Attribute Cleanup Wizard'

    category_id = fields.Many2one(
        'product.category',
        string='Product Category', 
        required=True,
        help="Select the category to clean attributes from"
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
    products_with_attributes = fields.Integer('Products With Attributes', readonly=True)
    attributes_to_remove = fields.Integer('Attributes to Remove', readonly=True)
    
    # Batch processing fields
    batch_size = fields.Integer('Batch Size', default=35, help="Number of products to process per batch")
    current_batch = fields.Integer('Current Batch', readonly=True, default=0)
    total_batches = fields.Integer('Total Batches', readonly=True, default=0)
    products_processed = fields.Integer('Products Processed', readonly=True, default=0)
    
    # Accumulated results across all batches
    total_success = fields.Integer('Total Successful', readonly=True, default=0)
    total_errors = fields.Integer('Total Errors', readonly=True, default=0)
    total_attributes_removed = fields.Integer('Total Attributes Removed', readonly=True, default=0)
    total_variants_removed = fields.Integer('Total Variants Removed', readonly=True, default=0)
    
    # Store product IDs to process (as text field to persist across requests)
    products_to_process_ids = fields.Text('Products To Process IDs', readonly=True)
    products_processed_ids = fields.Text('Products Processed IDs', readonly=True)
    
    def action_preview_category(self):
        """Preview what will be affected"""
        self.ensure_one()
        
        if not self.category_id:
            self.preview_results = "<div class='alert alert-warning'>Please select a category first!</div>"
            return self._reload_wizard()
        
        try:
            # Get preview data
            preview = self.env['product.template'].get_category_preview(self.category_id.id)
            
            if 'error' in preview:
                self.preview_results = f"<div class='alert alert-danger'>Error: {preview['error']}</div>"
            else:
                # Calculate batch information
                products_to_process = preview['with_attributes_count']
                batch_size = self.batch_size or 35
                total_batches = (products_to_process + batch_size - 1) // batch_size if products_to_process > 0 else 0
                
                # Enhanced preview with batch information
                html_content = f"""
                <div class='alert alert-info'>
                    <h4>Preview Results for: {preview['category_name']}</h4>
                    <table class='table table-sm'>
                        <tr><td><strong>Total Products:</strong></td><td>{preview['total_count']}</td></tr>
                        <tr><td><strong>Products WITH Attributes:</strong></td><td style='color: #d68910;'>{preview['with_attributes_count']}</td></tr>
                        <tr><td><strong>Products WITHOUT Attributes:</strong></td><td style='color: #28b463;'>{preview['without_attributes_count']}</td></tr>
                        <tr><td><strong>Attributes to Remove:</strong></td><td>{preview['summary']['total_attributes']}</td></tr>
                        <tr><td><strong>Variants to Remove:</strong></td><td>{preview['summary']['total_variants']}</td></tr>
                    </table>
                    <hr>
                    <h5>📦 Processing Plan</h5>
                    <table class='table table-sm'>
                        <tr><td><strong>Will be processed in:</strong></td><td><span style='color: #2874f0; font-weight: bold;'>{total_batches} batches</span></td></tr>
                        <tr><td><strong>Batch size:</strong></td><td>{batch_size} products per batch</td></tr>
                        <tr><td><strong>Estimated time:</strong></td><td>~{total_batches * 2}-{total_batches * 5} minutes total</td></tr>
                    </table>
                    <p style='color: #28a745;'><strong>✅ Each batch is processed in a separate step to prevent timeouts!</strong></p>
                </div>
                """
                self.preview_results = html_content
                
                # Update summary fields
                self.write({
                    'state': 'preview',
                    'products_found': preview['total_count'],
                    'products_with_attributes': preview['with_attributes_count'],
                    'attributes_to_remove': preview['summary']['total_attributes'],
                    'total_batches': total_batches,
                    'current_batch': 0,
                    'products_processed': 0,
                    'total_success': 0,
                    'total_errors': 0,
                    'total_attributes_removed': 0,
                    'total_variants_removed': 0,
                    'products_to_process_ids': '',
                    'products_processed_ids': ''
                })
            
            return self._reload_wizard()
            
        except Exception as e:
            self.preview_results = f"<div class='alert alert-danger'>Error: {str(e)}</div>"
            return self._reload_wizard()

    def action_start_batch_processing(self):
        """Initialize batch processing"""
        self.ensure_one()
        
        if self.state != 'preview':
            return self._reload_wizard()
        
        try:
            # Find products to process and store their IDs
            target_products = self.env['product.template'].search([
                ('categ_id', '=', self.category_id.id),
                ('attribute_line_ids', '!=', False)
            ])
            
            if not target_products:
                self.execution_results = "<div class='alert alert-info'>No products with attributes found to process.</div>"
                self.write({'state': 'executed'})
                return self._reload_wizard()
            
            # Store product IDs for processing across multiple requests
            product_ids_str = ','.join(str(id) for id in target_products.ids)
            
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
        """Process the next batch of products"""
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
            batch_size = self.batch_size or 35
            current_batch_ids = remaining_product_ids[:batch_size]
            batch_products = self.env['product.template'].browse(current_batch_ids)
            
            # Process this batch
            batch_results = self._process_single_batch(batch_products)
            
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
            new_total_attributes_removed = self.total_attributes_removed + batch_results['attributes_removed']
            new_total_variants_removed = self.total_variants_removed + batch_results['variants_removed']
            
            self.write({
                'current_batch': new_current_batch,
                'products_processed': new_products_processed,
                'products_processed_ids': processed_ids_str,
                'total_success': new_total_success,
                'total_errors': new_total_errors,
                'total_attributes_removed': new_total_attributes_removed,
                'total_variants_removed': new_total_variants_removed,
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

    def _process_single_batch(self, batch_products):
        """Process a single batch of products - same logic as before"""
        results = {
            'success_count': 0,
            'error_count': 0,
            'attributes_removed': 0,
            'variants_removed': 0
        }
        
        for product in batch_products:
            try:
                # Count before removal
                initial_attributes = len(product.attribute_line_ids)
                
                # Remove attributes
                if product.attribute_line_ids:
                    product.attribute_line_ids.unlink()
                    results['attributes_removed'] += initial_attributes
                
                if hasattr(product, 'product_template_attribute_value_ids'):
                    product.product_template_attribute_value_ids.unlink()
                
                # Remove extra variants
                if len(product.product_variant_ids) > 1:
                    variants_to_delete = product.product_variant_ids.filtered(
                        lambda v: v.id != product.product_variant_id.id
                    )
                    variants_removed = len(variants_to_delete)
                    variants_to_delete.unlink()
                    results['variants_removed'] += variants_removed
                
                # Clear main variant attributes
                if product.product_variant_id:
                    product.product_variant_id.write({
                        'attribute_value_ids': [(5, 0, 0)]
                    })
                
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
                    <tr><td><strong>Attributes Removed:</strong></td><td>{self.total_attributes_removed}</td></tr>
                    <tr><td><strong>Variants Removed:</strong></td><td>{self.total_variants_removed}</td></tr>
                </table>
            </div>
            """
        else:
            # Still processing
            progress_percent = (self.products_processed / self.products_with_attributes) * 100 if self.products_with_attributes > 0 else 0
            
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
                    <tr><td><strong>Products Processed:</strong></td><td>{self.products_processed} of {self.products_with_attributes}</td></tr>
                    <tr><td><strong>Products Remaining:</strong></td><td>{remaining_count}</td></tr>
                    <tr><td><strong>Successful So Far:</strong></td><td style='color: green;'>{self.total_success}</td></tr>
                    <tr><td><strong>Errors So Far:</strong></td><td style='color: red;'>{self.total_errors}</td></tr>
                    <tr><td><strong>Attributes Removed:</strong></td><td>{self.total_attributes_removed}</td></tr>
                </table>
                <p><strong>Next:</strong> Click "Process Next Batch" to continue with the next {min(remaining_count, self.batch_size)} products.</p>
            </div>
            """

    def _finalize_processing(self):
        """Mark processing as completed"""
        success_color = 'green' if self.total_errors == 0 else 'orange'
        
        final_html = f"""
        <div class='alert alert-success'>
            <h4>✅ Cleanup Completed Successfully!</h4>
            <table class='table table-sm'>
                <tr><td><strong>Total Batches:</strong></td><td>{self.current_batch}</td></tr>
                <tr><td><strong>Products Processed:</strong></td><td>{self.products_processed}</td></tr>
                <tr><td><strong>Successful:</strong></td><td style='color: {success_color};'>{self.total_success}</td></tr>
                <tr><td><strong>Errors:</strong></td><td style='color: red;'>{self.total_errors}</td></tr>
                <tr><td><strong>Attributes Removed:</strong></td><td>{self.total_attributes_removed}</td></tr>
                <tr><td><strong>Variants Removed:</strong></td><td>{self.total_variants_removed}</td></tr>
            </table>
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
            'res_model': 'attribute.cleanup.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context
        }