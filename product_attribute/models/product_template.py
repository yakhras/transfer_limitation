from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def remove_all_attributes_scheduled(self):
        """
        Scheduled action to remove attributes from all products in "Lotion Pumps (Sıvı Sabun Pompası)" category
        """
        try:
            # Stage 2: Target specific category - Lotion Pumps
            category_name = "Lotion Pumps (Sıvı Sabun Pompası)"
            
            # Find the category first
            target_category = self.env['product.category'].search([
                ('name', '=', category_name)
            ], limit=1)
            
            if not target_category:
                _logger.warning(f"Category '{category_name}' not found. Searching for similar names...")
                # Try to find similar category names
                similar_categories = self.env['product.category'].search([
                    '|', '|',
                    ('name', 'ilike', 'lotion'),
                    ('name', 'ilike', 'pump'),
                    ('name', 'ilike', 'sabun')
                ])
                
                if similar_categories:
                    _logger.info("Found similar categories:")
                    for cat in similar_categories:
                        _logger.info(f"  - ID: {cat.id}, Name: {cat.name}")
                
                _logger.error(f"Cannot proceed without finding category '{category_name}'")
                return False
            
            _logger.info(f"Found target category: {target_category.name} (ID: {target_category.id})")
            
            # Find all products in this category that have attributes
            target_products = self.search([
                ('categ_id', '=', target_category.id),
                ('attribute_line_ids', '!=', False)
            ])
            
            if not target_products:
                _logger.info(f"No products with attributes found in category '{category_name}'")
                return True
            
            total_products = len(target_products)
            _logger.info(f"Found {total_products} products with attributes in category '{category_name}'")
            
            # Process statistics
            stats = {
                'total_found': total_products,
                'processed': 0,
                'success': 0,
                'errors': 0,
                'total_attributes_removed': 0,
                'total_variants_removed': 0
            }
            
            # Process each product
            for index, product in enumerate(target_products, 1):
                stats['processed'] += 1
                
                _logger.info(f"Processing {index}/{total_products}: {product.name} (ID: {product.id})")
                
                try:
                    # Store initial state
                    initial_attributes = len(product.attribute_line_ids)
                    initial_variants = len(product.product_variant_ids)
                    
                    # Remove attribute lines
                    if product.attribute_line_ids:
                        product.attribute_line_ids.unlink()
                        stats['total_attributes_removed'] += initial_attributes
                    
                    # Remove product template attribute values
                    if hasattr(product, 'product_template_attribute_value_ids'):
                        if product.product_template_attribute_value_ids:
                            product.product_template_attribute_value_ids.unlink()
                    
                    # Handle product variants - keep only the main variant
                    variants_deleted = 0
                    if len(product.product_variant_ids) > 1:
                        variants_to_delete = product.product_variant_ids.filtered(
                            lambda v: v.id != product.product_variant_id.id
                        )
                        variants_deleted = len(variants_to_delete)
                        variants_to_delete.unlink()
                        stats['total_variants_removed'] += variants_deleted
                    
                    # Clear attribute values from main variant
                    if product.product_variant_id:
                        product.product_variant_id.write({
                            'attribute_value_ids': [(5, 0, 0)]
                        })
                    
                    stats['success'] += 1
                    _logger.info(f"  ✓ SUCCESS: Removed {initial_attributes} attributes, {variants_deleted} variants")
                    
                except Exception as e:
                    stats['errors'] += 1
                    _logger.error(f"  ✗ ERROR processing {product.name}: {str(e)}")
                    continue
            
            # Final summary
            _logger.info("="*60)
            _logger.info(f"CATEGORY CLEANUP COMPLETED: {category_name}")
            _logger.info(f"Products found: {stats['total_found']}")
            _logger.info(f"Products processed: {stats['processed']}")
            _logger.info(f"Successful: {stats['success']}")
            _logger.info(f"Errors: {stats['errors']}")
            _logger.info(f"Total attributes removed: {stats['total_attributes_removed']}")
            _logger.info(f"Total variants removed: {stats['total_variants_removed']}")
            _logger.info("="*60)
            
            return True
            
        except Exception as e:
            _logger.error(f"Failed to execute category-based attribute removal: {str(e)}")
            return False

    