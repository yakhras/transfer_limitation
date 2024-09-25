# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Custom',
    'version': '15.0.0.1',
    'category': 'Point of Sale',
    'summary': 'Point Of Sale Out Of Stock, Show location Available Quantity',
    'description' :"""
       Point Of Sale Prevent Out Of Stock, 
       Show location Available Quantity
    """,
    'author': 'Yaser Akhras',
    'website': '',
    'depends': ['base','point_of_sale','stock'],
    'data': [
        'views/pos_custom_view.xml',
    ],
    'assets':{
        'point_of_sale.assets': [
            '/pos_custom/static/src/css/pos_custom.css',
            '/pos_custom/static/src/js/models.js',
            '/pos_custom/static/src/js/ProductList.js',
            '/pos_custom/static/src/js/ProductScreen.js',
        ],
        'web.assets_qweb': [
            'pos_custom/static/src/xml/**/*',
        ],
        'web.assets_backend': [
            '/pos_custom/static/src/css/pos_custom.css',
        ],
    },
    'demo': [],
    'test': [],
    'license':'OPL-1',
    'installable': True,
    'auto_install': False,
}
