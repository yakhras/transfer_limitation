{
    'name': 'Product Attribute Removal',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Scheduled action and wizard to remove attributes from product templates',
    'description': """
Product Attribute Removal Module
=================================

This module provides both scheduled actions and a user-friendly wizard to remove 
attributes from product templates in your Odoo system.

Features:
---------
* Web-based wizard with preview functionality
* Scheduled action for automated cleanup
* Category-based attribute removal
* Comprehensive HTML reports
* Downloadable execution reports
* Real-time progress tracking

Usage:
------
1. Install the module
2. Go to Inventory > Attribute Cleanup
3. Enter category name and preview results
4. Execute cleanup and download reports

Warning:
--------
This action will remove ALL attributes from products in the selected category.
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
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/attribute_cleanup_wizard_views.xml',
        'views/attribute_assignment_wizard_views.xml',
    ],
    'demo': [
        'demo/product_template_demo.csv',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'sequence': 100,
    'images': [
        'static/description/icon.png',
    ],
    'external_dependencies': {
        'python': [],
    },
}