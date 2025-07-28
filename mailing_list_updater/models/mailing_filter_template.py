# -*- coding: utf-8 -*-

import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, AccessError
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class MailingFilterTemplate(models.Model):
    """
    Model for saving and managing filter configurations.
    
    This model allows users to save complex filter configurations as templates
    that can be reused for future mailing list updates. Templates can be
    private (user-specific) or public (shared with other users).
    """
    
    _name = 'mailing.filter.template'
    _description = 'Mailing List Filter Template'
    _order = 'name, create_date desc'
    _rec_name = 'name'
    
    # Template Information
    name = fields.Char(
        string='Template Name',
        required=True,
        index=True,
        help='Descriptive name for this filter template'
    )
    description = fields.Text(
        string='Description',
        help='Detailed description of what this template does'
    )
    
    # Template Configuration
    source_models = fields.Text(
        string='Source Models',
        required=True,
        help='JSON array of source model configurations'
    )
    quick_filters = fields.Text(
        string='Quick Filters',
        help='JSON object containing quick filter settings (date range, salesperson, etc.)'
    )
    advanced_filters = fields.Text(
        string='Advanced Filters',
        help='JSON object containing advanced/dynamic filter rules'
    )
    
    # Template Metadata
    user_id = fields.Many2one(
        'res.users',
        string='Created By',
        required=True,
        index=True,
        default=lambda self: self.env.user,
        help='User who created this template'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
        help='Company this template belongs to'
    )
    
    # Sharing and Access
    is_public = fields.Boolean(
        string='Public Template',
        default=False,
        help='Whether this template is available to other users in the company'
    )
    shared_with_group_ids = fields.Many2many(
        'res.groups',
        string='Shared with Groups',
        help='Specific groups that can access this template'
    )
    
    # Usage Statistics
    usage_count = fields.Integer(
        string='Usage Count',
        readonly=True,
        default=0,
        help='Number of times this template has been used'
    )
    last_used_date = fields.Datetime(
        string='Last Used',
        readonly=True,
        help='When this template was last used'
    )
    
    # Template Status
    is_active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this template is available for use'
    )
    
    # Computed Fields
    source_model_names = fields.Char(
        string='Source Models',
        compute='_compute_source_model_names',
        store=True,
        help='Human-readable list of source models'
    )
    is_accessible = fields.Boolean(
        string='Accessible',
        compute='_compute_is_accessible',
        help='Whether current user can access this template'
    )
    
    # SQL Constraints
    _sql_constraints = [
        ('name_company_unique', 
         'UNIQUE(name, company_id, user_id)', 
         'Template names must be unique per user within a company.'),
        ('usage_count_positive', 
         'CHECK(usage_count >= 0)', 
         'Usage count must be positive.'),
    ]
    
    @api.depends('source_models')
    def _compute_source_model_names(self):
        """Compute human-readable source model names."""
        for record in self:
            try:
                source_configs = json.loads(record.source_models or '[]')
                registry_model = self.env['mailing.source.registry']
                
                model_names = []
                for config in source_configs:
                    model_name = config.get('model_name')
                    if model_name:
                        registry_entry = registry_model.search([
                            ('model_name', '=', model_name),
                            ('is_active', '=', True)
                        ], limit=1)
                        
                        display_name = registry_entry.display_name if registry_entry else model_name
                        model_names.append(display_name)
                
                record.source_model_names = ', '.join(model_names) if model_names else 'None'
                
            except (ValueError, TypeError):
                record.source_model_names = 'Invalid Configuration'
    
    @api.depends('is_public', 'user_id', 'shared_with_group_ids', 'is_active')
    def _compute_is_accessible(self):
        """Compute whether current user can access this template."""
        current_user = self.env.user
        
        for record in self:
            if not record.is_active:
                record.is_accessible = False
                continue
            
            # Template owner always has access
            if record.user_id == current_user:
                record.is_accessible = True
                continue
            
            # Public templates are accessible to company users
            if record.is_public and record.company_id == current_user.company_id:
                record.is_accessible = True
                continue
            
            # Check group sharing
            if record.shared_with_group_ids:
                user_groups = current_user.groups_id
                if any(group in user_groups for group in record.shared_with_group_ids):
                    record.is_accessible = True
                    continue
            
            record.is_accessible = False
    
    @api.constrains('source_models', 'quick_filters', 'advanced_filters')
    def _check_json_fields(self):
        """Validate that JSON fields contain valid JSON."""
        for record in self:
            json_fields = [
                ('source_models', record.source_models),
                ('quick_filters', record.quick_filters),
                ('advanced_filters', record.advanced_filters),
            ]
            
            for field_name, field_value in json_fields:
                if field_value:
                    try:
                        json.loads(field_value)
                    except (ValueError, TypeError):
                        raise ValidationError(
                            _("Field '%s' must contain valid JSON.") % field_name
                        )
    
    @api.constrains('source_models')
    def _check_source_models_exist(self):
        """Validate that referenced source models exist in registry."""
        for record in self:
            if not record.source_models:
                continue
            
            try:
                source_configs = json.loads(record.source_models)
                registry_model = self.env['mailing.source.registry']
                
                for config in source_configs:
                    model_name = config.get('model_name')
                    if model_name:
                        registry_entry = registry_model.search([
                            ('model_name', '=', model_name),
                            ('company_id', 'in', [record.company_id.id, False])
                        ], limit=1)
                        
                        if not registry_entry:
                            raise ValidationError(
                                _("Source model '%s' is not registered in the system.") % 
                                model_name
                            )
                            
            except (ValueError, TypeError):
                # JSON validation is handled by _check_json_fields
                pass
    
    # Template Management Methods
    
    @api.model
    def save_template(self, name, description, source_models, quick_filters=None, 
                     advanced_filters=None, is_public=False, **kwargs):
        """
        Save a new filter template.
        
        Args:
            name (str): Template name
            description (str): Template description
            source_models (list): Source model configurations
            quick_filters (dict, optional): Quick filter settings
            advanced_filters (dict, optional): Advanced filter rules
            is_public (bool): Whether template is public
            **kwargs: Additional field values
            
        Returns:
            mailing.filter.template: Created template record
        """
        # Validate template name uniqueness
        existing = self.search([
            ('name', '=', name),
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)
        ])
        
        if existing:
            raise UserError(_("A template with the name '%s' already exists.") % name)
        
        # Prepare values
        vals = {
            'name': name,
            'description': description,
            'source_models': json.dumps(source_models),
            'quick_filters': json.dumps(quick_filters or {}),
            'advanced_filters': json.dumps(advanced_filters or {}),
            'is_public': is_public,
        }
        
        # Add any additional values
        vals.update(kwargs)
        
        # Create template
        template = self.create(vals)
        
        _logger.info(
            "Created filter template '%s' for user %s (public: %s)", 
            name, self.env.user.name, is_public
        )
        
        return template
    
    def load_template(self):
        """
        Load template configuration.
        
        Returns:
            dict: Template configuration data
        """
        self.ensure_one()
        
        if not self.is_accessible:
            raise AccessError(_("You don't have access to this template."))
        
        try:
            # Parse JSON configurations
            source_models = json.loads(self.source_models or '[]')
            quick_filters = json.loads(self.quick_filters or '{}')
            advanced_filters = json.loads(self.advanced_filters or '{}')
            
            # Update usage statistics
            self.write({
                'usage_count': self.usage_count + 1,
                'last_used_date': fields.Datetime.now(),
            })
            
            return {
                'id': self.id,
                'name': self.name,
                'description': self.description,
                'source_models': source_models,
                'quick_filters': quick_filters,
                'advanced_filters': advanced_filters,
                'created_by': self.user_id.name,
                'is_public': self.is_public,
                'usage_count': self.usage_count,
            }
            
        except (ValueError, TypeError) as e:
            _logger.error("Error loading template %s: %s", self.name, str(e))
            raise UserError(_("Template configuration is corrupted and cannot be loaded."))
    
    def update_template(self, **kwargs):
        """
        Update template configuration.
        
        Args:
            **kwargs: Fields to update
            
        Returns:
            bool: Update success
        """
        self.ensure_one()
        
        # Check permissions
        if not self._check_write_access():
            raise AccessError(_("You don't have permission to modify this template."))
        
        # Prepare update values
        update_vals = {}
        
        for field, value in kwargs.items():
            if field in ['source_models', 'quick_filters', 'advanced_filters']:
                # Ensure JSON fields are properly encoded
                if isinstance(value, (dict, list)):
                    update_vals[field] = json.dumps(value)
                else:
                    update_vals[field] = value
            elif field in self._fields:
                update_vals[field] = value
        
        if update_vals:
            self.write(update_vals)
            
            _logger.info(
                "Updated template '%s' with fields: %s", 
                self.name, list(update_vals.keys())
            )
        
        return True
    
    def duplicate_template(self, new_name=None):
        """
        Create a copy of this template.
        
        Args:
            new_name (str, optional): Name for the new template
            
        Returns:
            mailing.filter.template: Duplicated template
        """
        self.ensure_one()
        
        if not self.is_accessible:
            raise AccessError(_("You don't have access to this template."))
        
        # Generate new name if not provided
        if not new_name:
            new_name = _("%s (Copy)") % self.name
            
            # Ensure uniqueness
            counter = 1
            while self.search([
                ('name', '=', new_name),
                ('user_id', '=', self.env.user.id),
                ('company_id', '=', self.env.company.id)
            ]):
                new_name = _("%s (Copy %d)") % (self.name, counter)
                counter += 1
        
        # Create duplicate
        duplicate = self.copy({
            'name': new_name,
            'user_id': self.env.user.id,
            'is_public': False,  # Duplicates are private by default
            'usage_count': 0,
            'last_used_date': False,
        })
        
        _logger.info(
            "Duplicated template '%s' as '%s' for user %s", 
            self.name, new_name, self.env.user.name
        )
        
        return duplicate
    
    @api.model
    def get_accessible_templates(self, company_id=None):
        """
        Get all templates accessible to the current user.
        
        Args:
            company_id (int, optional): Company filter
            
        Returns:
            list: List of accessible template data
        """
        if not company_id:
            company_id = self.env.company.id
        
        # Build domain for accessible templates
        domain = [
            ('is_active', '=', True),
            ('company_id', '=', company_id),
            '|', '|',
            ('user_id', '=', self.env.user.id),  # Own templates
            ('is_public', '=', True),  # Public templates
            ('shared_with_group_ids', 'in', self.env.user.groups_id.ids)  # Shared templates
        ]
        
        templates = self.search(domain)
        
        result = []
        for template in templates:
            result.append({
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'source_model_names': template.source_model_names,
                'created_by': template.user_id.name,
                'is_public': template.is_public,
                'is_owner': template.user_id == self.env.user,
                'usage_count': template.usage_count,
                'last_used_date': template.last_used_date,
                'create_date': template.create_date,
            })
        
        return sorted(result, key=lambda x: (x['is_owner'], x['usage_count']), reverse=True)
    
    def share_template(self, group_ids=None, make_public=False):
        """
        Share template with specific groups or make public.
        
        Args:
            group_ids (list, optional): Group IDs to share with
            make_public (bool): Whether to make template public
            
        Returns:
            bool: Sharing success
        """
        self.ensure_one()
        
        if not self._check_write_access():
            raise AccessError(_("You don't have permission to share this template."))
        
        update_vals = {}
        
        if make_public:
            update_vals['is_public'] = True
        
        if group_ids:
            update_vals['shared_with_group_ids'] = [(6, 0, group_ids)]
        
        if update_vals:
            self.write(update_vals)
            
            _logger.info(
                "Shared template '%s' (public: %s, groups: %s)", 
                self.name, make_public, group_ids
            )
        
        return True
    
    def unshare_template(self):
        """Make template private (remove all sharing)."""
        self.ensure_one()
        
        if not self._check_write_access():
            raise AccessError(_("You don't have permission to modify this template."))
        
        self.write({
            'is_public': False,
            'shared_with_group_ids': [(5, 0, 0)],  # Remove all group links
        })
        
        _logger.info("Made template '%s' private", self.name)
        
        return True
    
    @api.model
    def cleanup_unused_templates(self, days_unused=180):
        """
        Clean up old unused templates.
        
        Args:
            days_unused (int): Remove templates unused for this many days
            
        Returns:
            int: Number of templates cleaned up
        """
        cutoff_date = fields.Datetime.now() - timedelta(days=days_unused)
        
        # Find old unused templates (not public, not recently used)
        unused_templates = self.search([
            ('is_public', '=', False),
            ('usage_count', '=', 0),
            ('create_date', '<=', cutoff_date),
        ])
        
        count = len(unused_templates)
        if count > 0:
            unused_templates.unlink()
            _logger.info("Cleaned up %d unused filter templates", count)
        
        return count
    
    # Helper Methods
    
    def _check_write_access(self):
        """Check if current user can modify this template."""
        self.ensure_one()
        
        # Template owner can always modify
        if self.user_id == self.env.user:
            return True
        
        # Admin users can modify any template in their company
        if (self.env.user.has_group('base.group_system') and 
            self.company_id == self.env.user.company_id):
            return True
        
        return False
    
    def get_template_preview(self):
        """
        Get a preview of what the template will filter.
        
        Returns:
            dict: Template preview information
        """
        self.ensure_one()
        
        try:
            config = self.load_template()
            
            # Count potential matches per source
            source_counts = {}
            registry_model = self.env['mailing.source.registry']
            
            for source_config in config['source_models']:
                model_name = source_config.get('model_name')
                if not model_name:
                    continue
                
                registry_entry = registry_model.search([
                    ('model_name', '=', model_name),
                    ('is_active', '=', True)
                ], limit=1)
                
                if registry_entry:
                    # Simple count without applying filters
                    model = self.env[model_name]
                    count = model.search_count([
                        ('company_id', '=', self.company_id.id)
                    ])
                    
                    source_counts[registry_entry.display_name] = count
            
            return {
                'template_name': self.name,
                'source_counts': source_counts,
                'total_potential': sum(source_counts.values()),
                'has_quick_filters': bool(config['quick_filters']),
                'has_advanced_filters': bool(config['advanced_filters']),
                'note': 'Actual results may be lower after applying filters and deduplication'
            }
            
        except Exception as e:
            return {'error': str(e)}