# -*- coding: utf-8 -*-

import json
import logging
import time
import random
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)


class MailingListUpdateController(http.Controller):
    """
    Main controller for mailing list update operations.
    
    This controller handles the core functionality including:
    - Mailing list source selection and configuration
    - Filter criteria management
    - Preview generation
    - Batch execution
    - Real-time progress tracking
    """


    @http.route('/mailing/test/domains', type='json', auth='user')
    def test_filter_domains(self, domains, models, test_only=True):
        """Test filter domains - company filtering now handled in frontend"""
        results = []
        total_records = 0
        start_time = time.time()
        
        for model_name, domain in domains.items():
            try:
                model = request.env[model_name]
                
                # Use domain as-is (company filter already included from frontend)
                query_start = time.time()
                count = model.search_count(domain)  # Domain already has company filter
                query_end = time.time()
                query_time = int((query_end - query_start) * 1000)
                
                results.append({
                    'model': model_name,
                    'source_name': self._get_source_name(model_name),
                    'record_count': count,  
                    'domain_conditions': len(domain),
                    'query_time': f"{query_time}ms"
                })
                total_records += count
            
            except Exception as e:
                print(f"Error processing model {model_name}: {str(e)}")
                
        execution_time = int((time.time() - start_time) * 1000)
        
        return {
            'success': True,
            'results': results,
            'total_records': total_records,
            'execution_time': f"{execution_time}ms",
        }
    
    def _add_company_filter(self, domain, model_name, company_id):
        """Add company filter to domain based on model type"""
        
        # Models that have company_id field
        company_models = {
            'res.partner': 'company_id',
            'crm.lead': 'company_id', 
            'crm.opportunity': 'company_id',
            'sale.order': 'company_id',
            'purchase.order': 'company_id',
            'account.move': 'company_id',
            'project.project': 'company_id',
            'hr.employee': 'company_id'
        }
        
        # Check if model has company field
        company_field = company_models.get(model_name)
        
        if company_field:
            # Create new domain with company filter
            company_domain = domain.copy() if domain else []
            
            # Check if company filter already exists
            has_company_filter = any(
                isinstance(condition, list) and 
                len(condition) == 3 and 
                condition[0] == company_field 
                for condition in company_domain
            )
            
            # Add company filter if not already present
            if not has_company_filter:
                company_domain.append([company_field, '=', company_id])
                _logger.info(f"Added company filter to {model_name}: {company_field} = {company_id}")
            
            return company_domain
        else:
            _logger.warning(f"Model {model_name} doesn't have company field, using original domain")
            return domain
    
    def _get_source_name(self, model_name):
        """Get display name for model"""
        source_names = {
            'res.partner': 'Contacts',
            'crm.lead': 'CRM Leads',
            'crm.opportunity': 'Opportunities'
        }
        return source_names.get(model_name, model_name)
    
    # ========================================
    # MAIN FUNCTIONALITY ROUTES
    # ========================================
    
    @http.route('/mailing/update/preview', type='json', auth='user', methods=['POST'])
    def preview_update(self, **kwargs):
        """
        Generate preview of contacts to be added to mailing list.
        
        Expected JSON payload:
        {
            "mailing_list_id": 123,
            "source_mailing_lists": [{"mailing_list_id": 456, "enabled": true}, ...],
            "filter_criteria": {...}
        }
        
        Returns:
            dict: Preview results with statistics and sample contacts
        """
        start_time = time.time()
        
        try:
            # Extract request data
            request_data = self._extract_request_data(kwargs)
            
            # Validate request
            batch_model = request.env['mailing.list.update.batch']
            validation_result = batch_model.validate_web_request(request_data)
            
            if not validation_result['valid']:
                return self._error_response(
                    message="Validation failed",
                    errors=validation_result['errors'],
                    warnings=validation_result.get('warnings', [])
                )
            
            # Create temporary batch for preview
            batch_record = batch_model.create_from_web_request(validation_result['validated_data'])
            
            # Execute preview
            preview_result = batch_record.execute_web_preview()
            
            execution_time = time.time() - start_time
            
            # Log successful preview
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': '/mailing/update/preview',
                    'method': 'POST',
                    'params': request_data,
                    'batch_id': batch_record.batch_id,
                },
                response_data=preview_result,
                execution_time=execution_time,
                success=preview_result.get('success', False)
            )
            
            if preview_result.get('success'):
                return self._success_response(
                    data=preview_result['preview_data'],
                    message="Preview generated successfully",
                    meta={
                        'batch_id': batch_record.batch_id,
                        'execution_time': round(execution_time, 2),
                        'warnings': validation_result.get('warnings', [])
                    }
                )
            else:
                return self._error_response(
                    message="Preview generation failed",
                    details=preview_result.get('error', 'Unknown error')
                )
                
        except ValidationError as e:
            return self._error_response(message=str(e), code=400)
        except AccessError as e:
            return self._error_response(message="Access denied", details=str(e), code=403)
        except Exception as e:
            _logger.error("Preview generation failed: %s", str(e), exc_info=True)
            return self._error_response(
                message="Internal server error",
                details="Please contact system administrator" if not request.env.user.has_group('base.group_system') else str(e),
                code=500
            )
    
    @http.route('/mailing/update/execute', type='json', auth='user', methods=['POST'])
    def execute_update(self, **kwargs):
        """
        Execute the mailing list update operation.
        
        Expected JSON payload:
        {
            "batch_id": "BATCH_20241231_143052",
            "confirmed": true,
            "options": {"send_notification": true, "batch_size": 1000}
        }
        
        Returns:
            dict: Execution results with batch information and WebSocket URL
        """
        start_time = time.time()
        
        try:
            # Extract and validate parameters
            batch_id = kwargs.get('batch_id')
            confirmed = kwargs.get('confirmed', False)
            options = kwargs.get('options', {})
            
            if not batch_id:
                return self._error_response(message="Batch ID is required")
            
            if not confirmed:
                return self._error_response(message="Operation must be confirmed")
            
            # Get batch record
            batch_model = request.env['mailing.list.update.batch']
            batch_record = batch_model.search([('batch_id', '=', batch_id)], limit=1)
            
            if not batch_record:
                return self._error_response(message="Batch not found", code=404)
            
            if batch_record.state != 'draft':
                return self._error_response(message=f"Batch is in '{batch_record.state}' state, cannot execute")
            
            # Parse configuration from batch
            source_configs = json.loads(batch_record.source_models)
            filter_criteria = json.loads(batch_record.filter_criteria) if batch_record.filter_criteria else {}
            
            # Execute the update
            execution_result = batch_record.execute_update(
                source_configs=source_configs,
                filter_criteria=filter_criteria,
                preview_only=False
            )
            
            execution_time = time.time() - start_time
            
            # Log execution attempt
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': '/mailing/update/execute',
                    'method': 'POST',
                    'params': kwargs,
                    'batch_id': batch_id,
                },
                response_data=execution_result,
                execution_time=execution_time,
                success=execution_result.get('success', False)
            )
            
            if execution_result.get('success'):
                return self._success_response(
                    data={
                        'batch_id': batch_id,
                        'status': batch_record.state,
                        'contacts_added': execution_result.get('contacts_added', 0),
                        'websocket_url': f'/ws/mailing/progress/{batch_id}',
                        'progress_url': f'/mailing/update/progress/{batch_id}',
                    },
                    message="Update executed successfully",
                    meta={
                        'execution_time': round(execution_time, 2),
                        'mailing_list': batch_record.mailing_list_id.name,
                    }
                )
            else:
                return self._error_response(
                    message="Execution failed",
                    details=execution_result.get('error', 'Unknown error')
                )
                
        except Exception as e:
            _logger.error("Execution failed for batch %s: %s", kwargs.get('batch_id'), str(e), exc_info=True)
            return self._error_response(
                message="Execution failed",
                details=str(e),
                code=500
            )
    
    @http.route('/mailing/update/sources', type='json', auth='user', methods=['GET'])
    def get_sources(self, **kwargs):
        """
        Get available contact sources from source registry (ORIGINAL FUNCTIONALITY).
        
        Query parameters:
        - company_id (optional): Specific company ID
        - include_stats (optional): Include usage statistics
        
        Returns:
            dict: Available contact sources with metadata
        """
        start_time = time.time()
        
        try:
            company_id = kwargs.get('company_id') or request.env.company.id
            include_stats = kwargs.get('include_stats', True)
            
            # Get sources from registry (ORIGINAL FUNCTIONALITY)
            try:
                registry_model = request.env['mailing.source.registry']
                sources_data = registry_model.get_sources_for_web(company_id=company_id)
            except Exception as registry_error:
                _logger.warning("Source registry not available, using fallback: %s", str(registry_error))
                # Fallback to basic contact sources
                sources_data = {
                    'sources': [
                        {
                            'model_name': 'res.partner',
                            'name': 'Contacts',
                            'description': 'Import contacts from Contacts module',
                            'available': True,
                            'recommended': True,
                            'estimated_count': request.env['res.partner'].search_count([]),
                            'email_field': 'email',
                            'name_field': 'name',
                            'phone_field': 'phone',
                            'company_field': 'company_id'
                        },
                        {
                            'model_name': 'crm.lead',
                            'name': 'CRM Leads',
                            'description': 'Import contacts from CRM Leads',  
                            'available': True,
                            'recommended': True,
                            'estimated_count': request.env['crm.lead'].search_count([]),
                            'email_field': 'email_from',
                            'name_field': 'name',
                            'phone_field': 'phone',
                            'company_field': 'company_id'
                        }
                    ],
                    'summary': {
                        'total_sources': 2,
                        'recommended_count': 2,
                    }
                }
            
            execution_time = time.time() - start_time
            
            return self._success_response(
                data=sources_data,
                message=f"Found {sources_data['summary']['total_sources']} available contact sources",
                meta={
                    'execution_time': round(execution_time, 2),
                    'company_id': company_id,
                }
            )
            
        except Exception as e:
            _logger.error("Failed to get contact sources: %s", str(e), exc_info=True)
            return self._error_response(
                message="Failed to retrieve contact sources",
                details=str(e),
                code=500
            )
    
    @http.route('/mailing/update/mailing-lists', type='json', auth='user', methods=['GET'])
    def get_mailing_lists(self, **kwargs):
        """
        Get available mailing lists for target selection.
        
        Query parameters:
        - search (optional): Search term for mailing list names
        - limit (optional): Maximum results (default: 50)
        - offset (optional): Pagination offset (default: 0)
        
        Returns:
            dict: Available mailing lists for target selection
        """
        start_time = time.time()
        
        try:
            # Extract parameters
            search = kwargs.get('search', '').strip()
            limit = min(kwargs.get('limit', 50), 100)  # Max 100 per request
            offset = kwargs.get('offset', 0)
            
            # Build domain for mailing list search
            domain = []
            
            # Add search term
            if search:
                domain.append(('name', 'ilike', search))
            
            # Execute search
            MailingList = request.env['mailing.list']
            total_count = MailingList.search_count(domain)
            mailing_lists = MailingList.search(domain, limit=limit, offset=offset, order='name asc')
            
            # Format results
            sources_data = []
            for mailing_list in mailing_lists:
                # Get contact count
                contact_count = len(mailing_list.contact_ids)
                
                source_data = {
                    'mailing_list_id': mailing_list.id,
                    'name': mailing_list.name,
                    'description': f'{contact_count} contacts in this mailing list',
                    'contact_count': contact_count,
                    'estimated_count': contact_count,  # For compatibility
                    'available': True,
                    'recommended': contact_count > 50,  # Simple recommendation logic
                    'created_date': mailing_list.create_date.isoformat() if mailing_list.create_date else None,
                    'last_updated': mailing_list.write_date.isoformat() if mailing_list.write_date else None,
                    'is_public': getattr(mailing_list, 'is_public', True),
                }
                sources_data.append(source_data)
            
            # Prepare response
            response_data = {
                'sources': sources_data,
                'summary': {
                    'total_sources': len(sources_data),
                    'total_available': total_count,
                    'recommended_count': len([s for s in sources_data if s['recommended']]),
                    'has_more': (offset + limit) < total_count,
                },
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'total': total_count,
                }
            }
            
            execution_time = time.time() - start_time
            
            return self._success_response(
                data=response_data,
                message=f"Found {total_count} mailing lists",
                meta={
                    'execution_time': round(execution_time, 2),
                    'search_term': search,
                }
            )
            
        except Exception as e:
            _logger.error("Failed to get mailing lists: %s", str(e), exc_info=True)
            return self._error_response(
                message="Failed to retrieve mailing lists",
                details=str(e),
                code=500
            )
    
    @http.route('/mailing/update/filters/<string:mailing_list_id>', type='json', auth='user', methods=['GET'])
    def get_mailing_list_filters(self, mailing_list_id, **kwargs):
        """
        Get available filter options for contacts within a specific mailing list.
        
        Parameters:
        - mailing_list_id: The mailing list ID
        
        Query parameters:
        - include_samples (optional): Include sample data for relation fields
        
        Returns:
            dict: Available filter fields and options for mailing list contacts
        """
        start_time = time.time()
        
        try:
            include_samples = kwargs.get('include_samples', False)
            
            # Get mailing list
            try:
                mailing_list_id = int(mailing_list_id)
            except (ValueError, TypeError):
                return self._error_response(
                    message="Invalid mailing list ID format",
                    code=400
                )
            
            mailing_list = request.env['mailing.list'].browse(mailing_list_id)
            
            if not mailing_list.exists():
                return self._error_response(
                    message=f"Mailing list with ID {mailing_list_id} not found",
                    code=404
                )
            
            # Check access permissions
            try:
                mailing_list.check_access_rights('read')
                mailing_list.check_access_rule('read')
            except AccessError:
                return self._error_response(
                    message="Access denied to mailing list",
                    code=403
                )
            
            # Get filter options for mailing list contacts (mailing.contact model)
            filter_options = self._get_mailing_contact_filter_options(
                mailing_list=mailing_list,
                include_sample_data=include_samples
            )
            
            execution_time = time.time() - start_time
            
            # Log request
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': f'/mailing/update/filters/{mailing_list_id}',
                    'method': 'GET',
                    'params': kwargs,
                },
                response_data=filter_options,
                execution_time=execution_time,
                success=True
            )
            
            return self._success_response(
                data=filter_options,
                message=f"Filter options retrieved for {mailing_list.name}",
                meta={
                    'execution_time': round(execution_time, 2),
                    'field_count': filter_options.get('field_count', 0),
                    'mailing_list_name': mailing_list.name,
                }
            )
            
        except Exception as e:
            _logger.error("Failed to get filters for mailing list %s: %s", mailing_list_id, str(e), exc_info=True)
            return self._error_response(
                message=f"Failed to retrieve filters for mailing list",
                details=str(e),
                code=500
            )
    
    @http.route('/mailing/update/validate-filters', type='json', auth='user', methods=['POST'])
    def validate_filters(self, **kwargs):
        """
        Validate filter criteria for specific mailing lists.
        
        Expected JSON payload:
        {
            "filters": {
                "mailing_list_123": {"create_date": {"operator": ">=", "value": "2024-01-01"}},
                "mailing_list_456": {"opt_out": {"operator": "=", "value": false}}
            }
        }
        
        Returns:
            dict: Validation results for each mailing list
        """
        start_time = time.time()
        
        try:
            filters = kwargs.get('filters', {})
            
            if not filters:
                return self._error_response(message="No filters provided for validation")
            
            validation_results = {}
            overall_valid = True
            
            for mailing_list_key, filter_criteria in filters.items():
                # Extract mailing list ID from key (format: "mailing_list_123")
                try:
                    mailing_list_id = int(mailing_list_key.replace('mailing_list_', ''))
                except (ValueError, AttributeError):
                    validation_results[mailing_list_key] = {
                        'valid': False,
                        'errors': [f"Invalid mailing list identifier: {mailing_list_key}"]
                    }
                    overall_valid = False
                    continue
                
                # Validate filters for this mailing list
                validation_result = self._validate_mailing_list_filter_criteria(
                    mailing_list_id, filter_criteria
                )
                validation_results[mailing_list_key] = validation_result
                
                if not validation_result.get('valid'):
                    overall_valid = False
            
            execution_time = time.time() - start_time
            
            # Log validation request
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': '/mailing/update/validate-filters',
                    'method': 'POST',
                    'params': kwargs,
                },
                response_data=validation_results,
                execution_time=execution_time,
                success=overall_valid
            )
            
            return self._success_response(
                data={
                    'validation_results': validation_results,
                    'overall_valid': overall_valid,
                    'mailing_lists_validated': len(validation_results),
                },
                message="Filter validation completed",
                meta={
                    'execution_time': round(execution_time, 2),
                }
            )
            
        except Exception as e:
            _logger.error("Filter validation failed: %s", str(e), exc_info=True)
            return self._error_response(
                message="Filter validation failed",
                details=str(e),
                code=500
            )
    
    # ========================================
    # PROGRESS TRACKING ROUTES
    # ========================================
    
    @http.route('/mailing/update/progress/<string:batch_id>', type='json', auth='user', methods=['GET'])
    def get_progress(self, batch_id, **kwargs):
        """
        Get current progress status for a batch operation.
        
        Parameters:
        - batch_id: The batch identifier
        
        Returns:
            dict: Current progress information
        """
        try:
            # Get batch record
            batch_model = request.env['mailing.list.update.batch']
            batch_record = batch_model.search([('batch_id', '=', batch_id)], limit=1)
            
            if not batch_record:
                return self._error_response(message="Batch not found", code=404)
            
            # Check access permissions
            if batch_record.user_id != request.env.user and not request.env.user.has_group('mass_mailing.group_mass_mailing_manager'):
                return self._error_response(message="Access denied", code=403)
            
            # Get progress status
            progress_data = batch_record.get_progress_status()
            
            return self._success_response(
                data=progress_data,
                message="Progress retrieved successfully"
            )
            
        except Exception as e:
            _logger.error("Failed to get progress for batch %s: %s", batch_id, str(e))
            return self._error_response(
                message="Failed to retrieve progress",
                details=str(e),
                code=500
            )
    
    # ========================================
    # HELPER METHODS FOR MAILING LIST OPERATIONS
    # ========================================
    
    def _get_mailing_lists_for_sources(self, company_id, target_mailing_list_id=None, include_stats=True):
        """
        Get available mailing lists that can be used as sources.
        
        Returns:
            dict: Formatted data structure compatible with frontend
        """
        # Build domain
        domain = [
            ('company_id', '=', company_id),
            ('is_public', '=', True),  # Only public/active lists
        ]
        
        # Exclude target list
        if target_mailing_list_id:
            domain.append(('id', '!=', target_mailing_list_id))
        
        # Get mailing lists
        MailingList = request.env['mailing.list']
        mailing_lists = MailingList.search(domain, order='name asc')
        
        sources = []
        for mailing_list in mailing_lists:
            contact_count = len(mailing_list.contact_ids)
            
            source_data = {
                'mailing_list_id': mailing_list.id,
                'model_name': f'mailing.list.{mailing_list.id}',  # For compatibility
                'name': mailing_list.name,
                'description': self._get_mailing_list_description(mailing_list),
                'available': True,
                'recommended': self._is_mailing_list_recommended(mailing_list, contact_count),
                'estimated_count': contact_count,
                'contact_count': contact_count,
                'email_field': 'email',
                'name_field': 'name',
                'phone_field': 'mobile',
                'company_field': 'company_name',
                'created_date': mailing_list.create_date.isoformat() if mailing_list.create_date else None,
                'is_public': mailing_list.is_public,
            }
            
            if include_stats:
                source_data.update(self._get_mailing_list_stats(mailing_list))
            
            sources.append(source_data)
        
        return {
            'sources': sources,
            'summary': {
                'total_sources': len(sources),
                'recommended_count': len([s for s in sources if s['recommended']]),
                'total_contacts': sum(s['contact_count'] for s in sources),
            }
        }
    
    def _get_mailing_list_description(self, mailing_list):
        """Generate description for mailing list."""
        contact_count = len(mailing_list.contact_ids)
        
        if contact_count == 0:
            return "Empty mailing list - no contacts"
        elif contact_count == 1:
            return "1 contact in this mailing list"
        else:
            return f"{contact_count} contacts in this mailing list"
    
    def _is_mailing_list_recommended(self, mailing_list, contact_count):
        """Determine if a mailing list should be marked as recommended."""
        # Recommend lists with good contact count and recent activity
        if contact_count < 10:
            return False
        
        # Check for recent mailing activity
        recent_mailings = request.env['mailing.mailing'].search_count([
            ('contact_list_ids', 'in', mailing_list.id),
            ('create_date', '>=', fields.Datetime.now() - fields.timedelta(days=90))
        ])
        
        return recent_mailings > 0 or contact_count > 100
    
    def _get_mailing_list_stats(self, mailing_list):
        """Get additional statistics for mailing list."""
        stats = {}
        
        # Last mailing sent
        last_mailing = request.env['mailing.mailing'].search([
            ('contact_list_ids', 'in', mailing_list.id)
        ], limit=1, order='create_date desc')
        
        if last_mailing:
            stats['last_mailing_date'] = last_mailing.create_date.isoformat()
            stats['last_mailing_subject'] = last_mailing.subject
        
        # Opt-out statistics
        opt_out_count = request.env['mailing.contact'].search_count([
            ('list_ids', 'in', mailing_list.id),
            ('opt_out', '=', True)
        ])
        stats['opt_out_count'] = opt_out_count
        stats['active_contact_count'] = len(mailing_list.contact_ids) - opt_out_count
        
        return stats
    
    def _get_mailing_contact_filter_options(self, mailing_list, include_sample_data=False):
        """
        Get filter options for mailing list contacts.
        
        Returns available fields that can be used for filtering contacts
        within the specified mailing list.
        """
        MailingContact = request.env['mailing.contact']
        
        # Define available filter fields for mailing contacts
        filter_fields = {
            'name': {
                'type': 'char',
                'string': 'Contact Name',
                'operators': ['=', '!=', 'ilike', 'not ilike', 'in', 'not in'],
            },
            'email': {
                'type': 'char',
                'string': 'Email Address',
                'operators': ['=', '!=', 'ilike', 'not ilike', 'in', 'not in'],
            },
            'mobile': {
                'type': 'char',
                'string': 'Mobile Phone',
                'operators': ['=', '!=', 'ilike', 'not ilike'],
            },
            'company_name': {
                'type': 'char',
                'string': 'Company Name',
                'operators': ['=', '!=', 'ilike', 'not ilike', 'in', 'not in'],
            },
            'country_id': {
                'type': 'many2one',
                'string': 'Country',
                'operators': ['=', '!=', 'in', 'not in'],
                'relation': 'res.country',
            },
            'title_id': {
                'type': 'many2one',
                'string': 'Title',
                'operators': ['=', '!=', 'in', 'not in'],
                'relation': 'res.partner.title',
            },
            'opt_out': {
                'type': 'boolean',
                'string': 'Opted Out',
                'operators': ['=', '!='],
            },
            'create_date': {
                'type': 'datetime',
                'string': 'Created Date',
                'operators': ['=', '!=', '<', '<=', '>', '>=', 'between'],
            },
            'write_date': {
                'type': 'datetime',
                'string': 'Last Updated',
                'operators': ['=', '!=', '<', '<=', '>', '>=', 'between'],
            },
        }
        
        # Add sample data if requested
        if include_sample_data:
            contacts = MailingContact.search([
                ('list_ids', 'in', mailing_list.id)
            ], limit=10)
            
            # Add sample values for relation fields
            if contacts:
                countries = contacts.mapped('country_id')
                if countries:
                    filter_fields['country_id']['sample_values'] = [
                        {'id': c.id, 'name': c.name} for c in countries[:5]
                    ]
                
                titles = contacts.mapped('title_id')
                if titles:
                    filter_fields['title_id']['sample_values'] = [
                        {'id': t.id, 'name': t.name} for t in titles[:5]
                    ]
        
        return {
            'model_name': 'mailing.contact',
            'display_name': f'Contacts from {mailing_list.name}',
            'fields': filter_fields,
            'field_count': len(filter_fields),
            'mailing_list_id': mailing_list.id,
            'mailing_list_name': mailing_list.name,
        }
    
    def _validate_mailing_list_filter_criteria(self, mailing_list_id, filter_criteria):
        """
        Validate filter criteria for a specific mailing list.
        
        Returns:
            dict: Validation result with valid flag and any errors
        """
        try:
            # Get mailing list
            mailing_list = request.env['mailing.list'].browse(mailing_list_id)
            if not mailing_list.exists():
                return {
                    'valid': False,
                    'errors': [f'Mailing list with ID {mailing_list_id} not found']
                }
            
            # Get available fields
            filter_options = self._get_mailing_contact_filter_options(mailing_list, False)
            available_fields = filter_options['fields']
            
            errors = []
            warnings = []
            
            # Validate each filter criterion
            for field_name, criterion in filter_criteria.items():
                if field_name not in available_fields:
                    errors.append(f"Field '{field_name}' is not available for filtering")
                    continue
                
                field_info = available_fields[field_name]
                operator = criterion.get('operator')
                value = criterion.get('value')
                
                # Validate operator
                if operator not in field_info['operators']:
                    errors.append(f"Operator '{operator}' is not valid for field '{field_name}'")
                
                # Validate value type based on field type
                if field_info['type'] == 'boolean' and not isinstance(value, bool):
                    errors.append(f"Field '{field_name}' requires a boolean value")
                elif field_info['type'] in ['datetime', 'date'] and not isinstance(value, str):
                    errors.append(f"Field '{field_name}' requires a date/datetime string")
                
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'validated_fields': len(filter_criteria),
            }
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f'Validation error: {str(e)}']
            }
    
    # ========================================
    # UTILITY METHODS
    # ========================================
    
    def _extract_request_data(self, kwargs):
        """Extract and normalize request data."""
        return {
            'mailing_list_id': kwargs.get('mailing_list_id'),
            'source_mailing_lists': kwargs.get('source_mailing_lists', []),  # Changed from source_models
            'filter_criteria': kwargs.get('filter_criteria', {}),
            'batch_config': kwargs.get('batch_config', {}),
        }
    
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
    
    def _error_response(self, message, code=400, details=None, errors=None, warnings=None):
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
        if errors:
            response['error']['errors'] = errors
        if warnings:
            response['error']['warnings'] = warnings
            
        return response