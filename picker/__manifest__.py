# -*- coding: utf-8 -*-
{
    'name': "picker",

    'summary': """
        Transfer Validation Limit.""",

    'description': """
        Transfer Validation Limit. 
    """,

    'author': "Yaser Akhras",
    #'website': "https://www.yaserakhras.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    
    'version': '15.0.1.2.0',
    'application': True,
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['stock_account','base'],

    # always loaded
    'data': [
        #"security/security.xml",
        "security/ir.model.access.csv",
        "wizard/transfer_limi_wizard_view.xml",
        "views/res_partner_view.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
