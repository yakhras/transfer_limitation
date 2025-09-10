# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)


class MailingContact(models.Model):
    """
    Extension of the standard mailing.contact model to support batch tracking
    and source information for the mailing list updater functionality.
    """
    
    _inherit = 'mailing.contact'
    
    # Batch Tracking Fields
    batch_ids = fields.Many2many(
        'mailing.list.update.batch',
        'mailing_contact_batch_rel',
        'contact_id',
        'batch_id',
        string='Associated Batches',
        readonly=True,
        help='All batches that have added or modified this contact'
    )
    
    last_batch_id = fields.Char(
        string='Last Batch ID',
        readonly=True,
        index=True,
        help='ID of the most recent batch that added or modified this contact'
    )
    
    # Source Information Fields
    source_model = fields.Selection([
        ('res.partner', 'Contact'),
        ('crm.lead', 'CRM Lead'),
        ('hr.employee', 'Employee'),
        ('event.registration', 'Event Registration'),
        ('manual', 'Manual Entry'),
    ], string='Source Model', index=True,
       help='The Odoo model where this contact originated from')
    
    source_record_id = fields.Integer(
        string='Source Record ID',
        index=True,
        help='ID of the source record in the originating model'
    )
    
    # Import Metadata
    is_auto_added = fields.Boolean(
        string='Auto Added',
        default=False,
        index=True,
        help='Whether this contact was automatically added via batch operations'
    )
    
    import_date = fields.Datetime(
        string='Import Date',
        readonly=True,
        help='When this contact was first imported via batch operations'
    )
    
    last_sync_date = fields.Datetime(
        string='Last Sync Date',
        readonly=True,
        help='When this contact was last synchronized with its source'
    )
    
    # Tracking Relationships
    tracking_ids = fields.One2many(
        'mailing.contact.tracking',
        'mailing_contact_id',
        string='Tracking Records',
        readonly=True,
        help='Detailed tracking records for this contact'
    )
    
    # Computed Fields
    batch_count = fields.Integer(
        string='Batch Count',
        compute='_compute_batch_count',
        store=True,
        help='Number of batches associated with this contact'
    )
    
    source_record_exists = fields.Boolean(
        string='Source Record Exists',
        compute='_compute_source_record_exists',
        help='Whether the source record still exists'
    )
    
    can_sync_from_source = fields.Boolean(
        string='Can Sync from Source',
        compute='_compute_can_sync_from_source',
        help='Whether this contact can be synchronized with its source'
    )
    
    @api.depends('batch_ids')
    def _compute_batch_count(self):
        """Compute the number of associated batches."""
        for record in self:
            record.batch_count = len(record.batch_ids)
    
    @api.depends('source_model', 'source_record_id')
    def _compute_source_record_exists(self):
        """Check if the source record still exists."""
        for record in self:
            if record.source_model and record.source_record_id:
                try:
                    source_model = self.env[record.source_model]
                    source_record = source_model.browse(record.source_record_id)
                    record.source_record_exists = source_record.exists()
                except (KeyError, ValueError):
                    record.source_record_exists = False
            else:
                record.source_record_exists = False
    
    @api.depends('source_record_exists', 'source_model')
    def _compute_can_sync_from_source(self):
        """Determine if contact can be synchronized with source."""
        for record in self:
            record.can_sync_from_source = (
                record.source_record_exists and 
                record.source_model and 
                record.source_model != 'manual'
            )
    
    @api.constrains('source_record_id')
    def _check_source_record_id(self):
        """Validate source record ID is positive when set."""
        for record in self:
            if record.source_record_id and record.source_record_id <= 0:
                raise ValidationError(
                    _("Source record ID must be positive.")
                )
    
    @api.model
    def create(self, vals):
        """Override create to set import metadata for auto-added contacts."""
        if vals.get('is_auto_added') and not vals.get('import_date'):
            vals['import_date'] = fields.Datetime.now()
        
        return super(MailingContact, self).create(vals)
    
    def write(self, vals):
        """Override write to update sync date when syncing from source."""
        # If this is a sync operation from source, update sync date
        if any(key in vals for key in ['email', 'name']) and self.source_model:
            vals['last_sync_date'] = fields.Datetime.now()
        
        return super(MailingContact, self).write(vals)
    
    # Batch Management Methods
    
    def add_to_batch(self, batch_record):
        """
        Associate this contact with a batch.
        
        Args:
            batch_record (recordset): mailing.list.update.batch record
        """
        self.ensure_one()
        
        if batch_record not in self.batch_ids:
            self.write({
                'batch_ids': [(4, batch_record.id)],
                'last_batch_id': batch_record.batch_id,
            })
            
            _logger.debug(
                "Added contact %s to batch %s", 
                self.email, batch_record.batch_id
            )
    
    def remove_from_batch(self, batch_record):
        """
        Remove association with a batch.
        
        Args:
            batch_record (recordset): mailing.list.update.batch record
        """
        self.ensure_one()
        
        if batch_record in self.batch_ids:
            self.write({
                'batch_ids': [(3, batch_record.id)],
            })
            
            # Update last_batch_id if this was the last batch
            remaining_batches = self.batch_ids
            if remaining_batches:
                latest_batch = remaining_batches.sorted('create_date', reverse=True)[0]
                self.last_batch_id = latest_batch.batch_id
            else:
                self.last_batch_id = False
            
            _logger.debug(
                "Removed contact %s from batch %s", 
                self.email, batch_record.batch_id
            )
    
    def get_batch_history(self):
        """
        Get the complete batch history for this contact.
        
        Returns:
            list: List of batch information
        """
        self.ensure_one()
        
        batch_info = []
        for batch in self.batch_ids.sorted('create_date', reverse=True):
            batch_info.append({
                'batch_id': batch.batch_id,
                'batch_display_name': batch.batch_display_name,
                'create_date': batch.create_date,
                'user': batch.user_id.name,
                'mailing_list': batch.mailing_list_id.name,
                'state': batch.state,
                'is_rolled_back': batch.is_rolled_back,
                'contacts_added': batch.contacts_added,
            })
        
        return batch_info
    
    # Source Synchronization Methods
    
    def sync_from_source(self, field_names=None):
        """
        Synchronize contact data with its source record.
        
        Args:
            field_names (list, optional): Specific fields to sync
            
        Returns:
            dict: Sync results
        """
        self.ensure_one()
        
        if not self.can_sync_from_source:
            return {
                'success': False,
                'error': 'Cannot sync: source record not available'
            }
        
        try:
            # Get registry entry for field mapping
            registry_entry = self.env['mailing.source.registry'].search([
                ('model_name', '=', self.source_model),
                ('is_active', '=', True)
            ], limit=1)
            
            if not registry_entry:
                return {
                    'success': False,
                    'error': 'Registry entry not found for source model'
                }
            
            # Get source record
            source_model = self.env[self.source_model]
            source_record = source_model.browse(self.source_record_id)
            
            if not source_record.exists():
                return {
                    'success': False,
                    'error': 'Source record no longer exists'
                }
            
            # Get field mapping
            field_mapping = registry_entry.get_field_mapping()
            
            # Prepare update values
            update_vals = {}
            fields_to_sync = field_names or ['email', 'name']
            
            for field in fields_to_sync:
                if field == 'email' and field_mapping.get('email_field'):
                    new_email = getattr(source_record, field_mapping['email_field'], None)
                    if new_email and new_email != self.email:
                        update_vals['email'] = new_email
                
                elif field == 'name' and field_mapping.get('name_field'):
                    new_name = getattr(source_record, field_mapping['name_field'], None)
                    if new_name and new_name != self.name:
                        update_vals['name'] = new_name
            
            # Apply updates
            if update_vals:
                self.write(update_vals)
                
                _logger.info(
                    "Synchronized contact %s with source %s:%s - updated fields: %s",
                    self.id, self.source_model, self.source_record_id, 
                    list(update_vals.keys())
                )
                
                return {
                    'success': True,
                    'fields_updated': list(update_vals.keys()),
                    'changes': update_vals
                }
            else:
                return {
                    'success': True,
                    'message': 'No changes needed'
                }
        
        except Exception as e:
            _logger.error(
                "Error syncing contact %s with source: %s", 
                self.id, str(e)
            )
            return {
                'success': False,
                'error': str(e)
            }
    
    @api.model
    def bulk_sync_from_source(self, contact_ids=None, batch_size=100):
        """
        Bulk synchronize multiple contacts with their sources.
        
        Args:
            contact_ids (list, optional): Specific contact IDs to sync
            batch_size (int): Number of contacts to process per batch
            
        Returns:
            dict: Bulk sync results
        """
        domain = [('can_sync_from_source', '=', True)]
        if contact_ids:
            domain.append(('id', 'in', contact_ids))
        
        contacts = self.search(domain)
        
        total_contacts = len(contacts)
        processed = 0
        updated = 0
        errors = 0
        
        # Process in batches
        for i in range(0, total_contacts, batch_size):
            batch_contacts = contacts[i:i + batch_size]
            
            for contact in batch_contacts:
                try:
                    result = contact.sync_from_source()
                    processed += 1
                    
                    if result.get('success') and result.get('fields_updated'):
                        updated += 1
                
                except Exception as e:
                    _logger.error(
                        "Error in bulk sync for contact %s: %s", 
                        contact.id, str(e)
                    )
                    errors += 1
            
            # Commit batch to avoid memory issues
            self.env.cr.commit()
        
        _logger.info(
            "Bulk sync completed: %d processed, %d updated, %d errors", 
            processed, updated, errors
        )
        
        return {
            'total_contacts': total_contacts,
            'processed': processed,
            'updated': updated,
            'errors': errors,
            'success_rate': processed / max(total_contacts, 1)
        }
    
    def get_source_record(self):
        """
        Get the source record for this contact.
        
        Returns:
            recordset: Source record or False if not found
        """
        self.ensure_one()
        
        if not self.source_model or not self.source_record_id:
            return False
        
        try:
            source_model = self.env[self.source_model]
            return source_model.browse(self.source_record_id)
        except (KeyError, ValueError):
            return False
    
    def get_contact_summary(self):
        """
        Get comprehensive summary information for this contact.
        
        Returns:
            dict: Contact summary
        """
        self.ensure_one()
        
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'is_auto_added': self.is_auto_added,
            'source_info': {
                'model': self.source_model,
                'record_id': self.source_record_id,
                'exists': self.source_record_exists,
                'can_sync': self.can_sync_from_source,
            },
            'batch_info': {
                'count': self.batch_count,
                'last_batch_id': self.last_batch_id,
                'history': self.get_batch_history(),
            },
            'dates': {
                'create_date': self.create_date,
                'import_date': self.import_date,
                'last_sync_date': self.last_sync_date,
            },
            'lists': [list_rec.name for list_rec in self.list_ids],
            'tracking_records': len(self.tracking_ids),
        }
    
    @api.model
    def cleanup_orphaned_contacts(self, days_old=90):
        """
        Clean up auto-added contacts that have become orphaned.
        
        Args:
            days_old (int): Only consider contacts older than this many days
            
        Returns:
            int: Number of contacts cleaned up
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=days_old)
        
        # Find auto-added contacts with no source or rolled-back batches
        orphaned_contacts = self.search([
            ('is_auto_added', '=', True),
            ('create_date', '<=', cutoff_date),
            '|',
            ('source_record_exists', '=', False),
            ('batch_ids.is_rolled_back', '=', True),
        ])
        
        # Filter out contacts that are still in active batches
        contacts_to_cleanup = self.browse()
        for contact in orphaned_contacts:
            active_batches = contact.batch_ids.filtered(lambda b: not b.is_rolled_back)
            if not active_batches:
                contacts_to_cleanup |= contact
        
        count = len(contacts_to_cleanup)
        if count > 0:
            contacts_to_cleanup.unlink()
            _logger.info("Cleaned up %d orphaned auto-added contacts", count)
        
        return count