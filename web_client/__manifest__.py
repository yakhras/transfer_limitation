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
    'depends': [],

    # always loaded
    'data': [
        #"security/security.xml",
        # "views/unpaid_invoice_view.xml",
        # "reports.xml", #action file.
        # "menuitems.xml", #menu items file.
        # "report/layouts.xml", #report page templates file. 
        # "report/unpaid_invoice_report.xml", #report data view file
    ],

    'assets': {
        'web.assets_backend': [
            'unpaid_invoice/static/src/js/main.js',
            'unpaid_invoice/static/src/js/navbar.js',
            'unpaid_invoice/static/src/js/web_client.js', #buttons event function file.
        ],
        'web.assets_qweb': [
            'unpaid_invoice/static/src/xml/navbar.xml',
            'unpaid_invoice/static/src/xml/web_client.xml', #buttons template file.
        ],
        
    },
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
