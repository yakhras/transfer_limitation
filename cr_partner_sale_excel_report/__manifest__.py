# -*- coding: utf-8 -*-
# Part of Creyox Technologies
{
    'name': 'Generate an Excel & PDF Report of Sales of Customers',
    "author": "Creyox Technologies",
    "website": "https://www.creyox.com",
    "support": "support@creyox.com",
    'category': 'Sales',
    'summary': 'Print Excel and PDF reports of sale orders of customer between start date and end date',
    "license": "OPL-1",
    'version': '15.0',
    'description': """

Generate Excel & PDF Report of sale order for Customer is module where 
all the sale orders of customer is fetched and stored into container and
on button click functionality it downloads the EXcel or PDF Report for 
the start date and end date given from wizard area.

""",
    'depends': ["account", "base", "sale"],
    'data': [
        "security/ir.model.access.csv",
        "wizard/res_partner_view.xml",
        "report/sale_excel_to_pdf_report_template.xml",
        "report/sale_excel_to_pdf_report.xml",
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "images": ["static/description/banner.png", ],
    "price": 0,
    "currency": "USD"
}
