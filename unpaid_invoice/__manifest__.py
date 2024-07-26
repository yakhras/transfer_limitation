# -*- coding: utf-8 -*-
{
    'name': "unpaid_invoice",

    'summary': """
        cretae a pdf report for unpaid invoices.""",

    'description': """
        cretae a pdf report for unpaid invoices. 
    """,

    'author': "Yaser Akhras",
    #'website': "https://www.yaserakhras.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    
    'version': '15.0.1.0',
    'application': True,
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base','account','sale'],

    # always loaded
    'data': [
        #"security/security.xml",
        "views/unpaid_invoice_view.xml",
    ],

    'assets': {
        'web.assets_qweb': [
            'unpaid_invoice/static/src/xml/unpaid_invoice.xml',
        ],
        'web.assets_backend': [
            'unpaid_invoice/static/src/js/unpaid_invoice.js'
        ],
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
