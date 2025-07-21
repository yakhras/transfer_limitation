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
        domain=[('product_tmpl_ids', '!=', False)],  # Only categories with products
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
        """Execute the actual cleanup"""
        self.ensure_one()
        
        if self.state != 'preview':
            self.preview_results = "<div class='alert alert-warning'>Please run preview first!</div>"
            return self._reload_wizard()
        
        if not self.category_id:
            self.execution_results = "<div class='alert alert-warning'>No category selected!</div>"
            return self._reload_wizard()
        
        try:
            # Execute cleanup and track results
            results = self._execute_cleanup_with_tracking()
            
            # Generate execution HTML report
            html_content = self._generate_execution_html(results)
            
            self.write({
                'execution_results': html_content,
                'state': 'executed'
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
        """Execute cleanup and track detailed results"""
        # Find products with attributes in the selected category
        target_products = self.env['product.template'].search([
            ('categ_id', '=', self.category_id.id),
            ('attribute_line_ids', '!=', False)
        ])
        
        results = {
            'total_processed': len(target_products),
            'success_count': 0,
            'error_count': 0,
            'attributes_removed': 0,
            'variants_removed': 0,
            'processed_products': []
        }
        
        # Process each product
        for product in target_products:
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