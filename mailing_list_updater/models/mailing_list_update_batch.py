# -*- coding: utf-8 -*-

import json
import uuid
import logging
from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, AccessError

_logger = logging.getLogger(__name__)


class MailingListUpdateBatch(models.Model):
    """
    Model for tracking batch operations for mailing list updates.
    
    This model manages the execution, tracking, and rollback of mailing list
    update operations. Each batch represents a complete update operation
    that can add multiple contacts from various sources to a mailing list.
    """
    
    _name = 'mailing.list.update.batch'
    _description = 'Mailing List Update Batch'
    _order = 'create_date desc'
    _rec_name = 'batch_display_name'
    
    # Core Identification
    batch_id = fields.Char(
        string='Batch ID',
        required=True,
        index=True,
        readonly=True,
        copy=False,
        help='Unique identifier for this batch operation'
    )
    
    # Relationships
    mailing_list_id = fields.Many2one(
        'mailing.list',
        string='Mailing List',
        required=True,
        index=True,
        ondelete='cascade',
        help='The mailing list being updated'
    )
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        index=True,
        default=lambda self: self.env.user,
        help='User who initiated this batch operation'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help='Company context for this operation'
    )
    
    # Operation Configuration
    source_models = fields.Text(
        string='Source Models',
        required=True,
        help='JSON array of source model configurations used in this batch'
    )
    filter_criteria = fields.Text(
        string='Filter Criteria',
        help='JSON object containing the filter criteria used'
    )
    
    # Status and Results
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('rolled_back', 'Rolled Back'),
    ], string='State', default='draft', required=True, index=True)
    
    contacts_found = fields.Integer(
        string='Contacts Found',
        readonly=True,
        help='Total number of contacts found before deduplication'
    )
    contacts_deduplicated = fields.Integer(
        string='Contacts Deduplicated',
        readonly=True,
        help='Number of duplicate contacts removed'
    )
    contacts_added = fields.Integer(
        string='Contacts Added',
        readonly=True,
        help='Number of contacts actually added to the mailing list'
    )
    
    # Execution Details
    start_time = fields.Datetime(
        string='Start Time',
        readonly=True,
        help='When the batch operation started'
    )
    end_time = fields.Datetime(
        string='End Time',
        readonly=True,
        help='When the batch operation completed'
    )
    execution_time = fields.Float(
        string='Execution Time (seconds)',
        readonly=True,
        compute='_compute_execution_time',
        store=True,
        help='Total execution time in seconds'
    )
    
    # Error Handling
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        help='Error details if the operation failed'
    )
    
    # Rollback Information
    is_rolled_back = fields.Boolean(
        string='Rolled Back',
        readonly=True,
        default=False,
        index=True,
        help='Whether this batch has been rolled back'
    )
    rollback_date = fields.Datetime(
        string='Rollback Date',
        readonly=True,
        help='When this batch was rolled back'
    )
    rollback_user_id = fields.Many2one(
        'res.users',
        string='Rollback User',
        readonly=True,
        help='User who performed the rollback'
    )
    rollback_reason = fields.Text(
        string='Rollback Reason',
        readonly=True,
        help='Reason for rolling back this batch'
    )
    
    # Display and Computed Fields
    batch_display_name = fields.Char(
        string='Batch Name',
        compute='_compute_batch_display_name',
        store=True,
        help='Human-readable batch identifier'
    )
    can_rollback = fields.Boolean(
        string='Can Rollback',
        compute='_compute_can_rollback',
        help='Whether this batch can be rolled back'
    )
    
    # Tracking and Relationships
    tracking_ids = fields.One2many(
        'mailing.contact.tracking',
        'batch_id',
        string='Contact Tracking',
        readonly=True,
        help='Individual contact tracking records for this batch'
    )
    audit_log_ids = fields.One2many(
        'mailing.operation.audit',
        'batch_id',
        string='Audit Log',
        readonly=True,
        help='Audit trail for this batch'
    )
    
    # SQL Constraints
    _sql_constraints = [
        ('unique_batch_id', 'UNIQUE(batch_id)', 'Batch ID must be unique.'),
        ('contacts_found_positive', 'CHECK(contacts_found >= 0)', 'Contacts found must be positive.'),
        ('contacts_added_positive', 'CHECK(contacts_added >= 0)', 'Contacts added must be positive.'),
        ('execution_time_positive', 'CHECK(execution_time >= 0)', 'Execution time must be positive.'),
    ]
    
    @api.depends('start_time', 'end_time')
    def _compute_execution_time(self):
        """Compute execution time in seconds."""
        for record in self:
            if record.start_time and record.end_time:
                delta = record.end_time - record.start_time
                record.execution_time = delta.total_seconds()
            else:
                record.execution_time = 0.0
    
    @api.depends('batch_id', 'mailing_list_id', 'create_date')
    def _compute_batch_display_name(self):
        """Compute human-readable batch name."""
        for record in self:
            if record.mailing_list_id and record.create_date:
                date_str = record.create_date.strftime('%Y-%m-%d %H:%M')
                record.batch_display_name = f"{record.mailing_list_id.name} - {date_str}"
            else:
                record.batch_display_name = record.batch_id or 'New Batch'
    
    @api.depends('state', 'is_rolled_back', 'create_date')
    def _compute_can_rollback(self):
        """Determine if batch can be rolled back (within 24 hours and completed)."""
        for record in self:
            if (record.state == 'completed' and 
                not record.is_rolled_back and 
                record.create_date):
                
                # Check 24-hour window
                cutoff_time = record.create_date + timedelta(hours=24)
                record.can_rollback = fields.Datetime.now() <= cutoff_time
            else:
                record.can_rollback = False
    
    @api.model
    def create(self, vals):
        """Override create to generate batch_id and set initial state."""
        if not vals.get('batch_id'):
            # Generate unique batch ID with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_id = str(uuid.uuid4())[:8]
            vals['batch_id'] = f"BATCH_{timestamp}_{unique_id}"
        
        return super(MailingListUpdateBatch, self).create(vals)
    
    # Core Business Methods
    
    def execute_update(self, source_configs, filter_criteria=None, preview_only=False):
        """
        Execute the mailing list update operation.
        
        Args:
            source_configs (list): List of source model configurations
            filter_criteria (dict, optional): Filter criteria to apply
            preview_only (bool): If True, only return preview without updating
            
        Returns:
            dict: Results of the operation
        """
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_("Only draft batches can be executed."))
        
        # Validate permissions
        self._check_execution_permissions()
        
        try:
            # Update state and start tracking
            self.write({
                'state': 'processing',
                'start_time': fields.Datetime.now(),
                'source_models': json.dumps(source_configs),
                'filter_criteria': json.dumps(filter_criteria or {}),
            })
            
            # Log operation start
            self._log_audit_event('execution_started', {
                'source_configs': source_configs,
                'filter_criteria': filter_criteria,
                'preview_only': preview_only,
            })
            
            # Get registry entries for source models
            registry_model = self.env['mailing.source.registry']
            all_contacts = []
            source_stats = {}
            
            for config in source_configs:
                model_name = config.get('model_name')
                if not model_name:
                    continue
                
                # Get registry entry
                registry_entry = registry_model.search([
                    ('model_name', '=', model_name),
                    ('is_active', '=', True),
                    ('company_id', 'in', [self.company_id.id, False])
                ], limit=1)
                
                if not registry_entry:
                    _logger.warning("Registry entry not found for model: %s", model_name)
                    continue
                
                # Extract contacts from this source
                contacts = self._extract_contacts_from_source(
                    registry_entry, config, filter_criteria
                )
                
                source_stats[model_name] = {
                    'found': len(contacts),
                    'registry_id': registry_entry.id,
                }
                
                all_contacts.extend(contacts)
                
                # Update registry usage stats
                if not preview_only:
                    registry_entry.update_usage_stats()
            
            # Perform deduplication
            dedup_engine = self.env['mailing.deduplication.engine']
            deduplicated_contacts, dedup_stats = dedup_engine.deduplicate_contacts(
                all_contacts, self.mailing_list_id
            )
            
            # Update statistics
            self.write({
                'contacts_found': len(all_contacts),
                'contacts_deduplicated': dedup_stats.get('removed_count', 0),
            })
            
            if preview_only:
                # Return preview data without actually updating
                return {
                    'success': True,
                    'preview': True,
                    'total_found': len(all_contacts),
                    'total_after_dedup': len(deduplicated_contacts),
                    'source_stats': source_stats,
                    'deduplication_stats': dedup_stats,
                    'sample_contacts': deduplicated_contacts[:100],  # First 100 for preview
                }
            
            # Create mailing contacts
            contacts_added = self._create_mailing_contacts(deduplicated_contacts)
            
            # Update final state
            self.write({
                'state': 'completed',
                'end_time': fields.Datetime.now(),
                'contacts_added': contacts_added,
            })
            
            # Log successful completion
            self._log_audit_event('execution_completed', {
                'contacts_found': len(all_contacts),
                'contacts_added': contacts_added,
                'source_stats': source_stats,
                'deduplication_stats': dedup_stats,
            })
            
            return {
                'success': True,
                'batch_id': self.batch_id,
                'contacts_added': contacts_added,
                'source_stats': source_stats,
                'deduplication_stats': dedup_stats,
            }
            
        except Exception as e:
            # Handle execution failure
            error_msg = str(e)
            _logger.error("Batch execution failed for %s: %s", self.batch_id, error_msg)
            
            self.write({
                'state': 'failed',
                'end_time': fields.Datetime.now(),
                'error_message': error_msg,
            })
            
            self._log_audit_event('execution_failed', {
                'error_message': error_msg,
            })
            
            raise UserError(_("Batch execution failed: %s") % error_msg)
    
    def rollback_operation(self, reason=None):
        """
        Rollback this batch operation.
        
        Args:
            reason (str, optional): Reason for rollback
            
        Returns:
            dict: Rollback results
        """
        self.ensure_one()
        
        if not self.can_rollback:
            raise UserError(_("This batch cannot be rolled back."))
        
        if self.is_rolled_back:
            raise UserError(_("This batch has already been rolled back."))
        
        # Validate permissions
        self._check_rollback_permissions()
        
        try:
            # Find all contacts added by this batch
            tracking_records = self.tracking_ids
            contact_ids = tracking_records.mapped('mailing_contact_id')
            
            if not contact_ids:
                _logger.warning("No contacts found to rollback for batch %s", self.batch_id)
                return {'success': True, 'contacts_removed': 0}
            
            # Remove contacts from mailing list
            contacts_removed = 0
            for contact in contact_ids:
                if contact.exists():
                    contact.unlink()
                    contacts_removed += 1
            
            # Update batch status
            self.write({
                'is_rolled_back': True,
                'rollback_date': fields.Datetime.now(),
                'rollback_user_id': self.env.user.id,
                'rollback_reason': reason or 'Manual rollback',
            })
            
            # Log rollback event
            self._log_audit_event('rollback_completed', {
                'contacts_removed': contacts_removed,
                'reason': reason,
            })
            
            _logger.info(
                "Successfully rolled back batch %s, removed %d contacts", 
                self.batch_id, contacts_removed
            )
            
            return {
                'success': True,
                'batch_id': self.batch_id,
                'contacts_removed': contacts_removed,
            }
            
        except Exception as e:
            error_msg = str(e)
            _logger.error("Rollback failed for batch %s: %s", self.batch_id, error_msg)
            
            self._log_audit_event('rollback_failed', {
                'error_message': error_msg,
            })
            
            raise UserError(_("Rollback failed: %s") % error_msg)
    
    def get_batch_statistics(self):
        """
        Get comprehensive statistics for this batch.
        
        Returns:
            dict: Batch statistics
        """
        self.ensure_one()
        
        # Parse source models
        try:
            source_models = json.loads(self.source_models) if self.source_models else []
        except (ValueError, TypeError):
            source_models = []
        
        # Get tracking statistics
        tracking_stats = {}
        for tracking in self.tracking_ids:
            source = tracking.source_model
            if source not in tracking_stats:
                tracking_stats[source] = 0
            tracking_stats[source] += 1
        
        return {
            'batch_id': self.batch_id,
            'mailing_list': self.mailing_list_id.name,
            'state': self.state,
            'created_by': self.user_id.name,
            'create_date': self.create_date,
            'execution_time': self.execution_time,
            'contacts_found': self.contacts_found,
            'contacts_deduplicated': self.contacts_deduplicated,
            'contacts_added': self.contacts_added,
            'source_models': source_models,
            'tracking_stats': tracking_stats,
            'is_rolled_back': self.is_rolled_back,
            'can_rollback': self.can_rollback,
            'rollback_info': {
                'date': self.rollback_date,
                'user': self.rollback_user_id.name if self.rollback_user_id else None,
                'reason': self.rollback_reason,
            } if self.is_rolled_back else None,
        }
    
    # Helper Methods
    
    def _extract_contacts_from_source(self, registry_entry, config, filter_criteria):
        """Extract contacts from a specific source model."""
        model = self.env[registry_entry.model_name]
        field_mapping = registry_entry.get_field_mapping()
        
        # Build domain
        domain = [('company_id', '=', self.company_id.id)]
        
        # Add active filter if field exists
        if field_mapping.get('active_field'):
            domain.append((field_mapping['active_field'], '=', True))
        
        # Apply filter criteria
        if filter_criteria and isinstance(filter_criteria, dict):
            for field, criteria in filter_criteria.items():
                if field in registry_entry.get_filter_fields():
                    # Simple field filtering (can be extended)
                    if isinstance(criteria, dict):
                        operator = criteria.get('operator', '=')
                        value = criteria.get('value')
                        if value is not None:
                            domain.append((field, operator, value))
        
        # Execute search
        records = model.search(domain)
        
        # Extract contact data
        contacts = []
        for record in records:
            email = getattr(record, field_mapping['email_field'], None)
            name = getattr(record, field_mapping['name_field'], None)
            
            if email:  # Only include records with email
                contact_data = {
                    'email': email,
                    'name': name or email,
                    'source_model': registry_entry.model_name,
                    'source_record_id': record.id,
                    'registry_id': registry_entry.id,
                }
                
                # Add phone if available
                if field_mapping.get('phone_field'):
                    phone = getattr(record, field_mapping['phone_field'], None)
                    if phone:
                        contact_data['phone'] = phone
                
                contacts.append(contact_data)
        
        return contacts
    
    def _create_mailing_contacts(self, deduplicated_contacts):
        """Create mailing.contact records and tracking entries."""
        mailing_contact_model = self.env['mailing.contact']
        tracking_model = self.env['mailing.contact.tracking']
        
        contacts_added = 0
        
        for contact_data in deduplicated_contacts:
            # Create mailing contact
            mailing_contact = mailing_contact_model.create({
                'email': contact_data['email'],
                'name': contact_data['name'],
                'list_ids': [(4, self.mailing_list_id.id)],
                'source_model': contact_data['source_model'],
                'source_record_id': contact_data['source_record_id'],
                'last_batch_id': self.batch_id,
                'is_auto_added': True,
                'company_id': self.company_id.id,
            })
            
            # Create tracking record
            tracking_model.create({
                'batch_id': self.batch_id,
                'mailing_contact_id': mailing_contact.id,
                'source_model': contact_data['source_model'],
                'source_record_id': contact_data['source_record_id'],
                'original_email': contact_data['email'],
                'company_id': self.company_id.id,
            })
            
            contacts_added += 1
        
        return contacts_added
    
    def _check_execution_permissions(self):
        """Check if user has permissions to execute batch operations."""
        if not self.env.user.has_group('mass_mailing.group_mass_mailing_user'):
            raise AccessError(_("You don't have permission to execute mailing list updates."))
        
        # Check mailing list access
        try:
            self.mailing_list_id.check_access_rights('write')
            self.mailing_list_id.check_access_rule('write')
        except AccessError:
            raise AccessError(_("You don't have permission to modify this mailing list."))
    
    def _check_rollback_permissions(self):
        """Check if user has permissions to rollback batch operations."""
        if not self.env.user.has_group('mass_mailing.group_mass_mailing_user'):
            raise AccessError(_("You don't have permission to rollback mailing list updates."))
        
        # Check if user can modify the mailing list
        try:
            self.mailing_list_id.check_access_rights('write')
            self.mailing_list_id.check_access_rule('write')
        except AccessError:
            raise AccessError(_("You don't have permission to modify this mailing list."))
    
    def _log_audit_event(self, event_type, data):
        """Log an audit event for this batch."""
        self.env['mailing.operation.audit'].create({
            'batch_id': self.batch_id,
            'operation_type': event_type,
            'user_id': self.env.user.id,
            'details': json.dumps(data),
            'execution_time': 0.0,  # Will be updated by audit model
            'company_id': self.company_id.id,
        })


    def _log_audit_event(self, event_type, data):
        """Log an audit event for this batch."""
        self.env['mailing.operation.audit'].create({
            'batch_id': self.batch_id,
            'operation_type': event_type,
            'user_id': self.env.user.id,
            'details': json.dumps(data),
            'execution_time': 0.0,  # Will be updated by audit model
            'company_id': self.company_id.id,
        })
    
    # ========================================
    # WEB INTEGRATION METHODS (Phase 2)
    # ========================================
    
    def to_json_preview(self):
        """
        Convert batch preview data to JSON format for web responses.
        
        Returns:
            dict: JSON-serializable preview data
        """
        self.ensure_one()
        
        # Parse source models safely
        try:
            source_models = json.loads(self.source_models) if self.source_models else []
        except (ValueError, TypeError):
            source_models = []
        
        # Parse filter criteria safely
        try:
            filter_criteria = json.loads(self.filter_criteria) if self.filter_criteria else {}
        except (ValueError, TypeError):
            filter_criteria = {}
        
        return {
            'batch_id': self.batch_id,
            'batch_display_name': self.batch_display_name,
            'mailing_list': {
                'id': self.mailing_list_id.id,
                'name': self.mailing_list_id.name,
                'contact_count': len(self.mailing_list_id.contact_ids),
            } if self.mailing_list_id else None,
            'state': self.state,
            'source_models': source_models,
            'filter_criteria': filter_criteria,
            'statistics': {
                'contacts_found': self.contacts_found,
                'contacts_deduplicated': self.contacts_deduplicated,
                'contacts_added': self.contacts_added,
                'execution_time': self.execution_time,
            },
            'dates': {
                'create_date': self.create_date.isoformat() if self.create_date else None,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': self.end_time.isoformat() if self.end_time else None,
            },
            'rollback_info': {
                'can_rollback': self.can_rollback,
                'is_rolled_back': self.is_rolled_back,
                'rollback_date': self.rollback_date.isoformat() if self.rollback_date else None,
                'rollback_user': self.rollback_user_id.name if self.rollback_user_id else None,
                'rollback_reason': self.rollback_reason,
            },
            'user_info': {
                'created_by': self.user_id.name if self.user_id else None,
                'user_id': self.user_id.id if self.user_id else None,
            },
            'error_message': self.error_message,
        }
    
    def get_progress_status(self):
        """
        Get current progress status for WebSocket updates.
        
        Returns:
            dict: Progress information
        """
        self.ensure_one()
        
        progress_percentage = 0.0
        estimated_remaining = 0.0
        current_operation = 'Unknown'
        
        if self.state == 'draft':
            progress_percentage = 0.0
            current_operation = 'Waiting to start'
        elif self.state == 'processing':
            # Calculate progress based on execution time and estimated total
            if self.start_time:
                elapsed = (fields.Datetime.now() - self.start_time).total_seconds()
                
                # Estimate progress based on contacts found vs typical processing rate
                if self.contacts_found > 0:
                    # Assume ~100 contacts per second processing rate
                    estimated_total_time = self.contacts_found / 100.0
                    progress_percentage = min(95.0, (elapsed / estimated_total_time) * 100)
                    estimated_remaining = max(0, estimated_total_time - elapsed)
                else:
                    # Default progress for early stages
                    progress_percentage = min(90.0, (elapsed / 60.0) * 100)
                    estimated_remaining = max(0, 60 - elapsed)
                
                current_operation = 'Processing contacts...'
        elif self.state == 'completed':
            progress_percentage = 100.0
            current_operation = 'Completed successfully'
        elif self.state == 'failed':
            progress_percentage = 0.0  # Reset on failure
            current_operation = 'Failed'
        elif self.state == 'rolled_back':
            progress_percentage = 0.0
            current_operation = 'Rolled back'
        
        return {
            'batch_id': self.batch_id,
            'state': self.state,
            'progress_percentage': round(progress_percentage, 1),
            'current_operation': current_operation,
            'estimated_remaining_seconds': round(estimated_remaining, 0),
            'statistics': {
                'contacts_found': self.contacts_found,
                'contacts_added': self.contacts_added,
                'execution_time': self.execution_time,
            },
            'timestamps': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'current_time': fields.Datetime.now().isoformat(),
            },
            'error_message': self.error_message,
        }
    
    @api.model
    def validate_web_request(self, request_data):
        """
        Validate incoming web requests for batch operations.
        
        Args:
            request_data (dict): Request data from web interface
            
        Returns:
            dict: Validation results with errors if any
        """
        errors = []
        warnings = []
        
        # Validate mailing list
        mailing_list_id = request_data.get('mailing_list_id')
        if not mailing_list_id:
            errors.append('Mailing list is required')
        else:
            mailing_list = self.env['mailing.list'].browse(mailing_list_id)
            if not mailing_list.exists():
                errors.append('Mailing list not found')
            else:
                # Check permissions
                try:
                    mailing_list.check_access_rights('write')
                    mailing_list.check_access_rule('write')
                except Exception:
                    errors.append('You do not have permission to modify this mailing list')
        
        # Validate source models
        source_models = request_data.get('source_models', [])
        if not source_models:
            errors.append('At least one source model must be selected')
        else:
            registry_model = self.env['mailing.source.registry']
            for source_config in source_models:
                model_name = source_config.get('model_name')
                if not model_name:
                    errors.append('Source model name is required')
                    continue
                
                # Check if model is registered
                registry_entry = registry_model.search([
                    ('model_name', '=', model_name),
                    ('is_active', '=', True),
                    ('company_id', 'in', [self.env.company.id, False])
                ], limit=1)
                
                if not registry_entry:
                    errors.append(f'Source model {model_name} is not registered or inactive')
                    continue
                
                # Validate model access
                if not registry_entry.validate_model_access():
                    errors.append(f'You do not have access to source model {model_name}')
        
        # Validate filter criteria
        filter_criteria = request_data.get('filter_criteria', {})
        if isinstance(filter_criteria, dict):
            # Validate date ranges
            quick_filters = filter_criteria.get('quick_filters', {})
            if isinstance(quick_filters, dict):
                date_range = quick_filters.get('date_range', {})
                if isinstance(date_range, dict):
                    date_from = date_range.get('from')
                    date_to = date_range.get('to')
                    
                    if date_from and date_to:
                        try:
                            from_date = fields.Datetime.from_string(date_from)
                            to_date = fields.Datetime.from_string(date_to)
                            
                            if from_date > to_date:
                                errors.append('Start date must be before end date')
                            
                            # Warn about very large date ranges
                            if (to_date - from_date).days > 365 * 2:
                                warnings.append('Large date range may result in many contacts')
                                
                        except (ValueError, TypeError):
                            errors.append('Invalid date format in date range')
        
        # Validate batch configuration
        batch_config = request_data.get('batch_config', {})
        if isinstance(batch_config, dict):
            batch_size = batch_config.get('batch_size', 1000)
            if not isinstance(batch_size, int) or batch_size <= 0:
                errors.append('Batch size must be a positive integer')
            elif batch_size > 10000:
                warnings.append('Large batch size may impact performance')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'validated_data': {
                'mailing_list_id': mailing_list_id,
                'source_models': source_models,
                'filter_criteria': filter_criteria,
            } if len(errors) == 0 else None
        }
    
    @api.model
    def create_from_web_request(self, validated_data):
        """
        Create a new batch from validated web request data.
        
        Args:
            validated_data (dict): Pre-validated request data
            
        Returns:
            mailing.list.update.batch: Created batch record
        """
        # Generate batch with web-specific defaults
        vals = {
            'mailing_list_id': validated_data['mailing_list_id'],
            'source_models': json.dumps(validated_data['source_models']),
            'filter_criteria': json.dumps(validated_data['filter_criteria']),
            'state': 'draft',
        }
        
        batch_record = self.create(vals)
        
        # Log web creation
        self.env['mailing.operation.audit'].log_operation(
            batch_id=batch_record.batch_id,
            operation_type='execution_started',
            details={
                'source': 'web_interface',
                'user_agent': self.env.context.get('user_agent'),
                'source_count': len(validated_data['source_models']),
            },
            mailing_list_id=validated_data['mailing_list_id']
        )
        
        return batch_record
    
    def execute_web_preview(self):
        """
        Execute preview specifically for web interface.
        
        Returns:
            dict: Web-formatted preview results
        """
        self.ensure_one()
        
        try:
            # Parse configuration
            source_configs = json.loads(self.source_models) if self.source_models else []
            filter_criteria = json.loads(self.filter_criteria) if self.filter_criteria else {}
            
            # Execute preview (using existing method)
            result = self.execute_update(source_configs, filter_criteria, preview_only=True)
            
            if result.get('success'):
                # Format for web response
                web_result = {
                    'success': True,
                    'preview_data': {
                        'total_found': result.get('total_found', 0),
                        'total_after_dedup': result.get('total_after_dedup', 0),
                        'deduplication_stats': result.get('deduplication_stats', {}),
                        'source_stats': result.get('source_stats', {}),
                        'sample_contacts': result.get('sample_contacts', [])[:50],  # Limit for web
                        'estimated_execution_time': self._estimate_execution_time(
                            result.get('total_after_dedup', 0)
                        ),
                    },
                    'batch_info': self.to_json_preview(),
                }
                
                # Log preview generation
                self.env['mailing.operation.audit'].log_operation(
                    batch_id=self.batch_id,
                    operation_type='preview_generated',
                    details={
                        'total_found': result.get('total_found', 0),
                        'total_after_dedup': result.get('total_after_dedup', 0),
                        'source': 'web_interface',
                    },
                    mailing_list_id=self.mailing_list_id.id
                )
                
                return web_result
            else:
                return {
                    'success': False,
                    'error': 'Preview generation failed',
                    'details': result
                }
                
        except Exception as e:
            _logger.error("Web preview failed for batch %s: %s", self.batch_id, str(e))
            return {
                'success': False,
                'error': str(e),
                'batch_id': self.batch_id
            }
    
    def _estimate_execution_time(self, contact_count):
        """
        Estimate execution time based on contact count.
        
        Args:
            contact_count (int): Number of contacts to process
            
        Returns:
            dict: Time estimates
        """
        # Base processing rate: ~100 contacts per second
        base_rate = 100.0
        
        # Adjust rate based on system load and complexity
        adjusted_rate = base_rate * 0.8  # Conservative estimate
        
        estimated_seconds = contact_count / adjusted_rate
        
        # Add overhead for deduplication and database operations
        overhead_seconds = min(30, contact_count * 0.01)  # Max 30s overhead
        total_seconds = estimated_seconds + overhead_seconds
        
        return {
            'total_seconds': round(total_seconds, 0),
            'display_time': self._format_duration(total_seconds),
            'contact_count': contact_count,
            'processing_rate': f"~{int(adjusted_rate)} contacts/second",
        }
    
    def _format_duration(self, seconds):
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            remaining_seconds = int(seconds % 60)
            return f"{minutes}m {remaining_seconds}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"