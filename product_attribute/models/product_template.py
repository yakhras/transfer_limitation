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
        


    @api.model
    def get_assignment_preview(self, category_id=None, attribute_ids=None):
        """
        Preview method for attribute assignment - shows what will happen when assigning attributes
        Returns information about products that need attribute assignment
        """
        try:
            if not category_id:
                return {'error': 'Category ID is required'}
                
            if not attribute_ids:
                return {'error': 'At least one attribute ID is required'}
            
            # Find the category
            target_category = self.env['product.category'].browse(category_id)
            if not target_category.exists():
                return {'error': f'Category with ID {category_id} not found'}
            
            # Find selected attributes
            selected_attributes = self.env['product.attribute'].browse(attribute_ids)
            if not selected_attributes:
                return {'error': 'Selected attributes not found'}
            
            # Find all products in this category
            all_products = self.search([
                ('categ_id', '=', target_category.id)
            ])
            
            if not all_products:
                return {
                    'category_id': target_category.id,
                    'category_name': target_category.name,
                    'total_products': 0,
                    'products_without_selected_attributes': 0,
                    'products_with_selected_attributes': 0,
                    'attribute_details': [],
                    'total_values_to_assign': 0
                }
            
            # Analyze which products need attribute assignment
            products_needing_assignment = []
            products_already_have_attributes = []
            
            for product in all_products:
                existing_attribute_ids = product.attribute_line_ids.mapped('attribute_id.id')
                selected_attribute_ids = selected_attributes.ids
                
                # Check if product has ALL selected attributes
                if all(attr_id in existing_attribute_ids for attr_id in selected_attribute_ids):
                    products_already_have_attributes.append(product.id)
                else:
                    products_needing_assignment.append(product.id)
            
            # Prepare attribute details for preview
            attribute_details = []
            total_values_to_assign = 0
            
            for attribute in selected_attributes:
                values = attribute.value_ids
                attribute_info = {
                    'id': attribute.id,
                    'name': attribute.name,
                    'value_count': len(values),
                    'values': [value.name for value in values],
                }
                attribute_details.append(attribute_info)
                
                # Calculate total values that will be assigned
                # (products needing assignment × values per attribute)
                total_values_to_assign += len(products_needing_assignment) * len(values)
            
            result = {
                'category_id': target_category.id,
                'category_name': target_category.name,
                'total_products': len(all_products),
                'products_without_selected_attributes': len(products_needing_assignment),
                'products_with_selected_attributes': len(products_already_have_attributes),
                'attribute_details': attribute_details,
                'total_values_to_assign': total_values_to_assign
            }
            
            _logger.info(f"Assignment preview for category '{target_category.name}' (ID: {category_id}):")
            _logger.info(f"  Total products: {result['total_products']}")
            _logger.info(f"  Products needing assignment: {result['products_without_selected_attributes']}")
            _logger.info(f"  Products already have attributes: {result['products_with_selected_attributes']}")
            _logger.info(f"  Attributes to assign: {len(selected_attributes)}")
            
            return result
            
        except Exception as e:
            _logger.error(f"Error in assignment preview: {str(e)}")
            return {'error': str(e)}

    @api.model
    def get_available_attributes_for_assignment(self, category_id=None):
        """
        Get list of attributes that can be assigned to products in a category
        Useful for populating attribute selection dropdown/checkboxes
        """
        try:
            # For now, return all product attributes
            # Could be enhanced to filter by category-specific logic if needed
            attributes = self.env['product.attribute'].search([])
            
            attribute_list = []
            for attr in attributes:
                attribute_list.append({
                    'id': attr.id,
                    'name': attr.name,
                    'value_count': len(attr.value_ids),
                    'values': [v.name for v in attr.value_ids[:5]]  # First 5 values as preview
                })
            
            return {
                'attributes': attribute_list,
                'total_count': len(attributes)
            }
            
        except Exception as e:
            _logger.error(f"Error getting available attributes: {str(e)}")
            return {'error': str(e)}

    def assign_selected_attributes(self, attribute_ids):
        """
        Assign selected attributes with ALL their values to this product
        Used by the wizard for batch processing individual products
        """
        self.ensure_one()
        
        try:
            results = {
                'success': True,
                'attribute_lines_created': 0,
                'values_assigned': 0,
                'errors': []
            }
            
            selected_attributes = self.env['product.attribute'].browse(attribute_ids)
            
            for attribute in selected_attributes:
                try:
                    # Check if product already has this attribute
                    existing_line = self.attribute_line_ids.filtered(
                        lambda l: l.attribute_id.id == attribute.id
                    )
                    
                    if not existing_line:
                        # Create new attribute line with ALL values
                        self.env['product.template.attribute.line'].create({
                            'product_tmpl_id': self.id,
                            'attribute_id': attribute.id,
                            'value_ids': [(6, 0, attribute.value_ids.ids)]
                        })
                        results['attribute_lines_created'] += 1
                        results['values_assigned'] += len(attribute.value_ids)
                        
                    else:
                        # Update existing line to ensure it has ALL values
                        current_value_ids = set(existing_line.value_ids.ids)
                        all_value_ids = set(attribute.value_ids.ids)
                        
                        if not all_value_ids.issubset(current_value_ids):
                            # Add missing values
                            combined_value_ids = list(current_value_ids.union(all_value_ids))
                            existing_line.write({
                                'value_ids': [(6, 0, combined_value_ids)]
                            })
                            newly_added = len(combined_value_ids) - len(current_value_ids)
                            results['values_assigned'] += newly_added
                        
                except Exception as e:
                    error_msg = f"Error assigning attribute {attribute.name}: {str(e)}"
                    results['errors'].append(error_msg)
                    _logger.error(f"Product {self.name}: {error_msg}")
                    continue
            
            if results['errors']:
                results['success'] = len(results['errors']) < len(selected_attributes)
            
            return results
            
        except Exception as e:
            _logger.error(f"Error in assign_selected_attributes for product {self.name}: {str(e)}")
            return {
                'success': False,
                'attribute_lines_created': 0,
                'values_assigned': 0,
                'errors': [str(e)]
            }

    @api.model
    def bulk_assign_attributes_scheduled(self, category_id=None, attribute_ids=None, category_name=None):
        """
        Scheduled action for bulk attribute assignment
        Can be used as a cron job for large-scale operations
        """
        try:
            # Determine target category
            target_category = None
            
            if category_id:
                target_category = self.env['product.category'].browse(category_id)
                if not target_category.exists():
                    _logger.error(f"Scheduled assignment failed: Category ID {category_id} not found")
                    return False
            elif category_name:
                target_category = self.env['product.category'].search([
                    ('name', '=', category_name)
                ], limit=1)
                if not target_category:
                    _logger.error(f"Scheduled assignment failed: Category '{category_name}' not found")
                    return False
            else:
                _logger.error("Scheduled assignment failed: No category specified")
                return False
            
            if not attribute_ids:
                _logger.error("Scheduled assignment failed: No attributes specified")
                return False
            
            # Get preview to understand the scope
            preview = self.get_assignment_preview(target_category.id, attribute_ids)
            if 'error' in preview:
                _logger.error(f"Preview failed: {preview['error']}")
                return False
            
            if preview['products_without_selected_attributes'] == 0:
                _logger.info(f"All products in category '{target_category.name}' already have the selected attributes - nothing to do")
                return True
            
            _logger.info(f"Starting bulk attribute assignment for {preview['products_without_selected_attributes']} products in category '{target_category.name}'")
            
            # Find products that need attribute assignment
            target_products = self.search([
                ('categ_id', '=', target_category.id),
            ])
            
            success_count = 0
            error_count = 0
            total_lines_created = 0
            total_values_assigned = 0
            
            for product in target_products:
                try:
                    # Check if this product needs assignment
                    existing_attribute_ids = product.attribute_line_ids.mapped('attribute_id.id')
                    if all(attr_id in existing_attribute_ids for attr_id in attribute_ids):
                        continue  # Product already has all selected attributes
                    
                    # Assign attributes to this product
                    result = product.assign_selected_attributes(attribute_ids)
                    
                    if result['success']:
                        success_count += 1
                        total_lines_created += result['attribute_lines_created']
                        total_values_assigned += result['values_assigned']
                    else:
                        error_count += 1
                        _logger.error(f"Failed to assign attributes to product {product.name}: {result['errors']}")
                    
                except Exception as e:
                    _logger.error(f"Error processing product {product.name}: {str(e)}")
                    error_count += 1
                    continue
            
            _logger.info(f"Bulk assignment completed:")
            _logger.info(f"  Successful: {success_count}")
            _logger.info(f"  Errors: {error_count}")
            _logger.info(f"  Attribute lines created: {total_lines_created}")
            _logger.info(f"  Values assigned: {total_values_assigned}")
            
            return True
            
        except Exception as e:
            _logger.error(f"Failed to execute bulk attribute assignment: {str(e)}")
            return False