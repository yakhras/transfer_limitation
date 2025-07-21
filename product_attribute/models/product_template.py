from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def remove_all_attributes_scheduled(self):
        """
        Scheduled action to remove attributes from all products in specified category
        Note: This method will need configuration to specify which category_id to use
        """
        try:
            # TODO: This should be configurable via system parameters or config
            # For now, using the original hardcoded category name for backward compatibility
            category_name = "Lotion Pumps (Sıvı Sabun Pompası)"
            
            # Find category by name (backward compatibility)
            target_category = self.env['product.category'].search([
                ('name', '=', category_name)
            ], limit=1)
            
            if not target_category:
                _logger.error(f"Scheduled cleanup failed: Category '{category_name}' not found")
                return False
            
            # Auto-preview before execution (for logging)
            _logger.info("="*50)
            _logger.info("STARTING CATEGORY CLEANUP WITH PREVIEW")
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
            
            # Proceed with actual cleanup
            _logger.info("="*50)
            _logger.info("STARTING ACTUAL CLEANUP")
            _logger.info("="*50)
            
            # Find all products in this category that have attributes
            target_products = self.search([
                ('categ_id', '=', target_category.id),
                ('attribute_line_ids', '!=', False)
            ])
            
            success_count = 0
            
            # Process each product
            for product in target_products:
                try:
                    # Remove attributes
                    if product.attribute_line_ids:
                        product.attribute_line_ids.unlink()
                    
                    if hasattr(product, 'product_template_attribute_value_ids'):
                        product.product_template_attribute_value_ids.unlink()
                    
                    if len(product.product_variant_ids) > 1:
                        variants_to_delete = product.product_variant_ids.filtered(
                            lambda v: v.id != product.product_variant_id.id
                        )
                        variants_to_delete.unlink()
                    
                    if product.product_variant_id:
                        product.product_variant_id.write({
                            'attribute_value_ids': [(5, 0, 0)]
                        })
                    
                    success_count += 1
                    _logger.info(f"✓ Processed: {product.name}")
                    
                except Exception as e:
                    _logger.error(f"✗ Error processing {product.name}: {str(e)}")
                    continue
            
            _logger.info("="*50)
            _logger.info(f"CLEANUP COMPLETED: {success_count}/{len(target_products)} products processed successfully")
            _logger.info("="*50)
            return True
            
        except Exception as e:
            _logger.error(f"Failed to execute category cleanup: {str(e)}")
            return False

    @api.model
    def get_category_preview(self, category_id=None):
        """
        Preview method to see what products would be affected before running the cleanup
        Returns both products with and without attributes for complete transparency
        """
        try:
            if not category_id:
                return {'error': 'Category ID is required'}
            
            # Find the category
            target_category = self.env['product.category'].browse(category_id)
            if not target_category.exists():
                return {'error': f'Category with ID {category_id} not found'}
            
            # Find ALL products in this category
            all_products = self.search([
                ('categ_id', '=', target_category.id)
            ])
            
            # Split products into two groups: with and without attributes
            products_with_attributes = all_products.filtered(lambda p: p.attribute_line_ids)
            products_without_attributes = all_products.filtered(lambda p: not p.attribute_line_ids)
            
            # Prepare detailed preview for products WITH attributes
            with_attributes_details = []
            for product in products_with_attributes:
                with_attributes_details.append({
                    'id': product.id,
                    'name': product.name,
                    'attribute_count': len(product.attribute_line_ids),
                    'variant_count': len(product.product_variant_ids),
                    'attributes': [attr.name for attr in product.attribute_line_ids.mapped('attribute_id')],
                    'list_price': product.list_price,
                    'active': product.active
                })
            
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
                    'total_attributes': sum(len(p.attribute_line_ids) for p in products_with_attributes),
                    'total_variants': sum(len(p.product_variant_ids) for p in products_with_attributes),
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