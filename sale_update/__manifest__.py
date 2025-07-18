# -*- coding: utf-8 -*-
{
    'name': 'Sales Order to Quotation Converter',
    'version': '16.0.1.0.0',
    'category': 'Sales',
    'summary': 'Convert Sales Orders to Quotations with PO Management',
    'description': """
        This module provides functionality to convert confirmed sales orders back to quotations
        with automatic purchase order cancellation and deletion. Includes comprehensive field tracking.
    """,
    'author': 'Your Company',
    'depends': ['sale', 'purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/conversion_log_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}