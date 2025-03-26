# -*- coding: utf-8 -*-
{
    'name': "Product Document",

    'summary': """
        Product documents""",

    'description': """
        Product documents. 
    """,

    'author': "Yaser Akhras",
    #'website': "https://www.yaserakhras.com",
    
    'version': '15.0.1.0',
    'application': True,
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['stock','project'],

    # always loaded
    'data': [
        "security/ir.model.access.csv",
        "views/product_product_view.xml",
    ],
    'assets': {
        'web.assets_qweb': [
            'product_doc/static/src/attachment_box.xml',
        ],
        'web.assets_backend': [
            'product_doc/static/src/project_task_kanban.js',
    ],
    }

}
