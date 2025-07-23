{
    'name': 'Cash Flow Dashboard',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Dashboard for Cash Flow Account Balances',
    'description': """
        Cash Flow Dashboard Module
        ==========================
        
        This module provides a dashboard view for monitoring cash flow accounts:
        - Account 120002 balance
        - Account 120001 balance  
        - Account 320002 balance
        - Account 320003 balance
        - Account 153000 balance
        
        Features:
        - Kanban card view for account balances
        - Real-time balance updates
        - Clean dashboard interface
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_model_access_data.xml',
        'data/cash_flow_data.xml',
        'views/cash_flow_dashboard_views.xml',
        'views/cash_flow_menuitem.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}