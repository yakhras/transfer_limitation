# -*- coding: utf-8 -*-
{
    'name': "Multi Email Signature",

    'summary': """
        Enhance email signature management for users with multiple emails.""",

    'description': """
        Multi Email Signature for Odoo Users
        
        This module allows users to manage multiple email signatures based on different email addresses.
        Key Features:
        - Store multiple signatures per user.
        - Automatically select the correct signature when composing an email.
        - Easy management of signatures through the user preferences.

        This enhances flexibility and professionalism when communicating via Odoo's email system. 
    """,

    'author': "Yaser Akhras",
    #'website': "https://www.yaserakhras.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    
    'version': '15.1.0.0',
    'installable': True,
    'application': False,
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail']  ,

    # always loaded
    'data': [
        "views/email_signature_views.xml",
    ],
}
