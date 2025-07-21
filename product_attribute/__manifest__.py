{
    'name': 'Product Attribute Removal',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Scheduled action to remove all attributes from product templates',
    'description': """
Product Attribute Removal Module
=================================

This module provides a scheduled action to automatically remove all attributes 
from product templates in your Odoo system.

Features:
---------
* Scheduled action to remove all product attributes
* Comprehensive logging and error handling
* Safe execution with progress tracking
* Configurable execution frequency
* Removes attribute lines, template attribute values, and excess variants

Usage:
------
1. Install the module
2. Go to Settings > Technical > Automation > Scheduled Actions
3. Find "Remove All Product Attributes" action
4. Activate and configure as needed

Warning:
--------
This action will remove ALL attributes from ALL product templates.
Make sure to backup your database before using this module.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
    ],
    'data': [
        'data/ir_cron_data.xml',
    ],
    
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 100,
    
    'external_dependencies': {
        'python': [],
    },
}