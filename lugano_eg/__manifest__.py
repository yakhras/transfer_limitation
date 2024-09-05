# -*- coding: utf-8 -*-
{
    'name': "lugano_eg",

    'summary': """
        Lugano Coffee Egypt.""",

    'description': """
        Lugano Coffee Egypt.. 
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
    'depends': ['base'],

    # always loaded
    'data': [
        #"security/security.xml",
        "security/logistics_security.xml",
        # "security/ir.model.access.csv",
        # "wizard/transfer_limi_wizard_view.xml",
        "views/lugano_eg_menu_view.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
