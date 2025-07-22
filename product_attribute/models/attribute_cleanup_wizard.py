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
        ('executed', 'Executed')
    ], default='draft')
    
    # Summary fields
    products_found = fields.Integer('Total Products Found', readonly=True)
    products_with_attributes = fields.Integer('Products With Attributes', readonly=True)
    attributes_to_remove = fields.Integer('Attributes to Remove', readonly=True)
    
    # Batch size for processing
    batch_size = fields.Integer('Batch Size', default=50, help="Number of products to process per batch")
    
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
                # Simple preview - just the essential info
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
                </div>
                """
                self.preview_results = html_content
                
                # Update summary fields
                self.write({
                    'state': 'preview',
                    'products_found': preview['total_count'],
                    'products_with_attributes': preview['with_attributes_count'],
                    'attributes_to_remove': preview['summary']['total_attributes']
                })
            
            return self._reload_wizard()
            
        except Exception as e:
            self.preview_results = f"<div class='alert alert-danger'>Error: {str(e)}</div>"
            return self._reload_wizard()

    def action_execute_cleanup(self):
        """Execute the actual cleanup"""
        self.ensure_one()
        
        if self.state != 'preview':
            self.execution_results = "<div class='alert alert-warning'>Please run preview first!</div>"
            return self._reload_wizard()
        
        if not self.category_id:
            self.execution_results = "<div class='alert alert-warning'>No category selected!</div>"
            return self._reload_wizard()
        
        try:
            # Find products to process
            target_products = self.env['product.template'].search([
                ('categ_id', '=', self.category_id.id),
                ('attribute_line_ids', '!=', False)
            ])
            
            if not target_products:
                self.execution_results = "<div class='alert alert-info'>No products with attributes found to process.</div>"
                return self._reload_wizard()
            
            # Execute cleanup with batching
            results = self._execute_cleanup_batched(target_products)
            
            # Simple results display
            success_color = 'green' if results['error_count'] == 0 else 'orange'
            html_content = f"""
            <div class='alert alert-success'>
                <h4>Cleanup Completed</h4>
                <table class='table table-sm'>
                    <tr><td><strong>Products Processed:</strong></td><td>{results['total_processed']}</td></tr>
                    <tr><td><strong>Successful:</strong></td><td style='color: {success_color};'>{results['success_count']}</td></tr>
                    <tr><td><strong>Errors:</strong></td><td style='color: red;'>{results['error_count']}</td></tr>
                    <tr><td><strong>Attributes Removed:</strong></td><td>{results['attributes_removed']}</td></tr>
                    <tr><td><strong>Variants Removed:</strong></td><td>{results['variants_removed']}</td></tr>
                </table>
            </div>
            """
            
            self.write({
                'execution_results': html_content,
                'state': 'executed'
            })
            
            return self._reload_wizard()
            
        except Exception as e:
            self.execution_results = f"<div class='alert alert-danger'>Execution Error: {str(e)}</div>"
            return self._reload_wizard()

    def _execute_cleanup_batched(self, target_products):
        """Execute cleanup with batching - simplified version"""
        batch_size = self.batch_size or 50
        total_products = len(target_products)
        
        # Initialize results tracking
        results = {
            'total_processed': total_products,
            'success_count': 0,
            'error_count': 0,
            'attributes_removed': 0,
            'variants_removed': 0
        }
        
        # Process in batches to prevent timeouts
        for i in range(0, total_products, batch_size):
            batch_products = target_products[i:i + batch_size]
            
            # Process current batch
            for product in batch_products:
                try:
                    # Count before removal
                    initial_attributes = len(product.attribute_line_ids)
                    initial_variants = len(product.product_variant_ids)
                    
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