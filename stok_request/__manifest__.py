# -*- coding: utf-8 -*-
{
    'name': 'Stock Request',
    'version': '15.0.1.0.0',
    'summary': 'Stock Request Module',
    'author': 'Yaser Akhras',
    'depends': ["base", "stock", "product"],
    'data': [
        # "security/ir.model.access.csv",
        'views/stock_request.xml',
        # 'data/mail_template_data.xml',
        # 'data/check_notifier_cron.xml',
    ],
    'installable': True,
    'application': False,
}