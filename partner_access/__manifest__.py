# -*- coding: utf-8 -*-

{
    "name": "Partner Access",
    "category": 'Sales',
    "version": '1.0',
    "sequence":1,
    "summary": " Partner Access ",
    "description": " Partner Access ",
    'author': 'Yaser Akhras', 
    'website': 'https://www.yaserakhras.com',
    "depends": ['sale'],
    "data": [
        'security/group.xml',
	    'security/ir.model.access.csv',
        'views/res_partner_view.xml',
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    'uninstall_hook': 'uninstall_hook',
}
