# -*- coding: utf-8 -*-
#╔══════════════════════════════════════════════════════════════════════╗
#║                                                                      ║
#║                  ╔═══╦╗       ╔╗  ╔╗     ╔═══╦═══╗                   ║
#║                  ║╔═╗║║       ║║ ╔╝╚╗    ║╔═╗║╔═╗║                   ║
#║                  ║║ ║║║╔╗╔╦╦══╣╚═╬╗╔╬╗ ╔╗║║ ╚╣╚══╗                   ║
#║                  ║╚═╝║║║╚╝╠╣╔╗║╔╗║║║║║ ║║║║ ╔╬══╗║                   ║
#║                  ║╔═╗║╚╣║║║║╚╝║║║║║╚╣╚═╝║║╚═╝║╚═╝║                   ║
#║                  ╚╝ ╚╩═╩╩╩╩╩═╗╠╝╚╝╚═╩═╗╔╝╚═══╩═══╝                   ║
#║                            ╔═╝║     ╔═╝║                             ║
#║                            ╚══╝     ╚══╝                             ║
#║                  SOFTWARE DEVELOPED AND SUPPORTED BY                 ║
#║                ALMIGHTY CONSULTING SOLUTIONS PVT. LTD.               ║
#║                      COPYRIGHT (C) 2016 - TODAY                      ║
#║                      https://www.almightycs.com                      ║
#║                                                                      ║
#╚══════════════════════════════════════════════════════════════════════╝
{
    'name' : 'Lugano Egypt',
    'category' : 'Project',
    'version': '1.0.1',
    'depends' : ['base'],
    'author': 'Yaser Akhras',
    'website': 'https://www.yaserakhras.com',
    'license': 'OPL-1',
    'summary': """Lugano Coffee Egypt""",
    'description': """Lugano Coffee Egypt""",
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/visit_data.xml',
        # 'views/project_views.xml',
        'views/visit_view.xml',
        # 'reports/visit_report.xml',
    ],
    'images': [
        'static/description/odoo_visits_almightycs_cover.jpg',
    ],
    'application': True,
    'sequence': 1,
    'price': 36,
    'currency': 'USD',
}
