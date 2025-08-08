# -*- coding: utf-8 -*-

from . import models
from . import controllers
# from . import wizards      # Phase 4

def _post_init_setup_registry(cr, registry):
    """
    Post-installation hook to set up default registry entries
    for Contact and CRM modules.
    """
    from odoo import api, SUPERUSER_ID
    
    try:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # Check if registry model exists and is ready
        if 'mailing.source.registry' not in env:
            return
            
        registry_model = env['mailing.source.registry']
        
        # Check if res.partner is already registered
        if not registry_model.search([('model_name', '=', 'res.partner')], limit=1):
            registry_model.create({
                'model_name': 'res.partner',
                'display_name': 'Contacts',
                'email_field': 'email',
                'name_field': 'name',
                'phone_field': 'phone',
                'company_field': 'company_id',
                'active_field': 'active',
                'filter_fields': '["create_date", "user_id", "category_id", "country_id", "is_company", "supplier_rank", "customer_rank"]',
                'is_active': True,
                'sequence': 10,
            })
        
        # Check if crm.lead is already registered
        if not registry_model.search([('model_name', '=', 'crm.lead')], limit=1):
            registry_model.create({
                'model_name': 'crm.lead',
                'display_name': 'CRM Leads',
                'email_field': 'email_from',
                'name_field': 'name',
                'phone_field': 'phone',
                'company_field': 'company_id',
                'active_field': 'active',
                'filter_fields': '["create_date", "user_id", "stage_id", "team_id", "country_id", "probability", "expected_revenue"]',
                'is_active': True,
                'sequence': 20,
            })
            
    except Exception as e:
        # Log error but don't fail installation
        import logging
        _logger = logging.getLogger(__name__)
        _logger.warning("Failed to setup registry during post-install: %s", str(e))