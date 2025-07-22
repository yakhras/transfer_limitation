from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def remove_all_attributes_scheduled(self, category_id=None, category_name=None, batch_size=100):
        """
        Scheduled action to remove attributes from all products in specified category
        MODIFIED: Added batching and improved error handling to prevent stuck processing
        
        Parameters:
        - category_id: ID of category to process (takes priority over category_name)
        - category_name: Name of category to process (fallback if category_id not provided)
        - batch_size: Number of products to process in each batch (default: 100)
        """
        try:
            # Determine target category
            target_category = None
            
            if category_id:
                target_category = self.env['product.category'].browse(category_id)
                if not target_category.exists():
                    _logger.error(f"Scheduled cleanup failed: Category ID {category_id} not found")
                    return False
            elif category_name:
                target_category = self.env['product.category'].search([
                    ('name', '=', category_name)
                ], limit=1)
                if not target_category:
                    _logger.error(f"Scheduled cleanup failed: Category '{category_name}' not found")
                    return False
            else:
                # TODO: This should be configurable via system parameters or config
                # For now, using the original hardcoded category name for backward compatibility
                category_name = "Lotion Pumps (Sıvı Sabun Pompası)"
                target_category = self.env['product.category'].search([
                    ('name', '=', category_name)
                ], limit=1)
                
                if not target_category:
                    _logger.error(f"Scheduled cleanup failed: Category '{category_name}' not found")
                    return False
            
            # Auto-preview before execution (for logging)
            _logger.info("="*50)
            _logger.info("STARTING SCHEDULED CATEGORY CLEANUP WITH PREVIEW")
            _logger.info("="*50)
            
            preview = self.get_category_preview(target_category.id)
            if 'error' in preview:
                _logger.error(f"Preview failed: {preview['error']}")
                return False
            
            # Log preview results
            _logger.info(f"PREVIEW RESULTS:")
            _logger.info(f"  Category: {preview['category_name']} (ID: {preview['category_id']})")
            _logger.info(f"  Total products in category: {preview['total_count']}")
            _logger.info(f"  Products with attributes: {preview['with_attributes_count']}")
            _logger.info(f"  Products without attributes: {preview['without_attributes_count']}")
            _logger.info(f"  Total attributes to remove: {preview['summary']['total_attributes']}")
            _logger.info(f"  Total variants to remove: {preview['summary']['total_variants']}")
            _logger.info(f"  Active products: {preview['summary']['active_products']}")
            _logger.info(f"  Inactive products: {preview['summary']['inactive_products']}")
            
            if preview['with_attributes_count'] == 0:
                _logger.info("No products with attributes found - nothing to do")
                return True
            
            # Proceed with actual cleanup - MODIFIED: Added batching
            _logger.info("="*50)
            _logger.info("STARTING ACTUAL CLEANUP WITH BATCHING")
            _logger.info(f"Batch size: {batch_size}")
            _logger.info("="*50)
            
            # Find all products in this category that have attributes
            target_products = self.search([
                ('categ_id', '=', target_category.id),
                ('attribute_line_ids', '!=', False)
            ])
            
            total_products = len(target_products)
            total_batches = (total_products + batch_size - 1) // batch_size  # Ceiling division
            
            _logger.info(f"Found {total_products} products to process in {total_batches} batches")
            
            # Initialize counters
            overall_success_count = 0
            overall_error_count = 0
            overall_attributes_removed = 0
            overall_variants_removed = 0
            
            # Process products in batches - MODIFIED: Added batching to prevent timeout
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min((batch_num + 1) * batch_size, total_products)
                batch_products = target_products[start_idx:end_idx]
                
                _logger.info(f"Processing batch {batch_num + 1}/{total_batches}: products {start_idx + 1}-{end_idx}")
                
                # Process current batch
                batch_results = self._process_cleanup_batch(batch_products, batch_num + 1)
                
                # Update overall counters
                overall_success_count += batch_results['success_count']
                overall_error_count += batch_results['error_count'] 
                overall_attributes_removed += batch_results['attributes_removed']
                overall_variants_removed += batch_results['variants_removed']
                
                # Log batch results
                _logger.info(f"Batch {batch_num + 1} completed: {batch_results['success_count']}/{len(batch_products)} successful")
                
                # REMOVED: Manual commits and delays that caused issues
            
            _logger.info("="*50)
            _logger.info(f"CLEANUP COMPLETED:")
            _logger.info(f"  Total processed: {overall_success_count + overall_error_count}/{total_products}")
            _logger.info(f"  Successful: {overall_success_count}")
            _logger.info(f"  Errors: {overall_error_count}")
            _logger.info(f"  Attributes removed: {overall_attributes_removed}")
            _logger.info(f"  Variants removed: {overall_variants_removed}")
            _logger.info("="*50)
            
            return True
            
        except Exception as e:
            _logger.error(f"Failed to execute scheduled category cleanup: {str(e)}")
            return False

    def _process_cleanup_batch(self, batch_products, batch_num):
        """
        Process a single batch of products for cleanup
        ADDED: Helper method to process batches efficiently
        """
        results = {
            'batch_number': batch_num,
            'success_count': 0,
            'error_count': 0,
            'attributes_removed': 0,
            'variants_removed': 0
        }
        
        for product in batch_products:
            try:
                # Count before removal for statistics
                initial_attributes = len(product.attribute_line_ids)
                initial_variants = len(product.product_variant_ids)
                
                # Remove attributes
                if product.attribute_line_ids:
                    product.attribute_line_ids.unlink()
                    results['attributes_removed'] += initial_attributes
                
                # Remove template attribute values
                if hasattr(product, 'product_template_attribute_value_ids'):
                    product.product_template_attribute_value_ids.unlink()
                
                # Remove extra variants (keep only the main variant)
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
                _logger.debug(f"✓ Processed: {product.name}")
                
            except Exception as e:
                _logger.error(f"✗ Error processing {product.name}: {str(e)}")
                results['error_count'] += 1
                continue
        
        return results

    @api.model
    def get_category_preview(self, category_id=None):
        """
        Preview method to see what products would be affected before running the cleanup
        Returns both products with and without attributes for complete transparency
        MODIFIED: Improved error handling and performance
        """
        try:
            if not category_id:
                return {'error': 'Category ID is required'}
            
            # Find the category
            target_category = self.env['product.category'].browse(category_id)
            if not target_category.exists():
                return {'error': f'Category with ID {category_id} not found'}
            
            # Find ALL products in this category - MODIFIED: More efficient query
            all_products = self.search([
                ('categ_id', '=', target_category.id)
            ])
            
            if not all_products:
                return {
                    'found_category': True,
                    'category_id': target_category.id,
                    'category_name': target_category.name,
                    'total_count': 0,
                    'with_attributes_count': 0,
                    'without_attributes_count': 0,
                    'products_with_attributes': [],
                    'products_without_attributes': [],
                    'summary': {
                        'total_attributes': 0,
                        'total_variants': 0,
                        'active_products': 0,
                        'inactive_products': 0
                    }
                }
            
            # Split products into two groups: with and without attributes
            products_with_attributes = all_products.filtered(lambda p: p.attribute_line_ids)
            products_without_attributes = all_products.filtered(lambda p: not p.attribute_line_ids)
            
            # Prepare detailed preview for products WITH attributes - MODIFIED: More efficient
            with_attributes_details = []
            total_attributes = 0
            total_variants = 0
            
            for product in products_with_attributes:
                attribute_count = len(product.attribute_line_ids)
                variant_count = len(product.product_variant_ids)
                
                with_attributes_details.append({
                    'id': product.id,
                    'name': product.name,
                    'attribute_count': attribute_count,
                    'variant_count': variant_count,
                    'attributes': [attr.name for attr in product.attribute_line_ids.mapped('attribute_id')],
                    'list_price': product.list_price,
                    'active': product.active
                })
                
                total_attributes += attribute_count
                total_variants += variant_count
            
            # Prepare detailed preview for products WITHOUT attributes
            without_attributes_details = []
            for product in products_without_attributes:
                without_attributes_details.append({
                    'id': product.id,
                    'name': product.name,
                    'list_price': product.list_price,
                    'active': product.active
                })
            
            result = {
                'found_category': True,
                'category_id': target_category.id,
                'category_name': target_category.name,
                'total_count': len(all_products),
                'with_attributes_count': len(products_with_attributes),
                'without_attributes_count': len(products_without_attributes),
                'products_with_attributes': with_attributes_details,
                'products_without_attributes': without_attributes_details,
                'summary': {
                    'total_attributes': total_attributes,
                    'total_variants': total_variants,
                    'active_products': len([p for p in all_products if p.active]),
                    'inactive_products': len([p for p in all_products if not p.active])
                }
            }
            
            _logger.info(f"Preview for category '{target_category.name}' (ID: {category_id}):")
            _logger.info(f"  Total products: {result['total_count']}")
            _logger.info(f"  With attributes: {result['with_attributes_count']}")
            _logger.info(f"  Without attributes: {result['without_attributes_count']}")
            
            return result
            
        except Exception as e:
            _logger.error(f"Error in category preview: {str(e)}")
            return {'error': str(e)}

    @api.model 
    def cleanup_category_by_name(self, category_name, batch_size=100):
        """
        ADDED: Convenience method to clean up category by name
        Useful for scheduled actions and external calls
        """
        return self.remove_all_attributes_scheduled(
            category_name=category_name, 
            batch_size=batch_size
        )
    
    @api.model
    def cleanup_category_by_id(self, category_id, batch_size=100):
        """
        ADDED: Convenience method to clean up category by ID
        Useful for scheduled actions and external calls
        """
        return self.remove_all_attributes_scheduled(
            category_id=category_id, 
            batch_size=batch_size
        )