# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError

_logger = logging.getLogger(__name__)


class MailingOperationAudit(models.Model):
    """
    Model for comprehensive audit trail of all mailing list operations.
    
    This model provides complete audit logging for all operations performed
    through the mailing list updater, enabling compliance, debugging, and
    performance analysis.
    """
    
    _name = 'mailing.operation.audit'
    _description = 'Mailing Operation Audit Log'
    _order = 'create_date desc'
    _rec_name = 'operation_display_name'
    
    # Core Audit Information
    batch_id = fields.Char(
        string='Batch ID',
        required=True,
        index=True,
        help='Reference to the batch operation'
    )
    operation_type = fields.Selection([
        ('execution_started', 'Execution Started'),
        ('execution_completed', 'Execution Completed'),
        ('execution_failed', 'Execution Failed'),
        ('rollback_started', 'Rollback Started'),
        ('rollback_completed', 'Rollback Completed'),
        ('rollback_failed', 'Rollback Failed'),
        ('preview_generated', 'Preview Generated'),
        ('template_applied', 'Template Applied'),
        ('registry_updated', 'Registry Updated'),
        ('deduplication_performed', 'Deduplication Performed'),
        ('contact_created', 'Contact Created'),
        ('contact_updated', 'Contact Updated'),
        ('error_occurred', 'Error Occurred'),
    ], string='Operation Type', required=True, index=True,
       help='Type of operation being audited')
    
    # User and Context Information
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        index=True,
        help='User who performed the operation'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help='Company context for the operation'
    )
    
    # Operation Details
    details = fields.Text(
        string='Operation Details',
        help='JSON object containing detailed operation information'
    )
    execution_time = fields.Float(
        string='Execution Time (seconds)',
        help='Time taken to complete the operation'
    )
    
    # Result Information
    success = fields.Boolean(
        string='Success',
        default=True,
        index=True,
        help='Whether the operation completed successfully'
    )
    error_message = fields.Text(
        string='Error Message',
        help='Error details if operation failed'
    )
    
    # Related Records
    mailing_list_id = fields.Many2one(
        'mailing.list',
        string='Mailing List',
        index=True,
        help='Mailing list involved in the operation'
    )
    batch_record_id = fields.Many2one(
        'mailing.list.update.batch',
        string='Batch Record',
        compute='_compute_batch_record',
        store=True,
        help='Reference to the batch record'
    )
    
    # Performance Metrics
    records_processed = fields.Integer(
        string='Records Processed',
        help='Number of records processed in this operation'
    )
    memory_usage = fields.Float(
        string='Memory Usage (MB)',
        help='Memory consumption during operation'
    )
    
    # System Information
    ip_address = fields.Char(
        string='IP Address',
        help='Client IP address when operation was performed'
    )
    user_agent = fields.Char(
        string='User Agent',
        help='Client user agent information'
    )
    
    # Display Fields
    operation_display_name = fields.Char(
        string='Operation',
        compute='_compute_operation_display_name',
        store=True,
        help='Human-readable operation description'
    )
    details_summary = fields.Char(
        string='Summary',
        compute='_compute_details_summary',
        store=True,
        help='Brief summary of operation details'
    )
    
    # SQL Constraints
    _sql_constraints = [
        ('execution_time_positive', 
         'CHECK(execution_time >= 0)', 
         'Execution time must be positive.'),
        ('records_processed_positive', 
         'CHECK(records_processed >= 0)', 
         'Records processed must be positive.'),
    ]
    
    @api.depends('batch_id')
    def _compute_batch_record(self):
        """Compute reference to the batch record."""
        for record in self:
            if record.batch_id:
                batch_record = self.env['mailing.list.update.batch'].search([
                    ('batch_id', '=', record.batch_id)
                ], limit=1)
                record.batch_record_id = batch_record.id if batch_record else False
            else:
                record.batch_record_id = False
    
    @api.depends('operation_type', 'batch_id', 'user_id')
    def _compute_operation_display_name(self):
        """Compute human-readable operation name."""
        for record in self:
            operation_name = dict(record._fields['operation_type'].selection).get(
                record.operation_type, record.operation_type
            )
            
            parts = [operation_name]
            
            if record.batch_id:
                # Truncate batch ID for display
                short_batch_id = record.batch_id[-8:] if len(record.batch_id) > 8 else record.batch_id
                parts.append(f"({short_batch_id})")
            
            record.operation_display_name = ' '.join(parts)
    
    @api.depends('details', 'records_processed', 'execution_time')
    def _compute_details_summary(self):
        """Compute brief summary of operation details."""
        for record in self:
            summary_parts = []
            
            if record.records_processed:
                summary_parts.append(f"{record.records_processed} records")
            
            if record.execution_time:
                summary_parts.append(f"{record.execution_time:.2f}s")
            
            # Try to extract key info from details JSON
            if record.details:
                try:
                    details_data = json.loads(record.details)
                    
                    # Add specific summaries based on operation type
                    if record.operation_type in ['execution_completed', 'execution_failed']:
                        contacts_added = details_data.get('contacts_added')
                        if contacts_added:
                            summary_parts.append(f"{contacts_added} added")
                    
                    elif record.operation_type in ['rollback_completed']:
                        contacts_removed = details_data.get('contacts_removed')
                        if contacts_removed:
                            summary_parts.append(f"{contacts_removed} removed")
                    
                    elif record.operation_type == 'deduplication_performed':
                        removed_count = details_data.get('removed_count')
                        if removed_count:
                            summary_parts.append(f"{removed_count} duplicates")
                
                except (ValueError, TypeError):
                    pass
            
            record.details_summary = ', '.join(summary_parts) if summary_parts else 'No details'
    
    @api.constrains('details')
    def _check_details_json(self):
        """Validate that details field contains valid JSON."""
        for record in self:
            if record.details:
                try:
                    json.loads(record.details)
                except (ValueError, TypeError):
                    raise ValidationError(
                        _("Details field must contain valid JSON.")
                    )
    
    @api.model
    def create(self, vals):
        """Override create to capture system information."""
        # Capture request context if available
        request = getattr(self.env, 'request', None)
        if request:
            if not vals.get('ip_address'):
                vals['ip_address'] = request.httprequest.environ.get('REMOTE_ADDR')
            if not vals.get('user_agent'):
                vals['user_agent'] = request.httprequest.environ.get('HTTP_USER_AGENT')
        
        return super(MailingOperationAudit, self).create(vals)
    
    # Audit Logging Methods
    
    @api.model
    def log_operation(self, batch_id, operation_type, details=None, 
                     mailing_list_id=None, execution_time=0.0, success=True, 
                     error_message=None, **kwargs):
        """
        Log an operation to the audit trail.
        
        Args:
            batch_id (str): Batch identifier
            operation_type (str): Type of operation
            details (dict, optional): Operation details
            mailing_list_id (int, optional): Mailing list ID
            execution_time (float): Execution time in seconds
            success (bool): Whether operation succeeded
            error_message (str, optional): Error message if failed
            **kwargs: Additional field values
            
        Returns:
            mailing.operation.audit: Created audit record
        """
        vals = {
            'batch_id': batch_id,
            'operation_type': operation_type,
            'user_id': self.env.user.id,
            'details': json.dumps(details or {}),
            'execution_time': execution_time,
            'success': success,
            'error_message': error_message,
        }
        
        if mailing_list_id:
            vals['mailing_list_id'] = mailing_list_id
        
        # Extract records processed from details
        if details and isinstance(details, dict):
            records_count = (
                details.get('contacts_found') or 
                details.get('contacts_added') or 
                details.get('contacts_removed') or 
                details.get('records_processed') or 
                0
            )
            vals['records_processed'] = records_count
        
        # Add any additional values
        vals.update(kwargs)
        
        audit_record = self.create(vals)
        
        # Log to system logger for critical operations
        if operation_type in ['execution_failed', 'rollback_failed', 'error_occurred']:
            _logger.error(
                "Audit: %s failed for batch %s: %s", 
                operation_type, batch_id, error_message or 'Unknown error'
            )
        elif operation_type in ['execution_completed', 'rollback_completed']:
            _logger.info(
                "Audit: %s for batch %s (%.2fs, %d records)", 
                operation_type, batch_id, execution_time, vals.get('records_processed', 0)
            )
        
        return audit_record
    
    def get_audit_trail(self, batch_id=None, operation_types=None, limit=None):
        """
        Get audit trail for specific criteria.
        
        Args:
            batch_id (str, optional): Filter by batch ID
            operation_types (list, optional): Filter by operation types
            limit (int, optional): Limit results
            
        Returns:
            list: List of audit records
        """
        domain = []
        
        if batch_id:
            domain.append(('batch_id', '=', batch_id))
        
        if operation_types:
            domain.append(('operation_type', 'in', operation_types))
        
        # Apply company filter
        domain.append(('company_id', '=', self.env.company.id))
        
        records = self.search(domain, limit=limit)
        
        result = []
        for record in records:
            # Parse details safely
            try:
                details_data = json.loads(record.details or '{}')
            except (ValueError, TypeError):
                details_data = {}
            
            result.append({
                'id': record.id,
                'batch_id': record.batch_id,
                'operation_type': record.operation_type,
                'operation_display_name': record.operation_display_name,
                'user': record.user_id.name,
                'create_date': record.create_date,
                'execution_time': record.execution_time,
                'success': record.success,
                'error_message': record.error_message,
                'records_processed': record.records_processed,
                'details_summary': record.details_summary,
                'details': details_data,
                'mailing_list': record.mailing_list_id.name if record.mailing_list_id else None,
            })
        
        return result
    
    @api.model
    def get_performance_stats(self, date_from=None, date_to=None, group_by='day'):
        """
        Get performance statistics for operations.
        
        Args:
            date_from (datetime, optional): Start date filter
            date_to (datetime, optional): End date filter
            group_by (str): Grouping period ('day', 'week', 'month')
            
        Returns:
            dict: Performance statistics
        """
        domain = [('company_id', '=', self.env.company.id)]
        
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))
        
        records = self.search(domain)
        
        # Group by time period
        grouped_data = {}
        for record in records:
            if group_by == 'day':
                period_key = record.create_date.strftime('%Y-%m-%d')
            elif group_by == 'week':
                period_key = record.create_date.strftime('%Y-W%U')
            elif group_by == 'month':
                period_key = record.create_date.strftime('%Y-%m')
            else:
                period_key = 'all'
            
            if period_key not in grouped_data:
                grouped_data[period_key] = {
                    'total_operations': 0,
                    'successful_operations': 0,
                    'failed_operations': 0,
                    'total_execution_time': 0.0,
                    'total_records_processed': 0,
                    'operation_types': {},
                }
            
            group = grouped_data[period_key]
            group['total_operations'] += 1
            
            if record.success:
                group['successful_operations'] += 1
            else:
                group['failed_operations'] += 1
            
            group['total_execution_time'] += record.execution_time or 0.0
            group['total_records_processed'] += record.records_processed or 0
            
            # Count operation types
            op_type = record.operation_type
            if op_type not in group['operation_types']:
                group['operation_types'][op_type] = 0
            group['operation_types'][op_type] += 1
        
        # Calculate averages
        for period, data in grouped_data.items():
            if data['total_operations'] > 0:
                data['avg_execution_time'] = data['total_execution_time'] / data['total_operations']
                data['success_rate'] = data['successful_operations'] / data['total_operations']
            else:
                data['avg_execution_time'] = 0.0
                data['success_rate'] = 0.0
        
        return {
            'period_data': grouped_data,
            'summary': {
                'total_operations': sum(d['total_operations'] for d in grouped_data.values()),
                'total_records_processed': sum(d['total_records_processed'] for d in grouped_data.values()),
                'overall_success_rate': (
                    sum(d['successful_operations'] for d in grouped_data.values()) /
                    max(sum(d['total_operations'] for d in grouped_data.values()), 1)
                ),
                'total_execution_time': sum(d['total_execution_time'] for d in grouped_data.values()),
            }
        }
    
    @api.model
    def get_error_analysis(self, days_back=30):
        """
        Analyze errors over a specific period.
        
        Args:
            days_back (int): Number of days to analyze
            
        Returns:
            dict: Error analysis data
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=days_back)
        
        error_records = self.search([
            ('success', '=', False),
            ('create_date', '>=', cutoff_date),
            ('company_id', '=', self.env.company.id)
        ])
        
        # Group errors by type and message
        error_groups = {}
        operation_errors = {}
        
        for record in error_records:
            # Group by operation type
            op_type = record.operation_type
            if op_type not in operation_errors:
                operation_errors[op_type] = []
            operation_errors[op_type].append({
                'batch_id': record.batch_id,
                'error_message': record.error_message,
                'create_date': record.create_date,
                'user': record.user_id.name,
            })
            
            # Group by error message pattern
            error_msg = record.error_message or 'Unknown error'
            # Simplify error message for grouping
            error_key = error_msg[:100] + '...' if len(error_msg) > 100 else error_msg
            
            if error_key not in error_groups:
                error_groups[error_key] = 0
            error_groups[error_key] += 1
        
        return {
            'total_errors': len(error_records),
            'error_by_operation': operation_errors,
            'error_by_message': sorted(
                error_groups.items(), 
                key=lambda x: x[1], 
                reverse=True
            ),
            'analysis_period_days': days_back,
        }
    
    @api.model
    def cleanup_old_audit_logs(self, days_to_keep=365):
        """
        Clean up old audit log records.
        
        Args:
            days_to_keep (int): Number of days to retain logs
            
        Returns:
            int: Number of records deleted
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=days_to_keep)
        
        old_records = self.search([
            ('create_date', '<=', cutoff_date),
            ('company_id', '=', self.env.company.id)
        ])
        
        count = len(old_records)
        if count > 0:
            old_records.unlink()
            _logger.info("Cleaned up %d old audit log records", count)
        
        return count
    
    @api.model
    def export_audit_trail(self, batch_id=None, date_from=None, date_to=None, format='csv'):
        """
        Export audit trail data for compliance or analysis.
        
        Args:
            batch_id (str, optional): Filter by batch ID
            date_from (datetime, optional): Start date filter
            date_to (datetime, optional): End date filter
            format (str): Export format ('csv', 'json')
            
        Returns:
            dict: Export data and metadata
        """
        domain = [('company_id', '=', self.env.company.id)]
        
        if batch_id:
            domain.append(('batch_id', '=', batch_id))
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))
        
        records = self.search(domain)
        
        export_data = []
        for record in records:
            export_data.append({
                'batch_id': record.batch_id,
                'operation_type': record.operation_type,
                'user': record.user_id.name,
                'company': record.company_id.name,
                'create_date': record.create_date.isoformat() if record.create_date else None,
                'execution_time': record.execution_time,
                'success': record.success,
                'error_message': record.error_message,
                'records_processed': record.records_processed,
                'mailing_list': record.mailing_list_id.name if record.mailing_list_id else None,
                'details': record.details,
                'ip_address': record.ip_address,
                'user_agent': record.user_agent,
            })
        
        return {
            'data': export_data,
            'format': format,
            'record_count': len(export_data),
            'export_date': fields.Datetime.now().isoformat(),
            'filters': {
                'batch_id': batch_id,
                'date_from': date_from.isoformat() if date_from else None,
                'date_to': date_to.isoformat() if date_to else None,
            }
        }
    

    def export_audit_trail(self, batch_id=None, date_from=None, date_to=None, format='csv'):
        """
        Export audit trail data for compliance or analysis.
        
        Args:
            batch_id (str, optional): Filter by batch ID
            date_from (datetime, optional): Start date filter
            date_to (datetime, optional): End date filter
            format (str): Export format ('csv', 'json')
            
        Returns:
            dict: Export data and metadata
        """
        domain = [('company_id', '=', self.env.company.id)]
        
        if batch_id:
            domain.append(('batch_id', '=', batch_id))
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))
        
        records = self.search(domain)
        
        export_data = []
        for record in records:
            export_data.append({
                'batch_id': record.batch_id,
                'operation_type': record.operation_type,
                'user': record.user_id.name,
                'company': record.company_id.name,
                'create_date': record.create_date.isoformat() if record.create_date else None,
                'execution_time': record.execution_time,
                'success': record.success,
                'error_message': record.error_message,
                'records_processed': record.records_processed,
                'mailing_list': record.mailing_list_id.name if record.mailing_list_id else None,
                'details': record.details,
                'ip_address': record.ip_address,
                'user_agent': record.user_agent,
            })
        
        return {
            'data': export_data,
            'format': format,
            'record_count': len(export_data),
            'export_date': fields.Datetime.now().isoformat(),
            'filters': {
                'batch_id': batch_id,
                'date_from': date_from.isoformat() if date_from else None,
                'date_to': date_to.isoformat() if date_to else None,
            }
        }
    
    # ========================================
    # WEB INTEGRATION METHODS (Phase 2)
    # ========================================
    
    @api.model
    def log_web_request(self, request_data, response_data, execution_time=0.0, 
                       success=True, error_message=None):
        """
        Log web requests for comprehensive audit trail.
        
        Args:
            request_data (dict): Web request information
            response_data (dict): Web response information
            execution_time (float): Request execution time
            success (bool): Whether request succeeded
            error_message (str, optional): Error message if failed
            
        Returns:
            mailing.operation.audit: Created audit record
        """
        # Extract relevant information from request
        endpoint = request_data.get('endpoint', 'unknown')
        method = request_data.get('method', 'GET')
        batch_id = request_data.get('batch_id', 'WEB_REQUEST')
        
        # Determine operation type based on endpoint
        operation_type = self._determine_operation_type_from_endpoint(endpoint, method)
        
        # Prepare detailed audit information
        audit_details = {
            'source': 'web_interface',
            'endpoint': endpoint,
            'method': method,
            'request_size': len(str(request_data)),
            'response_size': len(str(response_data)),
            'status_code': response_data.get('status_code', 200),
            'request_params': request_data.get('params', {}),
            'response_summary': {
                'success': success,
                'data_count': self._count_response_data(response_data),
            }
        }
        
        # Add error details if present
        if error_message:
            audit_details['error_details'] = {
                'message': error_message,
                'type': 'web_request_error',
            }
        
        # Add performance metrics
        if execution_time > 0:
            audit_details['performance'] = {
                'execution_time': execution_time,
                'requests_per_second': 1.0 / execution_time if execution_time > 0 else 0,
            }
        
        # Get mailing list ID if available
        mailing_list_id = None
        if isinstance(request_data.get('params'), dict):
            mailing_list_id = request_data['params'].get('mailing_list_id')
        
        # Create audit record
        audit_record = self.create({
            'batch_id': batch_id,
            'operation_type': operation_type,
            'user_id': self.env.user.id,
            'details': json.dumps(audit_details),
            'execution_time': execution_time,
            'success': success,
            'error_message': error_message,
            'mailing_list_id': mailing_list_id,
            'records_processed': self._count_response_data(response_data),
            'company_id': self.env.company.id,
        })
        
        # Log to system logger for important operations
        if not success:
            _logger.warning(
                "Web request failed: %s %s - %s", 
                method, endpoint, error_message
            )
        elif execution_time > 5.0:  # Log slow requests
            _logger.info(
                "Slow web request: %s %s took %.2fs", 
                method, endpoint, execution_time
            )
        
        return audit_record
    
    @api.model
    def log_websocket_event(self, event_type, batch_id, client_info=None, data=None):
        """
        Log WebSocket events for real-time communication audit.
        
        Args:
            event_type (str): Type of WebSocket event
            batch_id (str): Associated batch ID
            client_info (dict, optional): Client connection information
            data (dict, optional): Event data
            
        Returns:
            mailing.operation.audit: Created audit record
        """
        audit_details = {
            'source': 'websocket',
            'event_type': event_type,
            'client_info': client_info or {},
            'event_data': data or {},
            'timestamp': fields.Datetime.now().isoformat(),
        }
        
        return self.create({
            'batch_id': batch_id,
            'operation_type': 'websocket_event',
            'user_id': self.env.user.id,
            'details': json.dumps(audit_details),
            'execution_time': 0.0,
            'success': True,
            'company_id': self.env.company.id,
        })
    
    @api.model
    def get_web_audit_summary(self, date_from=None, date_to=None):
        """
        Get audit summary specifically for web interface operations.
        
        Args:
            date_from (datetime, optional): Start date filter
            date_to (datetime, optional): End date filter
            
        Returns:
            dict: Web audit summary
        """
        domain = [
            ('company_id', '=', self.env.company.id),
            ('details', 'ilike', '"source": "web_interface"')
        ]
        
        if date_from:
            domain.append(('create_date', '>=', date_from))
        if date_to:
            domain.append(('create_date', '<=', date_to))
        
        web_records = self.search(domain)
        
        # Analyze web requests
        endpoint_stats = {}
        user_stats = {}
        error_patterns = {}
        performance_stats = []
        
        for record in web_records:
            try:
                details = json.loads(record.details or '{}')
                endpoint = details.get('endpoint', 'unknown')
                method = details.get('method', 'GET')
                endpoint_key = f"{method} {endpoint}"
                
                # Endpoint statistics
                if endpoint_key not in endpoint_stats:
                    endpoint_stats[endpoint_key] = {
                        'count': 0,
                        'success_count': 0,
                        'total_time': 0.0,
                        'errors': 0
                    }
                
                stats = endpoint_stats[endpoint_key]
                stats['count'] += 1
                stats['total_time'] += record.execution_time or 0.0
                
                if record.success:
                    stats['success_count'] += 1
                else:
                    stats['errors'] += 1
                    
                    # Track error patterns
                    error_msg = record.error_message or 'Unknown error'
                    error_key = error_msg[:50]  # Truncate for grouping
                    error_patterns[error_key] = error_patterns.get(error_key, 0) + 1
                
                # User statistics
                user_name = record.user_id.name
                if user_name not in user_stats:
                    user_stats[user_name] = {'requests': 0, 'errors': 0}
                
                user_stats[user_name]['requests'] += 1
                if not record.success:
                    user_stats[user_name]['errors'] += 1
                
                # Performance data
                if record.execution_time and record.execution_time > 0:
                    performance_stats.append({
                        'endpoint': endpoint_key,
                        'time': record.execution_time,
                        'date': record.create_date,
                    })
                    
            except (ValueError, TypeError):
                continue
        
        # Calculate summary metrics
        total_requests = len(web_records)
        successful_requests = len([r for r in web_records if r.success])
        success_rate = successful_requests / max(total_requests, 1)
        
        # Calculate average response times
        for endpoint, stats in endpoint_stats.items():
            if stats['count'] > 0:
                stats['avg_time'] = stats['total_time'] / stats['count']
                stats['success_rate'] = stats['success_count'] / stats['count']
        
        return {
            'period': {
                'date_from': date_from.isoformat() if date_from else None,
                'date_to': date_to.isoformat() if date_to else None,
            },
            'summary': {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'failed_requests': total_requests - successful_requests,
                'success_rate': success_rate,
                'unique_endpoints': len(endpoint_stats),
                'unique_users': len(user_stats),
            },
            'endpoint_stats': dict(sorted(
                endpoint_stats.items(), 
                key=lambda x: x[1]['count'], 
                reverse=True
            )),
            'user_stats': dict(sorted(
                user_stats.items(), 
                key=lambda x: x[1]['requests'], 
                reverse=True
            )),
            'error_patterns': dict(sorted(
                error_patterns.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]),  # Top 10 error patterns
            'performance_metrics': {
                'avg_response_time': (
                    sum(p['time'] for p in performance_stats) / 
                    max(len(performance_stats), 1)
                ),
                'slowest_endpoints': sorted(
                    [(k, v['avg_time']) for k, v in endpoint_stats.items()], 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5],
            }
        }
    
    def _determine_operation_type_from_endpoint(self, endpoint, method):
        """Determine audit operation type from web endpoint."""
        endpoint_mapping = {
            '/mailing/update/preview': 'preview_generated',
            '/mailing/update/execute': 'execution_started',
            '/mailing/batch/rollback': 'rollback_started',
            '/mailing/registry/sources': 'registry_updated',
            '/mailing/templates': 'template_applied',
        }
        
        # Try exact match first
        if endpoint in endpoint_mapping:
            return endpoint_mapping[endpoint]
        
        # Try pattern matching
        if 'preview' in endpoint:
            return 'preview_generated'
        elif 'execute' in endpoint:
            return 'execution_started'
        elif 'rollback' in endpoint:
            return 'rollback_started'
        elif 'registry' in endpoint:
            return 'registry_updated'
        elif 'template' in endpoint:
            return 'template_applied'
        else:
            return 'web_request'
    
    def _count_response_data(self, response_data):
        """Count meaningful data items in response."""
        if not isinstance(response_data, dict):
            return 0
        
        data = response_data.get('data', {})
        if isinstance(data, dict):
            # Count contacts, batches, or other meaningful items
            return (
                data.get('total_after_dedup', 0) or
                data.get('contacts_added', 0) or  
                data.get('batch_count', 0) or
                len(data.get('sample_contacts', [])) or
                len(data.get('sources', [])) or
                1  # At least one item if data exists
            )
        elif isinstance(data, list):
            return len(data)
        else:
            return 1 if data else 0