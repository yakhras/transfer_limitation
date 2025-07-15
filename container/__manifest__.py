# -*- coding: utf-8 -*-
{
    'name': 'Container',
    'version': '15.0.1.0.0',
    'category': 'Logistics',
    'summary': 'Container Management and Tracking',
    'description': """
Container Management System
===========================

A comprehensive container tracking solution for logistics operations.

Key Features:
* Container lifecycle management from shipping to delivery
* Detailed container contents tracking
* Cost and financial management
* Status workflow with visual kanban boards
* Integration with purchase orders and suppliers
* Rich reporting and analytics

Perfect for companies managing shipping containers and need full visibility
into their logistics operations.
    """,
    'author': 'Yaser Akhras',
    'website': 'https://www.yaserakhras.com',
    'depends': [
        'base',
        'purchase',
        'purchase_requisition',
        'product',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/logistics_bill_lading_views.xml',
        'views/logistics_container_line_views.xml',
        'views/logistics_container_views.xml',
        'views/logistics_port_views.xml',
        'views/purchase_requisition_container_distribution_views.xml',
        'views/purchase_requisition_views.xml',
        'views/actions_menus.xml',
    ],
    'demo': [
        'demo/container_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}