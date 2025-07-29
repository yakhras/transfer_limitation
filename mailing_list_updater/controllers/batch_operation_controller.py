# -*- coding: utf-8 -*-

import json
import logging
import time
from datetime import datetime, timedelta
from odoo import http, fields, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)


class BatchOperationController(http.Controller):
    """
    Controller for batch operation management.
    
    This controller handles:
    - Batch operation history and details
    - Batch rollback operations
    - Contact tracking and management
    - Statistics and reporting
    """
    
    # ========================================
    # BATCH MANAGEMENT ROUTES
    # ========================================
    
    @http.route('/mailing/batch/history', type='json', auth='user', methods=['GET'])
    def get_batch_history(self, **kwargs):
        """
        Get batch operation history for the current user/company.
        
        Query parameters:
        - limit (optional): Number of records to return (default: 50)
        - offset (optional): Pagination offset (default: 0)
        - mailing_list_id (optional): Filter by specific mailing list
        - state (optional): Filter by batch state
        - date_from (optional): Start date filter
        - date_to (optional): End date filter
        - user_only (optional): Show only current user's batches
        
        Returns:
            dict: Batch history with pagination info
        """
        start_time = time.time()
        
        try:
            # Extract query parameters
            limit = min(kwargs.get('limit', 50), 200)  # Max 200 records
            offset = max(kwargs.get('offset', 0), 0)
            mailing_list_id = kwargs.get('mailing_list_id')
            state = kwargs.get('state')
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            user_only = kwargs.get('user_only', False)
            
            # Build domain
            domain = [('company_id', '=', request.env.company.id)]
            
            if mailing_list_id:
                domain.append(('mailing_list_id', '=', int(mailing_list_id)))
            
            if state:
                domain.append(('state', '=', state))
            
            if date_from:
                try:
                    date_from_dt = fields.Datetime.from_string(date_from)
                    domain.append(('create_date', '>=', date_from_dt))
                except (ValueError, TypeError):
                    return self._error_response(message="Invalid date_from format")
            
            if date_to:
                try:
                    date_to_dt = fields.Datetime.from_string(date_to)
                    domain.append(('create_date', '<=', date_to_dt))
                except (ValueError, TypeError):
                    return self._error_response(message="Invalid date_to format")
            
            if user_only or not request.env.user.has_group('mass_mailing.group_mass_mailing_manager'):
                domain.append(('user_id', '=', request.env.user.id))
            
            # Get batch records
            batch_model = request.env['mailing.list.update.batch']
            total_count = batch_model.search_count(domain)
            batches = batch_model.search(domain, limit=limit, offset=offset, order='create_date desc')
            
            # Format batch data
            batch_data = []
            for batch in batches:
                batch_info = batch.to_json_preview()
                batch_info['can_rollback'] = batch.can_rollback
                batch_info['tracking_count'] = len(batch.tracking_ids)
                batch_data.append(batch_info)
            
            execution_time = time.time() - start_time
            
            # Log request
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': '/mailing/batch/history',
                    'method': 'GET',
                    'params': kwargs,
                },
                response_data={'count': len(batch_data)},
                execution_time=execution_time,
                success=True
            )
            
            return self._success_response(
                data={
                    'batches': batch_data,
                    'pagination': {
                        'total_count': total_count,
                        'limit': limit,
                        'offset': offset,
                        'has_more': (offset + limit) < total_count,
                    }
                },
                message=f"Retrieved {len(batch_data)} batch records",
                meta={
                    'execution_time': round(execution_time, 2),
                    'filters_applied': len([k for k, v in kwargs.items() if v and k != 'limit' and k != 'offset']),
                }
            )
            
        except Exception as e:
            _logger.error("Failed to get batch history: %s", str(e), exc_info=True)
            return self._error_response(
                message="Failed to retrieve batch history",
                details=str(e),
                code=500
            )
    
    @http.route('/mailing/batch/<string:batch_id>', type='json', auth='user', methods=['GET'])
    def get_batch_details(self, batch_id, **kwargs):
        """
        Get detailed information about a specific batch.
        
        Parameters:
        - batch_id: The batch identifier
        
        Query parameters:
        - include_contacts (optional): Include sample contacts (default: true)
        - include_audit (optional): Include audit trail (default: false)
        
        Returns:
            dict: Detailed batch information
        """
        start_time = time.time()
        
        try:
            include_contacts = kwargs.get('include_contacts', True)
            include_audit = kwargs.get('include_audit', False)
            
            # Get batch record
            batch_model = request.env['mailing.list.update.batch']
            batch_record = batch_model.search([('batch_id', '=', batch_id)], limit=1)
            
            if not batch_record:
                return self._error_response(message="Batch not found", code=404)
            
            # Check access permissions
            if (batch_record.user_id != request.env.user and 
                not request.env.user.has_group('mass_mailing.group_mass_mailing_manager')):
                return self._error_response(message="Access denied", code=403)
            
            # Get detailed batch information
            batch_details = batch_record.get_batch_statistics()
            
            # Add contacts if requested
            if include_contacts:
                tracking_model = request.env['mailing.contact.tracking']
                contacts = tracking_model.get_batch_contacts(batch_id, request.env.company.id)
                batch_details['contacts'] = contacts[:50]  # Limit for performance
                batch_details['total_contacts'] = len(contacts)
            
            # Add audit trail if requested
            if include_audit:
                audit_model = request.env['mailing.operation.audit']
                audit_trail = audit_model.get_audit_trail(batch_id=batch_id, limit=20)
                batch_details['audit_trail'] = audit_trail
            
            execution_time = time.time() - start_time
            
            # Log request
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': f'/mailing/batch/{batch_id}',
                    'method': 'GET',
                    'params': kwargs,
                    'batch_id': batch_id,
                },
                response_data=batch_details,
                execution_time=execution_time,
                success=True
            )
            
            return self._success_response(
                data=batch_details,
                message="Batch details retrieved successfully",
                meta={
                    'execution_time': round(execution_time, 2),
                    'includes': {
                        'contacts': include_contacts,
                        'audit': include_audit,
                    }
                }
            )
            
        except Exception as e:
            _logger.error("Failed to get batch details for %s: %s", batch_id, str(e), exc_info=True)
            return self._error_response(
                message="Failed to retrieve batch details",
                details=str(e),
                code=500
            )
    
    @http.route('/mailing/batch/<string:batch_id>/rollback', type='json', auth='user', methods=['POST'])
    def rollback_batch(self, batch_id, **kwargs):
        """
        Rollback a specific batch operation.
        
        Parameters:
        - batch_id: The batch identifier
        
        Expected JSON payload:
        {
            "reason": "User requested rollback due to incorrect filters",
            "confirmed": true
        }
        
        Returns:
            dict: Rollback operation results
        """
        start_time = time.time()
        
        try:
            reason = kwargs.get('reason', 'Web interface rollback')
            confirmed = kwargs.get('confirmed', False)
            
            if not confirmed:
                return self._error_response(message="Rollback must be confirmed")
            
            # Get batch record
            batch_model = request.env['mailing.list.update.batch']
            batch_record = batch_model.search([('batch_id', '=', batch_id)], limit=1)
            
            if not batch_record:
                return self._error_response(message="Batch not found", code=404)
            
            # Check rollback permissions
            if (batch_record.user_id != request.env.user and 
                not request.env.user.has_group('mass_mailing.group_mass_mailing_manager')):
                return self._error_response(message="Access denied", code=403)
            
            if not batch_record.can_rollback:
                return self._error_response(
                    message="Batch cannot be rolled back",
                    details="Rollback window expired or batch already rolled back"
                )
            
            # Execute rollback
            rollback_result = batch_record.rollback_operation(reason=reason)
            
            execution_time = time.time() - start_time
            
            # Log rollback request
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': f'/mailing/batch/{batch_id}/rollback',
                    'method': 'POST',
                    'params': kwargs,
                    'batch_id': batch_id,
                },
                response_data=rollback_result,
                execution_time=execution_time,
                success=rollback_result.get('success', False)
            )
            
            if rollback_result.get('success'):
                return self._success_response(
                    data={
                        'batch_id': batch_id,
                        'contacts_removed': rollback_result.get('contacts_removed', 0),
                        'rollback_date': fields.Datetime.now().isoformat(),
                        'reason': reason,
                    },
                    message="Batch rolled back successfully",
                    meta={
                        'execution_time': round(execution_time, 2),
                    }
                )
            else:
                return self._error_response(
                    message="Rollback failed",
                    details=rollback_result.get('error', 'Unknown error')
                )
                
        except Exception as e:
            _logger.error("Rollback failed for batch %s: %s", batch_id, str(e), exc_info=True)
            return self._error_response(
                message="Rollback operation failed",
                details=str(e),
                code=500
            )
    
    @http.route('/mailing/batch/<string:batch_id>/contacts', type='json', auth='user', methods=['GET'])
    def get_batch_contacts(self, batch_id, **kwargs):
        """
        Get contacts added by a specific batch.
        
        Parameters:
        - batch_id: The batch identifier
        
        Query parameters:
        - limit (optional): Number of contacts to return (default: 100)
        - offset (optional): Pagination offset (default: 0)
        - source_model (optional): Filter by source model
        
        Returns:
            dict: Contacts added by the batch with pagination
        """
        start_time = time.time()
        
        try:
            limit = min(kwargs.get('limit', 100), 500)  # Max 500 contacts
            offset = max(kwargs.get('offset', 0), 0)
            source_model = kwargs.get('source_model')
            
            # Get batch record for permission check
            batch_model = request.env['mailing.list.update.batch']
            batch_record = batch_model.search([('batch_id', '=', batch_id)], limit=1)
            
            if not batch_record:
                return self._error_response(message="Batch not found", code=404)
            
            # Check access permissions
            if (batch_record.user_id != request.env.user and 
                not request.env.user.has_group('mass_mailing.group_mass_mailing_manager')):
                return self._error_response(message="Access denied", code=403)
            
            # Get tracking records
            tracking_model = request.env['mailing.contact.tracking']
            domain = [
                ('batch_id', '=', batch_id),
                ('company_id', '=', request.env.company.id)
            ]
            
            if source_model:
                domain.append(('source_model', '=', source_model))
            
            total_count = tracking_model.search_count(domain)
            tracking_records = tracking_model.search(domain, limit=limit, offset=offset, order='create_date desc')
            
            # Format contact data
            contacts_data = []
            for tracking in tracking_records:
                contact_info = {
                    'id': tracking.id,
                    'email': tracking.original_email,
                    'name': tracking.original_name,
                    'phone': tracking.original_phone,
                    'source_model': tracking.source_model,
                    'source_record_id': tracking.source_record_id,
                    'create_date': tracking.create_date.isoformat() if tracking.create_date else None,
                    'mailing_contact_active': not tracking.mailing_contact_id.opt_out if tracking.mailing_contact_id else False,
                }
                contacts_data.append(contact_info)
            
            execution_time = time.time() - start_time
            
            # Log request
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': f'/mailing/batch/{batch_id}/contacts',
                    'method': 'GET',
                    'params': kwargs,
                    'batch_id': batch_id,
                },
                response_data={'count': len(contacts_data)},
                execution_time=execution_time,
                success=True
            )
            
            return self._success_response(
                data={
                    'contacts': contacts_data,
                    'pagination': {
                        'total_count': total_count,
                        'limit': limit,
                        'offset': offset,
                        'has_more': (offset + limit) < total_count,
                    },
                    'batch_info': {
                        'batch_id': batch_id,
                        'batch_display_name': batch_record.batch_display_name,
                        'state': batch_record.state,
                    }
                },
                message=f"Retrieved {len(contacts_data)} contacts for batch",
                meta={
                    'execution_time': round(execution_time, 2),
                }
            )
            
        except Exception as e:
            _logger.error("Failed to get batch contacts for %s: %s", batch_id, str(e), exc_info=True)
            return self._error_response(
                message="Failed to retrieve batch contacts",
                details=str(e),
                code=500
            )
    
    # ========================================
    # STATISTICS AND REPORTING ROUTES
    # ========================================
    
    @http.route('/mailing/batch/statistics', type='json', auth='user', methods=['GET'])
    def get_batch_statistics(self, **kwargs):
        """
        Get comprehensive batch operation statistics.
        
        Query parameters:
        - date_from (optional): Start date for statistics
        - date_to (optional): End date for statistics
        - group_by (optional): Grouping period ('day', 'week', 'month')
        - include_performance (optional): Include performance analysis
        
        Returns:
            dict: Comprehensive statistics and analytics
        """
        start_time = time.time()
        
        try:
            # Parse parameters
            date_from = kwargs.get('date_from')
            date_to = kwargs.get('date_to')
            group_by = kwargs.get('group_by', 'day')
            include_performance = kwargs.get('include_performance', True)
            
            # Convert date strings to datetime objects
            date_from_dt = None
            date_to_dt = None
            
            if date_from:
                try:
                    date_from_dt = fields.Datetime.from_string(date_from)
                except (ValueError, TypeError):
                    return self._error_response(message="Invalid date_from format")
            
            if date_to:
                try:
                    date_to_dt = fields.Datetime.from_string(date_to)
                except (ValueError, TypeError):
                    return self._error_response(message="Invalid date_to format")
            
            # Default to last 30 days if no dates provided
            if not date_from_dt:
                date_from_dt = fields.Datetime.now() - timedelta(days=30)
            if not date_to_dt:
                date_to_dt = fields.Datetime.now()
            
            # Get batch statistics
            batch_model = request.env['mailing.list.update.batch']
            domain = [
                ('company_id', '=', request.env.company.id),
                ('create_date', '>=', date_from_dt),
                ('create_date', '<=', date_to_dt),
            ]
            
            # Apply user filter if not manager
            if not request.env.user.has_group('mass_mailing.group_mass_mailing_manager'):
                domain.append(('user_id', '=', request.env.user.id))
            
            batches = batch_model.search(domain)
            
            # Calculate basic statistics
            total_batches = len(batches)
            completed_batches = len(batches.filtered(lambda b: b.state == 'completed'))
            failed_batches = len(batches.filtered(lambda b: b.state == 'failed'))
            rolled_back_batches = len(batches.filtered(lambda b: b.is_rolled_back))
            
            total_contacts_added = sum(batch.contacts_added for batch in batches)
            total_contacts_found = sum(batch.contacts_found for batch in batches)
            total_execution_time = sum(batch.execution_time for batch in batches)
            
            # Group statistics by time period
            grouped_stats = self._group_batches_by_period(batches, group_by)
            
            # Performance analysis
            performance_stats = {}
            if include_performance:
                processor_model = request.env['mailing.batch.processor']
                performance_stats = processor_model.analyze_batch_performance(
                    date_from=date_from_dt,
                    date_to=date_to_dt
                )
            
            # Audit statistics
            audit_model = request.env['mailing.operation.audit']
            audit_stats = audit_model.get_performance_stats(
                date_from=date_from_dt,
                date_to=date_to_dt,
                group_by=group_by
            )
            
            statistics_data = {
                'summary': {
                    'total_batches': total_batches,
                    'completed_batches': completed_batches,
                    'failed_batches': failed_batches,
                    'rolled_back_batches': rolled_back_batches,
                    'success_rate': completed_batches / max(total_batches, 1),
                    'rollback_rate': rolled_back_batches / max(total_batches, 1),
                    'total_contacts_found': total_contacts_found,
                    'total_contacts_added': total_contacts_added,
                    'deduplication_rate': 1 - (total_contacts_added / max(total_contacts_found, 1)),
                    'total_execution_time': total_execution_time,
                    'avg_execution_time': total_execution_time / max(total_batches, 1),
                },
                'period_stats': grouped_stats,
                'audit_stats': audit_stats,
            }
            
            if include_performance:
                statistics_data['performance_analysis'] = performance_stats
            
            execution_time = time.time() - start_time
            
            # Log request
            request.env['mailing.operation.audit'].log_web_request(
                request_data={
                    'endpoint': '/mailing/batch/statistics',
                    'method': 'GET',
                    'params': kwargs,
                },
                response_data=statistics_data,
                execution_time=execution_time,
                success=True
            )
            
            return self._success_response(
                data=statistics_data,
                message="Statistics retrieved successfully",
                meta={
                    'execution_time': round(execution_time, 2),
                    'period': f"{date_from_dt.date()} to {date_to_dt.date()}",
                    'group_by': group_by,
                }
            )
            
        except Exception as e:
            _logger.error("Failed to get batch statistics: %s", str(e), exc_info=True)
            return self._error_response(
                message="Failed to retrieve statistics",
                details=str(e),
                code=500
            )
    
    # ========================================
    # UTILITY METHODS
    # ========================================
    
    def _group_batches_by_period(self, batches, group_by='day'):
        """Group batches by time period for statistics."""
        grouped = {}
        
        for batch in batches:
            if not batch.create_date:
                continue
                
            if group_by == 'day':
                key = batch.create_date.strftime('%Y-%m-%d')
            elif group_by == 'week':
                key = batch.create_date.strftime('%Y-W%U')
            elif group_by == 'month':
                key = batch.create_date.strftime('%Y-%m')
            else:
                key = 'all'
            
            if key not in grouped:
                grouped[key] = {
                    'period': key,
                    'total_batches': 0,
                    'completed': 0,
                    'failed': 0,
                    'contacts_added': 0,
                    'contacts_found': 0,
                    'execution_time': 0.0,
                }
            
            stats = grouped[key]
            stats['total_batches'] += 1
            stats['contacts_added'] += batch.contacts_added
            stats['contacts_found'] += batch.contacts_found
            stats['execution_time'] += batch.execution_time or 0.0
            
            if batch.state == 'completed':
                stats['completed'] += 1
            elif batch.state == 'failed':
                stats['failed'] += 1
        
        # Calculate rates
        for stats in grouped.values():
            if stats['total_batches'] > 0:
                stats['success_rate'] = stats['completed'] / stats['total_batches']
                stats['avg_execution_time'] = stats['execution_time'] / stats['total_batches']
            else:
                stats['success_rate'] = 0.0
                stats['avg_execution_time'] = 0.0
        
        return grouped
    
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