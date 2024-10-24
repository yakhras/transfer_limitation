# -*- coding: utf-8 -*-
{
    'name': "partner_balance",

    'summary': """
        Partner Balance""",

    'description': """
        Partner Balance. 
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
    'depends': ['base', 'account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        "views/partner_balance_view.xml",
        'report/partner_balance_report.xml',    # Report action
        'report/partner_balance_report_template.xml',   # Report template

    ],

    'assets': {
        'web.assets_backend': [
            'partner_balance/static/src/js/export_pdf_button.js',
        ],
        'web.assets_qweb': [
            'partner_balance/static/src/xml/partner_balance_qweb.xml',
        ],
    },
}
