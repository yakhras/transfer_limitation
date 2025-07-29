# -*- coding: utf-8 -*-

import json
import logging
import time
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)


class MailingListUpdateController(http.Controller):
    """
    Main controller for mailing list update operations.
    
    This controller handles the core functionality including:
    - Contact source selection and configuration
    - Filter criteria management
    - Preview generation
    - Batch execution
    - Real-time progress tracking
    """
    
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
            "source_models": [{"model_name": "res.partner", "enabled": true}, ...],
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
        Get available contact sources for the current company.
        
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
            
            # Get sources from registry
            registry_model = request.env['mailing.source.registry']
            sources_data = registry_model.get_sources_for_web(company_id=company_id)
            
            execution_time = time.time() - start_time
            
            # Log request
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': '/mailing/update/sources',
                    'method': 'GET',
                    'params': kwargs,
                },
                response_data=sources_data,
                execution_time=execution_time,
                success=True
            )
            
            return self._success_response(
                data=sources_data,
                message=f"Found {sources_data['summary']['total_sources']} available sources",
                meta={
                    'execution_time': round(execution_time, 2),
                    'company_id': company_id,
                }
            )
            
        except Exception as e:
            _logger.error("Failed to get sources: %s", str(e), exc_info=True)
            return self._error_response(
                message="Failed to retrieve sources",
                details=str(e),
                code=500
            )
    
    @http.route('/mailing/update/filters/<string:model_name>', type='json', auth='user', methods=['GET'])
    def get_model_filters(self, model_name, **kwargs):
        """
        Get available filter options for a specific source model.
        
        Parameters:
        - model_name: The source model name (e.g., 'res.partner', 'crm.lead')
        
        Query parameters:
        - include_samples (optional): Include sample data for relation fields
        
        Returns:
            dict: Available filter fields and options for the model
        """
        start_time = time.time()
        
        try:
            include_samples = kwargs.get('include_samples', False)
            
            # Get registry entry for the model
            registry_model = request.env['mailing.source.registry']
            registry_entry = registry_model.search([
                ('model_name', '=', model_name),
                ('is_active', '=', True),
                ('company_id', 'in', [request.env.company.id, False])
            ], limit=1)
            
            if not registry_entry:
                return self._error_response(
                    message=f"Model '{model_name}' is not registered or inactive",
                    code=404
                )
            
            # Get filter options
            filter_options = registry_entry.get_filter_options_json(include_sample_data=include_samples)
            
            if 'error' in filter_options:
                return self._error_response(
                    message="Failed to get filter options",
                    details=filter_options['error']
                )
            
            execution_time = time.time() - start_time
            
            # Log request
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': f'/mailing/update/filters/{model_name}',
                    'method': 'GET',
                    'params': kwargs,
                },
                response_data=filter_options,
                execution_time=execution_time,
                success=True
            )
            
            return self._success_response(
                data=filter_options,
                message=f"Filter options retrieved for {filter_options.get('display_name', model_name)}",
                meta={
                    'execution_time': round(execution_time, 2),
                    'field_count': filter_options.get('field_count', 0),
                }
            )
            
        except Exception as e:
            _logger.error("Failed to get filters for model %s: %s", model_name, str(e), exc_info=True)
            return self._error_response(
                message=f"Failed to retrieve filters for model '{model_name}'",
                details=str(e),
                code=500
            )
    
    @http.route('/mailing/update/validate-filters', type='json', auth='user', methods=['POST'])
    def validate_filters(self, **kwargs):
        """
        Validate filter criteria for specific models.
        
        Expected JSON payload:
        {
            "filters": {
                "res.partner": {"create_date": {"operator": ">=", "value": "2024-01-01"}},
                "crm.lead": {"probability": {"operator": ">=", "value": 75}}
            }
        }
        
        Returns:
            dict: Validation results for each model
        """
        start_time = time.time()
        
        try:
            filters = kwargs.get('filters', {})
            
            if not filters:
                return self._error_response(message="No filters provided for validation")
            
            registry_model = request.env['mailing.source.registry']
            validation_results = {}
            overall_valid = True
            
            for model_name, filter_criteria in filters.items():
                validation_result = registry_model.validate_filter_criteria(model_name, filter_criteria)
                validation_results[model_name] = validation_result
                
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
                    'models_validated': len(validation_results),
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
    # UTILITY METHODS
    # ========================================
    
    def _extract_request_data(self, kwargs):
        """Extract and normalize request data."""
        return {
            'mailing_list_id': kwargs.get('mailing_list_id'),
            'source_models': kwargs.get('source_models', []),
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