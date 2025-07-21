from odoo import models, fields, api
from datetime import datetime
import json
import base64

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
    
    products_found = fields.Integer('Total Products Found', readonly=True)
    products_with_attributes = fields.Integer('Products With Attributes', readonly=True)
    products_without_attributes = fields.Integer('Products Without Attributes', readonly=True)
    attributes_to_remove = fields.Integer('Attributes to Remove', readonly=True)
    variants_to_remove = fields.Integer('Variants to Remove', readonly=True)
    
    # Batching fields
    batch_size = fields.Integer('Batch Size', default=10, help="Number of products to process per batch")
    current_batch = fields.Integer('Current Batch', readonly=True, default=0)
    total_batches = fields.Integer('Total Batches', readonly=True, default=0)
    processing_progress = fields.Html('Processing Progress', readonly=True)
    
    def action_preview_category(self):
        """Preview what will be affected"""
        self.ensure_one()
        
        if not self.category_id:
            self.preview_results = "<div class='alert alert-warning'>Please select a category first!</div>"
            return self._reload_wizard()
        
        try:
            # Get preview data
            preview = self.env['product.template'].get_category_preview(self.category_id.id)
            
            # Create HTML report
            html_content = self._generate_preview_html(preview)
            
            # Update wizard fields
            self.write({
                'preview_results': html_content,
                'state': 'preview',
                'products_found': preview.get('total_count', 0),
                'products_with_attributes': preview.get('with_attributes_count', 0),
                'products_without_attributes': preview.get('without_attributes_count', 0),
                'attributes_to_remove': preview.get('summary', {}).get('total_attributes', 0),
                'variants_to_remove': preview.get('summary', {}).get('total_variants', 0)
            })
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'attribute.cleanup.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
                'context': self.env.context
            }
            
        except Exception as e:
            self.preview_results = f"<div class='alert alert-danger'>Error: {str(e)}</div>"
            return self._reload_wizard()

    def action_execute_cleanup(self):
        """Execute the actual cleanup with batching"""
        self.ensure_one()
        
        if self.state != 'preview':
            self.preview_results = "<div class='alert alert-warning'>Please run preview first!</div>"
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
            
            # Initialize batch processing
            total_products = len(target_products)
            batch_size = self.batch_size or 10
            total_batches = (total_products + batch_size - 1) // batch_size  # Ceiling division
            
            self.write({
                'total_batches': total_batches,
                'current_batch': 0,
                'processing_progress': self._initialize_progress_html(total_products, total_batches),
                'state': 'executed'
            })
            
            # Execute cleanup with batching and track results
            results = self._execute_cleanup_with_batching(target_products)
            
            # Generate final execution HTML report
            html_content = self._generate_execution_html(results)
            
            self.write({
                'execution_results': html_content,
                'processing_progress': False  # Clear progress since we're done
            })
            
            return self._reload_wizard()
            
        except Exception as e:
            self.execution_results = f"<div class='alert alert-danger'>Execution Error: {str(e)}</div>"
            return self._reload_wizard()

    def action_download_report(self):
        """Download detailed report as HTML file"""
        self.ensure_one()
        
        # Create comprehensive report
        report_html = self._create_full_report()
        
        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'attribute_cleanup_report_{self.category_id.name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html',
            'type': 'binary',
            'datas': base64.b64encode(report_html.encode('utf-8')).decode('utf-8'),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'text/html'
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def _generate_preview_html(self, preview):
        """Generate HTML for preview results with two product lists"""
        if 'error' in preview:
            return f"<div class='alert alert-danger'><h4>Error</h4><p>{preview['error']}</p></div>"
        
        # Generate detailed preview with two sections
        html = f"""
        <div class='alert alert-info'>
            <h4>📋 Preview Results for: {preview['category_name']}</h4>
            <div class='row'>
                <div class='col-md-6'>
                    <h5>📊 Summary</h5>
                    <table class='table table-sm'>
                        <tr><td><strong>Total Products in Category:</strong></td><td>{preview['total_count']}</td></tr>
                        <tr style='color: #d68910;'><td><strong>Products WITH Attributes:</strong></td><td>{preview['with_attributes_count']}</td></tr>
                        <tr style='color: #28b463;'><td><strong>Products WITHOUT Attributes:</strong></td><td>{preview['without_attributes_count']}</td></tr>
                        <tr><td><strong>Total Attributes to Remove:</strong></td><td>{preview['summary']['total_attributes']}</td></tr>
                        <tr><td><strong>Total Variants to Remove:</strong></td><td>{preview['summary']['total_variants']}</td></tr>
                        <tr><td><strong>Active Products:</strong></td><td>{preview['summary']['active_products']}</td></tr>
                        <tr><td><strong>Inactive Products:</strong></td><td>{preview['summary']['inactive_products']}</td></tr>
                    </table>
                </div>
            </div>
        """
        
        # Products WITH attributes section
        if preview['products_with_attributes']:
            html += """
            <div style='border: 2px solid #f39c12; border-radius: 5px; padding: 15px; margin: 15px 0; background-color: #fef9e7;'>
                <h5 style='color: #d68910;'>⚠️ Products WITH Attributes (Will be processed)</h5>
                <table class='table table-striped table-sm'>
                    <thead style='background-color: #f39c12; color: white;'>
                        <tr>
                            <th>ID</th>
                            <th>Product Name</th>
                            <th>Attributes</th>
                            <th>Variants</th>
                            <th>Price</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for product in preview['products_with_attributes'][:20]:  # Show first 20
                status = "✅ Active" if product['active'] else "❌ Inactive"
                html += f"""
                <tr>
                    <td>{product['id']}</td>
                    <td>{product['name']}</td>
                    <td><span style='color: #d68910; font-weight: bold;'>{product['attribute_count']}</span></td>
                    <td><span style='color: #d68910; font-weight: bold;'>{product['variant_count']}</span></td>
                    <td>{product['list_price']}</td>
                    <td>{status}</td>
                </tr>
                """
            
            if len(preview['products_with_attributes']) > 20:
                html += f"<tr><td colspan='6'><em>... and {len(preview['products_with_attributes']) - 20} more products with attributes</em></td></tr>"
            
            html += "</tbody></table></div>"
        
        # Products WITHOUT attributes section
        if preview['products_without_attributes']:
            html += """
            <div style='border: 2px solid #27ae60; border-radius: 5px; padding: 15px; margin: 15px 0; background-color: #eafaf1;'>
                <h5 style='color: #27ae60;'>✅ Products WITHOUT Attributes (No action needed)</h5>
                <table class='table table-striped table-sm'>
                    <thead style='background-color: #27ae60; color: white;'>
                        <tr>
                            <th>ID</th>
                            <th>Product Name</th>
                            <th>Price</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for product in preview['products_without_attributes'][:20]:  # Show first 20
                status = "✅ Active" if product['active'] else "❌ Inactive"
                html += f"""
                <tr>
                    <td>{product['id']}</td>
                    <td>{product['name']}</td>
                    <td>{product['list_price']}</td>
                    <td>{status}</td>
                </tr>
                """
            
            if len(preview['products_without_attributes']) > 20:
                html += f"<tr><td colspan='4'><em>... and {len(preview['products_without_attributes']) - 20} more products without attributes</em></td></tr>"
            
            html += "</tbody></table></div>"
        
        html += "</div>"
        return html

    def _initialize_progress_html(self, total_products, total_batches):
        """Initialize progress HTML display"""
        return f"""
        <div class='alert alert-info'>
            <h4>🔄 Processing Started</h4>
            <p><strong>Total Products:</strong> {total_products}</p>
            <p><strong>Total Batches:</strong> {total_batches} (batch size: {self.batch_size})</p>
            <p><strong>Status:</strong> Initializing...</p>
        </div>
        """

    def _update_progress_html(self, batch_num, total_batches, batch_results, overall_results):
        """Update progress HTML with current batch results"""
        progress_percent = (batch_num / total_batches) * 100
        
        # Create progress bar
        progress_bar = f"""
        <div style='background-color: #f0f0f0; border-radius: 10px; overflow: hidden; margin: 10px 0;'>
            <div style='background-color: #28a745; height: 25px; width: {progress_percent:.1f}%; 
                        display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;'>
                {progress_percent:.1f}%
            </div>
        </div>
        """
        
        # Latest batch info
        latest_info = ""
        if batch_results.get('processed_products'):
            latest_product = batch_results['processed_products'][-1]
            status_icon = "✅" if latest_product['status'] == 'success' else "❌"
            latest_info = f"<p><strong>Latest:</strong> {status_icon} {latest_product['name']}</p>"
        
        return f"""
        <div class='alert alert-info'>
            <h4>🔄 Processing in Progress...</h4>
            <p><strong>Batch {batch_num} of {total_batches}</strong> 
               (Products {(batch_num-1) * self.batch_size + 1}-{min(batch_num * self.batch_size, overall_results['total_to_process'])})</p>
            {progress_bar}
            <div class='row'>
                <div class='col-md-4'>
                    <p>✅ <strong>Successful:</strong> {overall_results['success_count']}</p>
                </div>
                <div class='col-md-4'>
                    <p>❌ <strong>Errors:</strong> {overall_results['error_count']}</p>
                </div>
                <div class='col-md-4'>
                    <p>⏳ <strong>Remaining:</strong> {overall_results['total_to_process'] - overall_results['success_count'] - overall_results['error_count']}</p>
                </div>
            </div>
            {latest_info}
        </div>
        """

    def _execute_cleanup_with_batching(self, target_products):
        """Execute cleanup with batching and real-time progress updates"""
        batch_size = self.batch_size or 10
        total_products = len(target_products)
        
        # Initialize overall results tracking
        overall_results = {
            'total_to_process': total_products,
            'total_processed': 0,
            'success_count': 0,
            'error_count': 0,
            'attributes_removed': 0,
            'variants_removed': 0,
            'processed_products': []
        }
        
        # Process products in batches
        for i in range(0, total_products, batch_size):
            batch_products = target_products[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            
            # Process current batch
            batch_results = self._process_single_batch(batch_products, batch_num)
            
            # Update overall results
            overall_results['total_processed'] += batch_results['total_processed']
            overall_results['success_count'] += batch_results['success_count']
            overall_results['error_count'] += batch_results['error_count']
            overall_results['attributes_removed'] += batch_results['attributes_removed']
            overall_results['variants_removed'] += batch_results['variants_removed']
            overall_results['processed_products'].extend(batch_results['processed_products'])
            
            # Update progress display
            progress_html = self._update_progress_html(batch_num, self.total_batches, batch_results, overall_results)
            
            self.write({
                'current_batch': batch_num,
                'processing_progress': progress_html
            })
            
            # Commit changes to ensure progress is saved
            self.env.cr.commit()
            
            # Brief pause between batches (simulate real-time processing)
            import time
            time.sleep(0.5)
        
        return overall_results

    def _process_single_batch(self, batch_products, batch_num):
        """Process a single batch of products"""
        results = {
            'batch_number': batch_num,
            'total_processed': len(batch_products),
            'success_count': 0,
            'error_count': 0,
            'attributes_removed': 0,
            'variants_removed': 0,
            'processed_products': []
        }
        
        # Process each product in the batch
        for product in batch_products:
            product_result = {
                'id': product.id,
                'name': product.name,
                'status': 'success',
                'attributes_removed': 0,
                'variants_removed': 0,
                'error_message': ''
            }
            
            try:
                # Count before removal
                initial_attributes = len(product.attribute_line_ids)
                initial_variants = len(product.product_variant_ids)
                
                # Remove attributes
                if product.attribute_line_ids:
                    product.attribute_line_ids.unlink()
                    product_result['attributes_removed'] = initial_attributes
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
                    product_result['variants_removed'] = variants_removed
                    results['variants_removed'] += variants_removed
                
                # Clear main variant attributes
                if product.product_variant_id:
                    product.product_variant_id.write({
                        'attribute_value_ids': [(5, 0, 0)]
                    })
                
                results['success_count'] += 1
                
            except Exception as e:
                product_result['status'] = 'error'
                product_result['error_message'] = str(e)
                results['error_count'] += 1
            
            results['processed_products'].append(product_result)
        
        return results

    def _generate_execution_html(self, results):
        """Generate HTML for execution results"""
        html = f"""
        <div class='alert alert-success'>
            <h4>✅ Cleanup Execution Results</h4>
            <div class='row'>
                <div class='col-md-6'>
                    <table class='table table-sm'>
                        <tr><td><strong>Products Processed:</strong></td><td>{results['total_processed']}</td></tr>
                        <tr><td><strong>Successful:</strong></td><td style='color: green;'>{results['success_count']}</td></tr>
                        <tr><td><strong>Errors:</strong></td><td style='color: red;'>{results['error_count']}</td></tr>
                        <tr><td><strong>Attributes Removed:</strong></td><td>{results['attributes_removed']}</td></tr>
                        <tr><td><strong>Variants Removed:</strong></td><td>{results['variants_removed']}</td></tr>
                    </table>
                </div>
            </div>
        """
        
        if results.get('processed_products'):
            html += """
            <h5>📋 Processing Details</h5>
            <table class='table table-striped table-sm'>
                <thead>
                    <tr><th>Product Name</th><th>Status</th><th>Attributes Removed</th><th>Variants Removed</th></tr>
                </thead>
                <tbody>
            """
            
            for product in results['processed_products']:
                status_icon = "✅" if product['status'] == 'success' else "❌"
                html += f"""
                <tr>
                    <td>{product['name']}</td>
                    <td>{status_icon} {product['status']}</td>
                    <td>{product.get('attributes_removed', 0)}</td>
                    <td>{product.get('variants_removed', 0)}</td>
                </tr>
                """
            
            html += "</tbody></table>"
        
        html += "</div>"
        return html

    def _execute_cleanup_with_tracking(self):
        """Legacy method - now redirects to batching approach for backward compatibility"""
        target_products = self.env['product.template'].search([
            ('categ_id', '=', self.category_id.id),
            ('attribute_line_ids', '!=', False)
        ])
        return self._execute_cleanup_with_batching(target_products)

    def _create_full_report(self):
        """Create comprehensive downloadable report"""
        report_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Product Attribute Cleanup Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #f2f2f2; }}
                .success {{ color: green; }}
                .error {{ color: red; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Product Attribute Cleanup Report</h1>
                <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Category:</strong> {self.category_id.name} (ID: {self.category_id.id})</p>
            </div>
            
            <div class="section">
                <h2>Preview Results</h2>
                {self.preview_results or 'No preview data available'}
            </div>
            
            <div class="section">
                <h2>Execution Results</h2>
                {self.execution_results or 'No execution data available'}
            </div>
        </body>
        </html>
        """
        return report_html

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