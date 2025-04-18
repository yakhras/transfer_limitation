# -*- coding: utf-8 -*-
{
    'name': 'Check Notifier',
    'version': '1.0',
    'summary': 'Send email notifications for multi-currency checks',
    'author': 'Yaser Akhras',
    'depends': ['l10n_tr_account_check'],
    'data': [
        # "security/ir.model.access.csv",
        'views/check_report_queue_views.xml',
    #     'data/check_notifier_cron.xml',
    ],
    'installable': True,
    'application': False,
}