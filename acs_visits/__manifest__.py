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
    'name' : 'Visit Management',
    'category' : 'Project',
    'version': '1.0.1',
    'depends' : ['project', 'sale_timesheet'],
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'website': 'https://www.almightycs.com',
    'license': 'OPL-1',
    'support': 'info@almightycs.com',
    'summary': """Site Visit Management for Projects or sales""",
    'description': """Visits Management System to manage your employee visits to onsite related to project or sales.
    Employee Visits
    Visits Management
    site visits
    client visits project visits

    Système de gestion des visites pour gérer les visites de vos employés sur site liées au projet ou aux ventes.
     Visites d'employés
     Gestion des visites
     visites de sites
     visites de clients visites de projets

    Sistema de gestión de visitas para gestionar las visitas de sus empleados a sitios relacionados con proyectos o ventas.
     Visitas de empleados
     Gestión de visitas
     visitas al sitio
     visitas de clientes visitas de proyectos

    Visits Management System zur Verwaltung Ihrer Mitarbeiterbesuche vor Ort in Bezug auf Projekt oder Vertrieb
     Mitarbeiterbesuche
     Besuch des Managements
     Seitenbesuche
     Kunde besucht Projektbesuche

    Visits Management System voor het beheren van uw werknemersbezoeken aan onsite gerelateerd aan project of verkoop.
     Medewerkersbezoeken
     Visits Management
     bezoeken ter plaatse
     klant bezoekt projectbezoeken
    """,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/visit_data.xml',
        'views/project_views.xml',
        'views/visit_view.xml',
        'reports/visit_report.xml',
    ],
    'images': [
        'static/description/odoo_visits_almightycs_cover.jpg',
    ],
    'application': True,
    'sequence': 1,
    'price': 36,
    'currency': 'USD',
}
