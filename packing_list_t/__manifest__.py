# -*- coding: utf-8 -*-
{
    'name': "packing_list",

    'summary': """
        packing_list""",

    'description': """
        packing_list. 
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
    'depends': ['base', 'account', 'sale_management'],

    # always loaded
    'data': [
        "wizard/res_partner_view.xml",
        "views/report_packing_template.xml",
        "views/custom_packing_template.xml",
        "views/sale_order_view.xml",
        "views/product_view.xml",
    ],
}
