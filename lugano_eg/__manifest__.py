# -*- coding: utf-8 -*-

{
    'name' : 'Lugano Egypt',
    'category' : 'Project',
    'version': '1.0.1',
    'depends' : ['base','mail'],
    'author': 'Yaser Akhras',
    'website': 'https://www.yaserakhras.com',
    'license': 'OPL-1',
    'summary': """Lugano Coffee Egypt""",
    'description': """Lugano Coffee Egypt""",
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/visit_data.xml',
        'views/visit_view.xml',
    ],
    'application': True,
    'sequence': 1,
}
