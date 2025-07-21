# -*- coding: utf-8 -*-

from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def remove_all_attributes_scheduled(self):
        """
        Scheduled action to remove all attributes from all product templates
        """
        try:
            # Find all product templates that have attributes
            products_with_attributes = self.search([
                ('attribute_line_ids', '!=', False)
            ])
            
            total_products = len(products_with_attributes)
            processed_count = 0
            
            _logger.info(f"Starting to remove attributes from {total_products} products")
            
            for product in products_with_attributes:
                try:
                    # Remove attribute lines
                    if product.attribute_line_ids:
                        product.attribute_line_ids.unlink()
                    
                    # Remove product template attribute values (for newer Odoo versions)
                    if hasattr(product, 'product_template_attribute_value_ids'):
                        product.product_template_attribute_value_ids.unlink()
                    
                    # Handle product variants - keep only the main variant
                    if len(product.product_variant_ids) > 1:
                        variants_to_delete = product.product_variant_ids.filtered(
                            lambda v: v.id != product.product_variant_id.id
                        )
                        variants_to_delete.unlink()
                    
                    # Clear attribute values from the main variant
                    if product.product_variant_id:
                        product.product_variant_id.write({
                            'attribute_value_ids': [(5, 0, 0)]
                        })
                    
                    processed_count += 1
                    _logger.info(f"Processed {processed_count}/{total_products}: {product.name}")
                    
                except Exception as e:
                    _logger.error(f"Error removing attributes from {product.name}: {str(e)}")
                    continue
            
            _logger.info(f"Completed: Removed attributes from {processed_count} out of {total_products} products")
            return True
            
        except Exception as e:
            _logger.error(f"Failed to execute scheduled attribute removal: {str(e)}")
            return False