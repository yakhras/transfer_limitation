# -*- coding: utf-8 -*-
{
    'name': "Stock Flow",

    'summary': """Tracks the running quantity of a product at each stock move.""",

    'description': """The quantity is being updated at each move.""",

    'author': "Yaser Akhras",
    #'website': "https://www.yaserakhras.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    
    'version': '15.0.1.0',
    'installable': True,
    'application': True,
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['stock','base']  ,

    # always loaded
    'data': [
        "views/stock_flow_view.xml",
    ],
}
