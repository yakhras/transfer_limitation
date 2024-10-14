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
    'depends': ['point_of_sale', 'base', 'web'],
    #"data": ['views/pos_config.xml'],
    'assets': {
        'point_of_sale.assets': [
            'geolocation/static/src/js/Screens/SaleOrderScreen/SaleOrderScreen.js',
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