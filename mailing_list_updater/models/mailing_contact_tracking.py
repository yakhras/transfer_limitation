# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)


class MailingContactTracking(models.Model):
    """
    Model for tracking individual contacts added through batch operations.
    
    This model maintains the relationship between mailing contacts and the
    batch operations that created them, enabling precise rollback capabilities
    and detailed audit trails.
    """
    
    _name = 'mailing.contact.tracking'
    _description = 'Mailing Contact Batch Tracking'
    _order = 'create_date desc'
    _rec_name = 'display_name'
    
    # Core Relationships
    batch_id = fields.Char(
        string='Batch ID',
        required=True,
        index=True,
        help='Reference to the batch that created this contact'
    )
    mailing_contact_id = fields.Many2one(
        'mailing.contact',
        string='Mailing Contact',
        required=True,
        index=True,
        ondelete='cascade',
        help='The mailing contact record that was created'
    )
    
    # Source Information
    source_model = fields.Selection([
        ('res.partner', 'Contact'),
        ('crm.lead', 'CRM Lead'),
        ('hr.employee', 'Employee'),
        ('event.registration', 'Event Registration'),
    ], string='Source Model', required=True, index=True,
       help='The Odoo model where this contact originated from')
    
    source_record_id = fields.Integer(
        string='Source Record ID',
        required=True,
        index=True,
        help='ID of the source record in the originating model'
    )
    
    # Contact Data Snapshot
    original_email = fields.Char(
        string='Original Email',
        required=True,
        index=True,
        help='Email address at the time of import (for audit purposes)'
    )
    original_name = fields.Char(
        string='Original Name',
        help='Name at the time of import'
    )
    original_phone = fields.Char(
        string='Original Phone',
        help='Phone number at the time of import'
    )
    
    # Batch Reference Information
    batch_record_id = fields.Many2one(
        'mailing.list.update.batch',
        string='Batch Record',
        compute='_compute_batch_record',
        store=True,
        help='Reference to the batch record'
    )
    mailing_list_ids = fields.Many2many(
        'mailing.list',
        string='Mailing Lists',
        related='mailing_contact_id.list_ids',
        readonly=True,
        help='The mailing lists this contact belongs to'
    )
    
    # Metadata
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help='Company context for this tracking record'
    )
    
    # Display Fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Human-readable identifier for this tracking record'
    )
    
    # Status Fields
    is_active = fields.Boolean(
        string='Contact Active',
        related='mailing_contact_id.opt_out',
        store=False,
        help='Whether the mailing contact is still active'
    )
    
    # SQL Constraints
    _sql_constraints = [
        ('unique_contact_batch', 
         'UNIQUE(mailing_contact_id, batch_id)', 
         'A contact can only be tracked once per batch.'),
        ('source_record_id_positive', 
         'CHECK(source_record_id > 0)', 
         'Source record ID must be positive.'),
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
    
    @api.depends('original_email', 'original_name', 'source_model', 'batch_id')
    def _compute_display_name(self):
        """Compute human-readable display name."""
        for record in self:
            name_parts = []
            
            if record.original_name:
                name_parts.append(record.original_name)
            elif record.original_email:
                name_parts.append(record.original_email)
            
            if record.source_model:
                source_display = dict(record._fields['source_model'].selection).get(
                    record.source_model, record.source_model
                )
                name_parts.append(f"({source_display})")
            
            record.display_name = ' '.join(name_parts) or 'Contact Tracking'
    
    @api.constrains('original_email')
    def _check_email_format(self):
        """Validate email format."""
        for record in self:
            if record.original_email:
                # Basic email validation
                if '@' not in record.original_email or '.' not in record.original_email:
                    raise ValidationError(
                        _("Invalid email format: %s") % record.original_email
                    )
    
    # Business Methods
    
    def link_to_batch(self, batch_id, mailing_contact, source_data):
        """
        Create tracking link between a contact and batch.
        
        Args:
            batch_id (str): Batch identifier
            mailing_contact (recordset): mailing.contact record
            source_data (dict): Original source data
            
        Returns:
            mailing.contact.tracking: Created tracking record
        """
        vals = {
            'batch_id': batch_id,
            'mailing_contact_id': mailing_contact.id,
            'source_model': source_data.get('source_model'),
            'source_record_id': source_data.get('source_record_id'),
            'original_email': source_data.get('email'),
            'original_name': source_data.get('name'),
            'original_phone': source_data.get('phone'),
            'company_id': mailing_contact.company_id.id or self.env.company.id,
        }
        
        tracking_record = self.create(vals)
        
        _logger.info(
            "Created tracking record for contact %s in batch %s", 
            mailing_contact.email, batch_id
        )
        
        return tracking_record
    
    @api.model
    def get_batch_contacts(self, batch_id, company_id=None):
        """
        Get all contacts associated with a specific batch.
        
        Args:
            batch_id (str): Batch identifier
            company_id (int, optional): Company filter
            
        Returns:
            list: List of contact tracking records
        """
        domain = [('batch_id', '=', batch_id)]
        
        if company_id:
            domain.append(('company_id', '=', company_id))
        
        tracking_records = self.search(domain)
        
        result = []
        for record in tracking_records:
            # Get the target mailing list from the batch record
            target_list = None
            if record.batch_record_id and record.batch_record_id.mailing_list_id:
                target_list = record.batch_record_id.mailing_list_id.name
            
            result.append({
                'id': record.id,
                'mailing_contact_id': record.mailing_contact_id.id,
                'email': record.original_email,
                'name': record.original_name,
                'phone': record.original_phone,
                'source_model': record.source_model,
                'source_record_id': record.source_record_id,
                'create_date': record.create_date,
                'target_mailing_list': target_list,
                'is_active': not record.mailing_contact_id.opt_out if record.mailing_contact_id else False,
            })
        
        return result
    
    def track_source_changes(self):
        """
        Track changes in the source record since import.
        
        Returns:
            dict: Changes detected in source record
        """
        self.ensure_one()
        
        if not self.source_model or not self.source_record_id:
            return {'error': 'No source information available'}
        
        try:
            # Get current source record
            source_model = self.env[self.source_model]
            source_record = source_model.browse(self.source_record_id)
            
            if not source_record.exists():
                return {
                    'status': 'deleted',
                    'message': 'Source record has been deleted'
                }
            
            # Get registry entry for field mapping
            registry_entry = self.env['mailing.source.registry'].search([
                ('model_name', '=', self.source_model),
                ('is_active', '=', True)
            ], limit=1)
            
            if not registry_entry:
                return {'error': 'Registry entry not found for source model'}
            
            field_mapping = registry_entry.get_field_mapping()
            changes = {}
            
            # Check email changes
            current_email = getattr(source_record, field_mapping['email_field'], None)
            if current_email != self.original_email:
                changes['email'] = {
                    'original': self.original_email,
                    'current': current_email
                }
            
            # Check name changes
            current_name = getattr(source_record, field_mapping['name_field'], None)
            if current_name != self.original_name:
                changes['name'] = {
                    'original': self.original_name,
                    'current': current_name
                }
            
            # Check phone changes
            if field_mapping.get('phone_field'):
                current_phone = getattr(source_record, field_mapping['phone_field'], None)
                if current_phone != self.original_phone:
                    changes['phone'] = {
                        'original': self.original_phone,
                        'current': current_phone
                    }
            
            return {
                'status': 'active',
                'changes': changes,
                'has_changes': bool(changes)
            }
            
        except Exception as e:
            _logger.error(
                "Error tracking source changes for tracking ID %s: %s", 
                self.id, str(e)
            )
            return {'error': str(e)}
    
    def update_from_source(self, field_names=None):
        """
        Update mailing contact with current data from source.
        
        Args:
            field_names (list, optional): Specific fields to update
            
        Returns:
            dict: Update results
        """
        self.ensure_one()
        
        if not self.mailing_contact_id or not self.mailing_contact_id.exists():
            return {'error': 'Mailing contact no longer exists'}
        
        source_changes = self.track_source_changes()
        
        if source_changes.get('status') != 'active':
            return source_changes
        
        changes = source_changes.get('changes', {})
        if not changes:
            return {'status': 'no_changes', 'message': 'No changes detected'}
        
        # Apply updates to mailing contact
        update_vals = {}
        fields_to_update = field_names or changes.keys()
        
        for field in fields_to_update:
            if field in changes:
                if field == 'email':
                    update_vals['email'] = changes[field]['current']
                elif field == 'name':
                    update_vals['name'] = changes[field]['current']
                # Phone is not directly stored in mailing.contact
        
        if update_vals:
            self.mailing_contact_id.write(update_vals)
            
            _logger.info(
                "Updated mailing contact %s from source changes: %s", 
                self.mailing_contact_id.id, list(update_vals.keys())
            )
        
        return {
            'status': 'updated',
            'fields_updated': list(update_vals.keys()),
            'changes_applied': len(update_vals)
        }
    
    @api.model
    def cleanup_orphaned_tracking(self, days_old=30):
        """
        Clean up tracking records for deleted mailing contacts.
        
        Args:
            days_old (int): Only clean records older than this many days
            
        Returns:
            int: Number of records cleaned up
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=days_old)
        
        # Find tracking records with deleted mailing contacts
        orphaned_records = self.search([
            ('create_date', '<=', cutoff_date),
            ('mailing_contact_id', '=', False)
        ])
        
        count = len(orphaned_records)
        if count > 0:
            orphaned_records.unlink()
            _logger.info("Cleaned up %d orphaned tracking records", count)
        
        return count
    
    def get_contact_history(self):
        """
        Get the complete history for this tracked contact.
        
        Returns:
            dict: Contact history information
        """
        self.ensure_one()
        
        # Get all tracking records for the same source
        related_tracking = self.search([
            ('source_model', '=', self.source_model),
            ('source_record_id', '=', self.source_record_id),
            ('company_id', '=', self.company_id.id)
        ])
        
        # Get batch information
        batch_info = []
        for tracking in related_tracking:
            if tracking.batch_record_id:
                batch_info.append({
                    'batch_id': tracking.batch_id,
                    'create_date': tracking.create_date,
                    'mailing_list': tracking.batch_record_id.mailing_list_id.name if tracking.batch_record_id.mailing_list_id else 'Unknown',
                    'is_current': tracking.id == self.id,
                })
        
        # Get current source status
        source_status = self.track_source_changes()
        
        return {
            'source_model': self.source_model,
            'source_record_id': self.source_record_id,
            'original_data': {
                'email': self.original_email,
                'name': self.original_name,
                'phone': self.original_phone,
            },
            'batch_history': sorted(batch_info, key=lambda x: x['create_date'], reverse=True),
            'source_status': source_status,
            'total_imports': len(related_tracking),
        }