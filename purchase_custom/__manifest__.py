# -*- coding: utf-8 -*-
{
    'name': "Purchase Custom",

    'summary': """
        Purchase Custom""",

    'description': """
        Purchase Custom. 
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
    'depends': ['purchase_requisition'],

    # always loaded
    'data': [
        "views/purchase_requisition_view.xml",
    ],
}
