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
    
    'version': '15.0.2.0',
    'application': True,
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['account','sale'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/sales_team_card_view.xml',
        'views/pdf.xml',
        'views/pdf_group_by_template.xml',
        'data/mail_template_data.xml',
        'data/month_card_data.xml',
        'data/payment_term_data.xml',
    ],
    
    'assets': {
        'web.assets_qweb': [
            'unpaid_invoice/static/src/xml/button_view.xml',
        ],
        'web.assets_backend': [
            'unpaid_invoice/static/src/css/custom_styles.css',
            'unpaid_invoice/static/src/js/pdf_export.js'
        ]
    },

    # 'assets': {
    #     'web.assets_backend': [
    #         'unpaid_invoice/static/src/js/unpaid_invoice.js', #buttons event function file.
    #     ],
    #     'web.assets_qweb': [
    #         'unpaid_invoice/static/src/xml/unpaid_invoice.xml', #buttons template file.
    #     ],
        
    # },
    # only loaded in demonstration mode
    
}
