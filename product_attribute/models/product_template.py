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
                    
                    
                    processed_count += 1
                    
                except Exception as e:
                    _logger.error(f"Error removing attributes from {product.name}: {str(e)}")
                    continue
            
            return True
            
        except Exception as e:
            _logger.error(f"Failed to execute scheduled attribute removal: {str(e)}")
            return False