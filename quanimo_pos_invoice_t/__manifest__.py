# -*- coding: utf-8 -*-

{
    "name": "Quanimo POS Invoice",
    "summary": "Quanimo POS Invoice Enhanced",
    "version": "15.0.1.0.1",
    "category": "Accounting",
    "website": "https://www.quanimo.com",
    'author': 'Quanimo',
    "license": "AGPL-3",
    "depends": [
        "point_of_sale",
        "l10n_tr_account_einvoice"
    ],
    "data": [
        'data/ir_actions_data.xml',
        'views/res_partner_view.xml'
    ],
    'assets': {
        'point_of_sale.assets': [
            'quanimo_pos_invoice_t/static/src/js/models.js',
        ]
    },
    "qweb": [
    ],
    "application": False,
    "installable": True,
    "auto_install": False,
}
