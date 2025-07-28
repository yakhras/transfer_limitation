# -*- coding: utf-8 -*-

import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class MailingSourceRegistry(models.Model):
    """
    Registry model for managing dynamic contact sources.
    
    This model serves as the central configuration hub for all contact sources
    that can be used to update mailing lists. It provides a plugin-based 
    architecture allowing new contact sources to be registered dynamically.
    """
    
    _name = 'mailing.source.registry'
    _description = 'Mailing List Contact Source Registry'
    _order = 'sequence, display_name'
    _rec_name = 'display_name'
    
    # Basic Information
    model_name = fields.Char(
        string='Model Name',
        required=True,
        index=True,
        help='Technical name of the Odoo model (e.g., res.partner, crm.lead)'
    )
    display_name = fields.Char(
        string='Display Name',
        required=True,
        help='Human-readable name shown in the UI (e.g., Contacts, CRM Leads)'
    )
    description = fields.Text(
        string='Description',
        help='Detailed description of this contact source'
    )
    
    # Field Mapping Configuration
    email_field = fields.Char(
        string='Email Field',
        required=True,
        default='email',
        help='Field name containing the email address (e.g., email, email_from, work_email)'
    )
    name_field = fields.Char(
        string='Name Field',
        required=True,
        default='name',
        help='Field name containing the contact name (e.g., name, display_name, full_name)'
    )
    phone_field = fields.Char(
        string='Phone Field',
        help='Field name containing the phone number (e.g., phone, mobile, work_phone)'
    )
    company_field = fields.Char(
        string='Company Field',
        default='company_id',
        help='Field name for company association (for multi-company support)'
    )
    active_field = fields.Char(
        string='Active Field',
        default='active',
        help='Field name to check if record is active'
    )
    
    # Filter Configuration
    filter_fields = fields.Text(
        string='Available Filter Fields',
        required=True,
        default='[]',
        help='JSON array of field names that can be used for filtering'
    )
    
    # Registry Management
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this source is available for selection'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=100,
        help='Order in which sources are displayed'
    )
    
    # Statistics and Metadata
    last_used_date = fields.Datetime(
        string='Last Used',
        readonly=True,
        help='When this source was last used for mailing list updates'
    )
    usage_count = fields.Integer(
        string='Usage Count',
        readonly=True,
        default=0,
        help='Number of times this source has been used'
    )
    
    # Company Support
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        index=True,
        help='Company-specific registry entries (leave empty for global)'
    )
    
    # SQL Constraints
    _sql_constraints = [
        ('unique_model_company', 
         'UNIQUE(model_name, company_id)', 
         'Each model can only be registered once per company.'),
        ('sequence_positive', 
         'CHECK(sequence >= 0)', 
         'Sequence must be positive.'),
    ]
    
    @api.constrains('model_name')
    def _check_model_exists(self):
        """Validate that the specified model exists in the system."""
        for record in self:
            if record.model_name:
                try:
                    self.env[record.model_name]
                except KeyError:
                    raise ValidationError(
                        _("Model '%s' does not exist in the system.") % record.model_name
                    )
    
    @api.constrains('filter_fields')
    def _check_filter_fields_json(self):
        """Validate that filter_fields contains valid JSON."""
        for record in self:
            if record.filter_fields:
                try:
                    json.loads(record.filter_fields)
                except (ValueError, TypeError):
                    raise ValidationError(
                        _("Filter fields must be a valid JSON array.")
                    )
    
    @api.constrains('email_field', 'name_field', 'phone_field', 'company_field', 'active_field')
    def _check_field_exists(self):
        """Validate that mapped fields exist in the target model."""
        for record in self:
            if not record.model_name:
                continue
                
            try:
                target_model = self.env[record.model_name]
                model_fields = target_model._fields
                
                # Check required fields
                for field_name, field_value in [
                    ('email_field', record.email_field),
                    ('name_field', record.name_field),
                ]:
                    if field_value and field_value not in model_fields:
                        raise ValidationError(
                            _("Field '%s' does not exist in model '%s'.") % 
                            (field_value, record.model_name)
                        )
                
                # Check optional fields
                for field_name, field_value in [
                    ('phone_field', record.phone_field),
                    ('company_field', record.company_field),  
                    ('active_field', record.active_field),
                ]:
                    if field_value and field_value not in model_fields:
                        raise ValidationError(
                            _("Field '%s' does not exist in model '%s'.") % 
                            (field_value, record.model_name)
                        )
                        
            except KeyError:
                # Model doesn't exist - will be caught by _check_model_exists
                pass
    
    # Core Registry Methods
    
    @api.model
    def get_active_sources(self, company_id=None):
        """
        Get all active contact sources available for the current company.
        
        Args:
            company_id (int, optional): Company ID to filter by
            
        Returns:
            list: List of dictionaries with source information
        """
        domain = [('is_active', '=', True)]
        
        if company_id:
            domain.append(('company_id', 'in', [company_id, False]))
        else:
            # Use current company if not specified
            company_id = self.env.company.id
            domain.append(('company_id', 'in', [company_id, False]))
        
        sources = self.search(domain)
        
        result = []
        for source in sources:
            result.append({
                'id': source.id,
                'model_name': source.model_name,
                'display_name': source.display_name,
                'description': source.description,
                'field_mapping': source.get_field_mapping(),
                'filter_fields': json.loads(source.filter_fields),
                'sequence': source.sequence,
                'usage_count': source.usage_count,
                'last_used_date': source.last_used_date,
            })
        
        return result
    
    def get_field_mapping(self):
        """
        Get the field mapping configuration for this source.
        
        Returns:
            dict: Field mapping configuration
        """
        self.ensure_one()
        
        return {
            'email_field': self.email_field,
            'name_field': self.name_field,
            'phone_field': self.phone_field,
            'company_field': self.company_field,
            'active_field': self.active_field,
        }
    
    def get_filter_fields(self):
        """
        Get the available filter fields for this source.
        
        Returns:
            list: List of field names available for filtering
        """
        self.ensure_one()
        
        try:
            return json.loads(self.filter_fields)
        except (ValueError, TypeError):
            _logger.warning(
                "Invalid JSON in filter_fields for registry ID %s", self.id
            )
            return []
    
    @api.model
    def register_model(self, model_name, display_name, email_field='email', 
                      name_field='name', phone_field=None, filter_fields=None,
                      company_id=None, **kwargs):
        """
        Register a new contact source model.
        
        Args:
            model_name (str): Technical model name
            display_name (str): Human-readable name
            email_field (str): Email field name
            name_field (str): Name field name  
            phone_field (str, optional): Phone field name
            filter_fields (list, optional): Available filter fields
            company_id (int, optional): Company ID
            **kwargs: Additional field values
            
        Returns:
            mailing.source.registry: Created registry record
        """
        if filter_fields is None:
            filter_fields = ['create_date', 'write_date']
        
        # Check if model is already registered
        domain = [('model_name', '=', model_name)]
        if company_id:
            domain.append(('company_id', '=', company_id))
        else:
            domain.append(('company_id', '=', False))
            
        existing = self.search(domain)
        if existing:
            raise UserError(
                _("Model '%s' is already registered for this company.") % model_name
            )
        
        # Prepare values
        values = {
            'model_name': model_name,
            'display_name': display_name,
            'email_field': email_field,
            'name_field': name_field,
            'filter_fields': json.dumps(filter_fields),
            'company_id': company_id,
        }
        
        if phone_field:
            values['phone_field'] = phone_field
            
        # Add any additional values
        values.update(kwargs)
        
        # Create registry entry
        registry_entry = self.create(values)
        
        _logger.info(
            "Successfully registered model '%s' as contact source '%s'", 
            model_name, display_name
        )
        
        return registry_entry
    
    def unregister_model(self):
        """
        Unregister this contact source.
        
        This method checks for dependencies before allowing unregistration.
        """
        self.ensure_one()
        
        # Check if source is being used in any active batches
        active_batches = self.env['mailing.list.update.batch'].search([
            ('source_models', 'like', '"%s"' % self.model_name),
            ('is_rolled_back', '=', False),
        ])
        
        if active_batches:
            raise UserError(
                _("Cannot unregister source '%s' because it's used in %d active batch(es).") %
                (self.display_name, len(active_batches))
            )
        
        # Deactivate instead of delete to preserve audit trail
        self.write({'is_active': False})
        
        _logger.info(
            "Deactivated contact source '%s' (model: %s)", 
            self.display_name, self.model_name
        )
    
    def update_usage_stats(self):
        """Update usage statistics when this source is used."""
        self.ensure_one()
        
        self.write({
            'usage_count': self.usage_count + 1,
            'last_used_date': fields.Datetime.now(),
        })
    
    def validate_model_access(self, user_id=None):
        """
        Validate that the current user has access to the registered model.
        
        Args:
            user_id (int, optional): User ID to check (defaults to current user)
            
        Returns:
            bool: True if user has access
        """
        self.ensure_one()
        
        if not user_id:
            user_id = self.env.user.id
        
        try:
            # Try to access the model with current user context
            model = self.env[self.model_name].with_user(user_id)
            model.check_access_rights('read')
            return True
        except Exception as e:
            _logger.warning(
                "User %s does not have access to model %s: %s", 
                user_id, self.model_name, str(e)
            )
            return False
    
    @api.model
    def get_model_info(self, model_name):
        """
        Get detailed information about a registered model.
        
        Args:
            model_name (str): Model name to get info for
            
        Returns:
            dict: Model information or None if not found
        """
        registry_entry = self.search([
            ('model_name', '=', model_name),
            ('is_active', '=', True)
        ], limit=1)
        
        if not registry_entry:
            return None
        
        return {
            'id': registry_entry.id,
            'model_name': registry_entry.model_name,
            'display_name': registry_entry.display_name,
            'description': registry_entry.description,
            'field_mapping': registry_entry.get_field_mapping(),
            'filter_fields': registry_entry.get_filter_fields(),
            'usage_count': registry_entry.usage_count,
            'last_used_date': registry_entry.last_used_date,
        }