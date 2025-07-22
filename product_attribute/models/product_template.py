from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def remove_all_attributes_scheduled(self, category_id=None, category_name=None):
        """
        Scheduled action to remove attributes from all products in specified category
        Compatible with the multi-step wizard approach
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
                # Default category for backward compatibility
                category_name = "Lotion Pumps (Sıvı Sabun Pompası)"
                target_category = self.env['product.category'].search([
                    ('name', '=', category_name)
                ], limit=1)
                
                if not target_category:
                    _logger.error(f"Scheduled cleanup failed: Category '{category_name}' not found")
                    return False
            
            # Get basic preview info
            preview = self.get_category_preview(target_category.id)
            if 'error' in preview:
                _logger.error(f"Preview failed: {preview['error']}")
                return False
            
            if preview['with_attributes_count'] == 0:
                _logger.info(f"No products with attributes found in category '{target_category.name}' - nothing to do")
                return True
            
            _logger.info(f"Starting cleanup of {preview['with_attributes_count']} products in category '{target_category.name}'")
            
            # Find all products in this category that have attributes
            target_products = self.search([
                ('categ_id', '=', target_category.id),
                ('attribute_line_ids', '!=', False)
            ])
            
            success_count = 0
            error_count = 0
            
            # Process each product - scheduled actions can handle all at once
            for product in target_products:
                try:
                    # Remove attributes
                    if product.attribute_line_ids:
                        product.attribute_line_ids.unlink()
                    
                    if hasattr(product, 'product_template_attribute_value_ids'):
                        product.product_template_attribute_value_ids.unlink()
                    
                    # Remove extra variants
                    if len(product.product_variant_ids) > 1:
                        variants_to_delete = product.product_variant_ids.filtered(
                            lambda v: v.id != product.product_variant_id.id
                        )
                        variants_to_delete.unlink()
                    
                    # Clear main variant attributes
                    if product.product_variant_id:
                        product.product_variant_id.write({
                            'attribute_value_ids': [(5, 0, 0)]
                        })
                    
                    success_count += 1
                    
                except Exception as e:
                    _logger.error(f"Error processing product {product.name}: {str(e)}")
                    error_count += 1
                    continue
            
            _logger.info(f"Cleanup completed: {success_count}/{len(target_products)} products processed successfully")
            return True
            
        except Exception as e:
            _logger.error(f"Failed to execute scheduled category cleanup: {str(e)}")
            return False

    @api.model
    def get_category_preview(self, category_id=None):
        """
        Preview method - returns essential information for both wizard and scheduled actions
        Optimized for multi-step wizard compatibility
        """
        try:
            if not category_id:
                return {'error': 'Category ID is required'}
            
            # Find the category
            target_category = self.env['product.category'].browse(category_id)
            if not target_category.exists():
                return {'error': f'Category with ID {category_id} not found'}
            
            # Find all products in this category
            all_products = self.search([
                ('categ_id', '=', target_category.id)
            ])
            
            if not all_products:
                return {
                    'category_id': target_category.id,
                    'category_name': target_category.name,
                    'total_count': 0,
                    'with_attributes_count': 0,
                    'without_attributes_count': 0,
                    'summary': {
                        'total_attributes': 0,
                        'total_variants': 0,
                        'active_products': 0,
                        'inactive_products': 0
                    }
                }
            
            # Split products into two groups
            products_with_attributes = all_products.filtered(lambda p: p.attribute_line_ids)
            products_without_attributes = all_products.filtered(lambda p: not p.attribute_line_ids)
            
            # Calculate totals efficiently
            total_attributes = sum(len(p.attribute_line_ids) for p in products_with_attributes)
            total_variants = sum(len(p.product_variant_ids) for p in products_with_attributes)
            active_products = len([p for p in all_products if p.active])
            
            result = {
                'category_id': target_category.id,
                'category_name': target_category.name,
                'total_count': len(all_products),
                'with_attributes_count': len(products_with_attributes),
                'without_attributes_count': len(products_without_attributes),
                'summary': {
                    'total_attributes': total_attributes,
                    'total_variants': total_variants,
                    'active_products': active_products,
                    'inactive_products': len(all_products) - active_products
                }
            }
            
            return result
            
        except Exception as e:
            _logger.error(f"Error in category preview: {str(e)}")
            return {'error': str(e)}