{
    'name': 'geolocation',
    'version': '15.0.0.1',
    'category': 'Sales/Point of Sale',
    'summary': 'geolocation ',
    'description': '''
    ''',
    'author': 'Yaser Akhras',
    'website': 'http://yaserakhras.com',
    #'support': 'support@warlocktechnologies.com',
    'depends': ['base', 'web'],
    "data": ["views/res_partner.xml",],
    'assets': {
        'backend.assets': [
            #'geolocation/static/src/js/Screens/SaleOrderScreen/SaleOrderScreen.js',
            'geolocation/static/src/js/Screens/SaleOrderScreen/SaleOrderScreen copy.js',
            'geolocation/static/src/js/Popups/SalesOrderPopup.js',
        ],
        'web.assets_qweb': [
            'geolocation/static/src/xml/**/*',
        ],
    },
    'images': ['static/images/screen_image.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
    'license': 'OPL-1',
    'external_dependencies': {
    },
}
