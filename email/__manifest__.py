# -*- coding: utf-8 -*-
{
    'name': "email",

    'summary': """
        email marketing""",

    'description': """
        email marketing. 
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
    'depends': ['base', 'web', 'mass_mailing'],

    # always loaded
    'data': [
        #"security/security.xml",
        "views/email_view.xml",
        # "reports.xml", #action file.
        # "menuitems.xml", #menu items file.
        # "report/layouts.xml", #report page templates file. 
        # "report/unpaid_invoice_report.xml", #report data view file
    ],

    # 'assets': {
    #     'web.assets_backend': [
    #         'web_client/static/src/js/main.js',
    #         'web_client/static/src/js/navbar.js',
    #         'web_client/static/src/js/web_client.js', #buttons event function file.
    #     ],
    #     'web.assets_qweb': [
    #         'web_client/static/src/xml/navbar.xml',
    #         'web_client/static/src/xml/web_client.xml', #buttons template file.
    #     ],
        
    # },
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
}
