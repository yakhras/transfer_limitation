# -*- coding: utf-8 -*-

import json
import logging
import time
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)


class RegistryConfigController(http.Controller):
    """
    Controller for registry configuration and template management.
    
    This controller handles:
    - Contact source registry management (Admin only)
    - Filter template operations
    - Registry validation and testing
    - System configuration
    """
    
    # ========================================
    # REGISTRY MANAGEMENT ROUTES (Admin Only)
    # ========================================
    
    @http.route('/mailing/registry/sources', type='json', auth='user', methods=['GET', 'POST'])
    def manage_sources(self, **kwargs):
        """
        Get or create registry sources.
        
        GET: Returns all registry sources for current company
        POST: Creates a new registry source
        
        For GET query parameters:
        - include_inactive (optional): Include inactive sources
        
        For POST expected JSON payload:
        {
            "model_name": "res.partner",
            "display_name": "Contacts",
            "description": "Standard Odoo contacts",
            "email_field": "email",
            "name_field": "name",
            "phone_field": "phone",
            "filter_fields": ["create_date", "category_id", "country_id"]
        }
        
        Returns:
            dict: Registry sources or creation result
        """
        start_time = time.time()
        
        # Check admin permissions
        if not request.env.user.has_group('mailing_list_updater_t.group_mailing_list_updater_manager'):
            return self._error_response(message="Access denied: Manager permissions required", code=403)
        
        try:
            if request.httprequest.method == 'GET':
                return self._get_registry_sources(**kwargs)
            else:  # POST
                return self._create_registry_source(**kwargs)
                
        except Exception as e:
            _logger.error("Registry sources management failed: %s", str(e), exc_info=True)
            return self._error_response(
                message="Registry management failed",
                details=str(e),
                code=500
            )
    
    def _get_registry_sources(self, **kwargs):
        """Get all registry sources."""
        include_inactive = kwargs.get('include_inactive', False)
        
        # Build domain
        domain = [('company_id', 'in', [request.env.company.id, False])]
        if not include_inactive:
            domain.append(('is_active', '=', True))
        
        registry_model = request.env['mailing.source.registry']
        sources = registry_model.search(domain, order='sequence, display_name')
        
        # Format source data
        sources_data = []
        for source in sources:
            source_info = {
                'id': source.id,
                'model_name': source.model_name,
                'display_name': source.display_name,
                'description': source.description,
                'field_mapping': source.get_field_mapping(),
                'filter_fields': source.get_filter_fields(),
                'is_active': source.is_active,
                'sequence': source.sequence,
                'usage_stats': {
                    'usage_count': source.usage_count,
                    'last_used_date': source.last_used_date.isoformat() if source.last_used_date else None,
                },
                'validation': {
                    'model_exists': self._validate_model_exists(source.model_name),
                    'fields_valid': self._validate_source_fields(source),
                    'access_ok': source.validate_model_access(),
                },
                'company_id': source.company_id.id if source.company_id else None,
                'create_date': source.create_date.isoformat() if source.create_date else None,
            }
            sources_data.append(source_info)
        
        return self._success_response(
            data={
                'sources': sources_data,
                'total_count': len(sources_data),
                'active_count': len([s for s in sources_data if s['is_active']]),
                'company_specific': len([s for s in sources_data if s['company_id']]),
            },
            message=f"Retrieved {len(sources_data)} registry sources"
        )
    
    def _create_registry_source(self, **kwargs):
        """Create a new registry source."""
        required_fields = ['model_name', 'display_name', 'email_field', 'name_field']
        
        # Validate required fields
        for field in required_fields:
            if not kwargs.get(field):
                return self._error_response(message=f"Field '{field}' is required")
        
        # Validate model exists
        model_name = kwargs.get('model_name')
        if not self._validate_model_exists(model_name):
            return self._error_response(message=f"Model '{model_name}' does not exist")
        
        try:
            registry_model = request.env['mailing.source.registry']
            
            # Prepare values
            vals = {
                'model_name': model_name,
                'display_name': kwargs.get('display_name'),
                'description': kwargs.get('description', ''),
                'email_field': kwargs.get('email_field'),
                'name_field': kwargs.get('name_field'),
                'phone_field': kwargs.get('phone_field'),
                'company_field': kwargs.get('company_field', 'company_id'),
                'active_field': kwargs.get('active_field', 'active'),
                'filter_fields': json.dumps(kwargs.get('filter_fields', ['create_date'])),
                'sequence': kwargs.get('sequence', 100),
                'is_active': kwargs.get('is_active', True),
                'company_id': kwargs.get('company_id') or request.env.company.id,
            }
            
            # Create registry entry
            source = registry_model.create(vals)
            
            return self._success_response(
                data={
                    'id': source.id,
                    'model_name': source.model_name,
                    'display_name': source.display_name,
                },
                message=f"Registry source '{source.display_name}' created successfully"
            )
            
        except ValidationError as e:
            return self._error_response(message=str(e), code=400)
        except Exception as e:
            return self._error_response(message=f"Creation failed: {str(e)}", code=500)
    
    @http.route('/mailing/registry/sources/<int:source_id>', type='json', auth='user', methods=['GET', 'PUT', 'DELETE'])
    def update_source(self, source_id, **kwargs):
        """
        Get, update, or delete a specific registry source.
        
        GET: Returns detailed source information
        PUT: Updates source configuration
        DELETE: Deactivates source (doesn't actually delete for audit trail)
        
        Returns:
            dict: Source information or operation result
        """
        start_time = time.time()
        
        # Check permissions
        if not request.env.user.has_group('mailing_list_updater_t.group_mailing_list_updater_manager'):
            return self._error_response(message="Access denied: Manager permissions required", code=403)
        
        try:
            registry_model = request.env['mailing.source.registry']
            source = registry_model.browse(source_id)
            
            if not source.exists():
                return self._error_response(message="Registry source not found", code=404)
            
            if request.httprequest.method == 'GET':
                return self._get_source_details(source)
            elif request.httprequest.method == 'PUT':
                return self._update_source_config(source, **kwargs)
            else:  # DELETE
                return self._deactivate_source(source)
                
        except Exception as e:
            _logger.error("Source management failed for ID %s: %s", source_id, str(e), exc_info=True)
            return self._error_response(
                message="Source management failed",
                details=str(e),
                code=500
            )
    
    def _get_source_details(self, source):
        """Get detailed information about a source."""
        return self._success_response(
            data={
                'id': source.id,
                'model_name': source.model_name,
                'display_name': source.display_name,
                'description': source.description,
                'field_mapping': source.get_field_mapping(),
                'filter_fields': source.get_filter_fields(),
                'is_active': source.is_active,
                'sequence': source.sequence,
                'usage_stats': {
                    'usage_count': source.usage_count,
                    'last_used_date': source.last_used_date.isoformat() if source.last_used_date else None,
                },
                'validation': {
                    'model_exists': self._validate_model_exists(source.model_name),
                    'fields_valid': self._validate_source_fields(source),
                    'access_ok': source.validate_model_access(),
                    'sample_count': self._get_sample_contact_count(source),
                },
                'company_id': source.company_id.id if source.company_id else None,
            },
            message="Source details retrieved successfully"
        )
    
    def _update_source_config(self, source, **kwargs):
        """Update source configuration."""
        updatable_fields = [
            'display_name', 'description', 'email_field', 'name_field', 
            'phone_field', 'company_field', 'active_field', 'sequence', 'is_active'
        ]
        
        update_vals = {}
        for field in updatable_fields:
            if field in kwargs:
                if field == 'filter_fields':
                    update_vals[field] = json.dumps(kwargs[field])
                else:
                    update_vals[field] = kwargs[field]
        
        if 'filter_fields' in kwargs:
            update_vals['filter_fields'] = json.dumps(kwargs['filter_fields'])
        
        if update_vals:
            source.write(update_vals)
            
            return self._success_response(
                data={'id': source.id, 'updated_fields': list(update_vals.keys())},
                message="Source updated successfully"
            )
        else:
            return self._success_response(
                message="No changes requested"
            )
    
    def _deactivate_source(self, source):
        """Deactivate a source (soft delete)."""
        if not source.is_active:
            return self._error_response(message="Source is already inactive")
        
        # Check if source is being used in active batches
        batch_model = request.env['mailing.list.update.batch']
        active_batches = batch_model.search([
            ('source_models', 'like', f'"{source.model_name}"'),
            ('state', 'in', ['draft', 'processing']),
        ])
        
        if active_batches:
            return self._error_response(
                message="Cannot deactivate source while it's used in active batches",
                details=f"Found {len(active_batches)} active batches using this source"
            )
        
        source.write({'is_active': False})
        
        return self._success_response(
            data={'id': source.id},
            message="Source deactivated successfully"
        )
    
    @http.route('/mailing/registry/validate', type='json', auth='user', methods=['POST'])
    def validate_registry_config(self, **kwargs):
        """
        Validate registry configuration for a model.
        
        Expected JSON payload:
        {
            "model_name": "res.partner",
            "email_field": "email",
            "name_field": "name",
            "phone_field": "phone",
            "filter_fields": ["create_date", "category_id"]
        }
        
        Returns:
            dict: Validation results with detailed feedback
        """
        try:
            model_name = kwargs.get('model_name')
            if not model_name:
                return self._error_response(message="Model name is required")
            
            validation_results = {
                'model_name': model_name,
                'valid': True,
                'errors': [],
                'warnings': [],
                'field_validations': {},
                'sample_data': {},
            }
            
            # Validate model exists
            if not self._validate_model_exists(model_name):
                validation_results['valid'] = False
                validation_results['errors'].append(f"Model '{model_name}' does not exist")
                return self._success_response(data=validation_results)
            
            try:
                target_model = request.env[model_name]
                model_fields = target_model._fields
                
                # Validate each field
                field_mappings = {
                    'email_field': kwargs.get('email_field'),
                    'name_field': kwargs.get('name_field'),
                    'phone_field': kwargs.get('phone_field'),
                    'company_field': kwargs.get('company_field', 'company_id'),
                    'active_field': kwargs.get('active_field', 'active'),
                }
                
                for field_type, field_name in field_mappings.items():
                    if not field_name:
                        if field_type in ['email_field', 'name_field']:
                            validation_results['valid'] = False
                            validation_results['errors'].append(f"{field_type} is required")
                        continue
                    
                    field_valid = field_name in model_fields
                    validation_results['field_validations'][field_type] = {
                        'field_name': field_name,
                        'exists': field_valid,
                        'type': model_fields[field_name].type if field_valid else None,
                    }
                    
                    if not field_valid:
                        validation_results['valid'] = False
                        validation_results['errors'].append(f"Field '{field_name}' does not exist in model")
                
                # Validate filter fields
                filter_fields = kwargs.get('filter_fields', [])
                valid_filter_fields = []
                for field_name in filter_fields:
                    if field_name in model_fields:
                        valid_filter_fields.append(field_name)
                        validation_results['field_validations'][f'filter_{field_name}'] = {
                            'field_name': field_name,
                            'exists': True,
                            'type': model_fields[field_name].type,
                        }
                    else:
                        validation_results['warnings'].append(f"Filter field '{field_name}' does not exist")
                
                # Get sample data if validation passes
                if validation_results['valid']:
                    try:
                        # Get sample record count
                        domain = []
                        if validation_results['field_validations'].get('company_field', {}).get('exists'):
                            domain.append((kwargs.get('company_field', 'company_id'), '=', request.env.company.id))
                        
                        sample_count = target_model.search_count(domain, limit=1000)
                        validation_results['sample_data']['total_records'] = min(sample_count, 1000)
                        
                        # Get sample with email
                        email_field = kwargs.get('email_field')
                        if email_field:
                            email_domain = domain + [(email_field, '!=', False)]
                            email_count = target_model.search_count(email_domain, limit=1000)
                            validation_results['sample_data']['records_with_email'] = min(email_count, 1000)
                        
                    except Exception as e:
                        validation_results['warnings'].append(f"Could not retrieve sample data: {str(e)}")
                
            except Exception as e:
                validation_results['valid'] = False
                validation_results['errors'].append(f"Model validation failed: {str(e)}")
            
            return self._success_response(
                data=validation_results,
                message="Validation completed"
            )
            
        except Exception as e:
            _logger.error("Registry validation failed: %s", str(e), exc_info=True)
            return self._error_response(
                message="Validation failed",
                details=str(e),
                code=500
            )
    
    # ========================================
    # TEMPLATE MANAGEMENT ROUTES
    # ========================================
    
    @http.route('/mailing/templates', type='json', auth='user', methods=['GET', 'POST'])
    def manage_templates(self, **kwargs):
        """
        Get or create filter templates.
        
        GET: Returns accessible templates for current user
        POST: Creates a new template
        
        Returns:
            dict: Templates list or creation result
        """
        start_time = time.time()
        
        try:
            if request.httprequest.method == 'GET':
                return self._get_filter_templates(**kwargs)
            else:  # POST
                return self._create_filter_template(**kwargs)
                
        except Exception as e:
            _logger.error("Template management failed: %s", str(e), exc_info=True)
            return self._error_response(
                message="Template management failed",
                details=str(e),
                code=500
            )
    
    def _get_filter_templates(self, **kwargs):
        """Get accessible filter templates."""
        template_model = request.env['mailing.filter.template']
        templates_data = template_model.get_accessible_templates(request.env.company.id)
        
        return self._success_response(
            data={
                'templates': templates_data,
                'total_count': len(templates_data),
                'user_templates': len([t for t in templates_data if t['is_owner']]),
                'public_templates': len([t for t in templates_data if t['is_public']]),
            },
            message=f"Retrieved {len(templates_data)} accessible templates"
        )
    
    def _create_filter_template(self, **kwargs):
        """Create a new filter template."""
        required_fields = ['name', 'source_models']
        
        # Validate required fields
        for field in required_fields:
            if not kwargs.get(field):
                return self._error_response(message=f"Field '{field}' is required")
        
        try:
            template_model = request.env['mailing.filter.template']
            
            template = template_model.save_template(
                name=kwargs.get('name'),
                description=kwargs.get('description', ''),
                source_models=kwargs.get('source_models'),
                quick_filters=kwargs.get('quick_filters', {}),
                advanced_filters=kwargs.get('advanced_filters', {}),
                is_public=kwargs.get('is_public', False)
            )
            
            return self._success_response(
                data={
                    'id': template.id,
                    'name': template.name,
                    'is_public': template.is_public,
                },
                message=f"Template '{template.name}' created successfully"
            )
            
        except UserError as e:
            return self._error_response(message=str(e), code=400)
        except Exception as e:
            return self._error_response(message=f"Creation failed: {str(e)}", code=500)
    
    @http.route('/mailing/templates/<int:template_id>', type='json', auth='user', methods=['GET', 'PUT', 'DELETE'])
    def manage_template(self, template_id, **kwargs):
        """
        Get, update, or delete a specific template.
        
        Returns:
            dict: Template information or operation result
        """
        try:
            template_model = request.env['mailing.filter.template']
            template = template_model.browse(template_id)
            
            if not template.exists():
                return self._error_response(message="Template not found", code=404)
            
            if not template.is_accessible:
                return self._error_response(message="Access denied", code=403)
            
            if request.httprequest.method == 'GET':
                template_data = template.load_template()
                return self._success_response(
                    data=template_data,
                    message="Template retrieved successfully"
                )
                
            elif request.httprequest.method == 'PUT':
                template.update_template(**kwargs)
                return self._success_response(
                    data={'id': template.id},
                    message="Template updated successfully"
                )
                
            else:  # DELETE
                if template.user_id != request.env.user:
                    return self._error_response(message="Can only delete your own templates", code=403)
                
                template.unlink()
                return self._success_response(
                    message="Template deleted successfully"
                )
                
        except AccessError as e:
            return self._error_response(message="Access denied", details=str(e), code=403)
        except Exception as e:
            _logger.error("Template management failed for ID %s: %s", template_id, str(e), exc_info=True)
            return self._error_response(
                message="Template management failed",
                details=str(e),
                code=500
            )
    
    # ========================================
    # UTILITY METHODS
    # ========================================
    
    def _validate_model_exists(self, model_name):
        """Validate that a model exists in the system."""
        try:
            request.env[model_name]
            return True
        except KeyError:
            return False
    
    def _validate_source_fields(self, source):
        """Validate that all fields in a source configuration exist."""
        try:
            target_model = request.env[source.model_name]
            model_fields = target_model._fields
            
            field_mapping = source.get_field_mapping()
            filter_fields = source.get_filter_fields()
            
            # Check required fields
            for field_name in [field_mapping['email_field'], field_mapping['name_field']]:
                if field_name not in model_fields:
                    return False
            
            # Check optional fields
            for field_name in [field_mapping['phone_field'], field_mapping['company_field'], field_mapping['active_field']]:
                if field_name and field_name not in model_fields:
                    return False
            
            # Check filter fields
            for field_name in filter_fields:
                if field_name not in model_fields:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _get_sample_contact_count(self, source):
        """Get estimated contact count for a source."""
        try:
            target_model = request.env[source.model_name]
            field_mapping = source.get_field_mapping()
            
            domain = []
            if field_mapping.get('email_field'):
                domain.append((field_mapping['email_field'], '!=', False))
            
            if field_mapping.get('company_field'):
                domain.append((field_mapping['company_field'], '=', request.env.company.id))
            
            return target_model.search_count(domain, limit=10000)
            
        except Exception:
            return 0
    
    def _success_response(self, data=None, message=None, meta=None):
        """Generate standardized success response."""
        response = {
            'success': True,
            'timestamp': fields.Datetime.now().isoformat(),
        }
        
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        if meta:
            response['meta'] = meta
            
        return response
    
    def _error_response(self, message, code=400, details=None):
        """Generate standardized error response."""
        response = {
            'success': False,
            'error': {
                'code': code,
                'message': message,
            },
            'timestamp': fields.Datetime.now().isoformat(),
        }
        
        if details:
            response['error']['details'] = details
            
        return response