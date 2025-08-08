{
    'name': 'Mailing List Updater',
    'version': '15.0.1.0.0',
    'category': 'Marketing',
    'summary': 'Advanced mailing list update tool with dynamic filtering and multi-source support',
    'description': """
Mailing List Updater
====================

This module provides advanced functionality to update mailing lists by pulling contacts 
from multiple Odoo modules with sophisticated filtering, deduplication, and management capabilities.

Key Features:
* Dynamic contact source selection (Contacts, CRM)
* Advanced filtering with template saving
* Multi-phase deduplication algorithm
* Real-time preview with statistics
* 24-hour rollback capability
* Complete audit trail
* Batch processing for performance
* Plugin-based architecture for extensibility

Technical Features:
* Registry-based model system for scalability
* Company-scoped data isolation
* Performance optimization with batch processing
* Comprehensive error handling
* OWL 1.0 frontend components
* WebSocket real-time updates
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'mass_mailing',
        'contacts',
        'crm',
        'web',
        'bus',
    ],
    'data': [
        # Security
        'security/mailing_list_updater_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/registry_default_data.xml',
        'data/menu_items.xml',
        
        # Views
        # 'views/mailing_list_updater_views.xml',
        
    ],
    'assets': {
        'web.assets_backend': [
            'mailing_list_updater/static/src/css/*.css',
            'mailing_list_updater/static/src/js/*.js',
            
        ],
        'web.assets_qweb': [
            'mailing_list_updater/static/src/xml/*.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 100,
    'post_init_hook': '_post_init_setup_registry',
}