from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def remove_all_attributes_scheduled(self):
        """
        Scheduled action to remove attributes - Starting with product 22006
        """
        try:
            # Stage 1: Start with specific product 22006
            target_product = self.search([
                ('id', '=', 22006),
                ('attribute_line_ids', '!=', False)
            ])
            
            if not target_product:
                _logger.info("Product 22006 not found or has no attributes")
                return True
            
            _logger.info(f"Processing product 22006: {target_product.name}")
            
            # Store initial state for logging
            initial_attributes = len(target_product.attribute_line_ids)
            initial_variants = len(target_product.product_variant_ids)
            
            try:
                # Remove attribute lines
                if target_product.attribute_line_ids:
                    _logger.info(f"Removing {initial_attributes} attribute lines")
                    target_product.attribute_line_ids.unlink()
                
                # Remove product template attribute values (for newer Odoo versions)
                if hasattr(target_product, 'product_template_attribute_value_ids'):
                    attr_values = len(target_product.product_template_attribute_value_ids)
                    if attr_values > 0:
                        _logger.info(f"Removing {attr_values} template attribute values")
                        target_product.product_template_attribute_value_ids.unlink()
                
                # Handle product variants - keep only the main variant
                if len(target_product.product_variant_ids) > 1:
                    variants_to_delete = target_product.product_variant_ids.filtered(
                        lambda v: v.id != target_product.product_variant_id.id
                    )
                    _logger.info(f"Removing {len(variants_to_delete)} extra variants, keeping main variant")
                    variants_to_delete.unlink()
                
                # Clear attribute values from the main variant
                if target_product.product_variant_id:
                    target_product.product_variant_id.write({
                        'attribute_value_ids': [(5, 0, 0)]
                    })
                    _logger.info("Cleared attribute values from main variant")
                
                # Final verification
                final_attributes = len(target_product.attribute_line_ids)
                final_variants = len(target_product.product_variant_ids)
                
                _logger.info(f"SUCCESS - Product 22006 processed:")
                _logger.info(f"  - Attributes: {initial_attributes} → {final_attributes}")
                _logger.info(f"  - Variants: {initial_variants} → {final_variants}")
                
                return True
                
            except Exception as e:
                _logger.error(f"Error processing product 22006: {str(e)}")
                return False
            
        except Exception as e:
            _logger.error(f"Failed to execute scheduled attribute removal: {str(e)}")
            return False
