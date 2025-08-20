{
    'name': 'Cash Flow Dashboard',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Interactive Dashboard for Cash Flow Account Balances',
    'description': """
        Cash Flow Dashboard Module
        ==========================
        
        This module provides an interactive OWL-based dashboard for monitoring cash flow accounts:
        - Account 120002 balance
        - Account 120001 balance  
        - Account 320002 balance
        - Account 320003 balance
        - Account 153000 balance
        
        Features:
        - Interactive OWL dashboard with real-time data
        - Period selection (monthly, quarterly, yearly)
        - Interactive Chart.js charts with balance trends
        - Responsive design for all devices
        - Click-through navigation to account details
        - Real-time balance updates
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'account',
        'web',  # Required for OWL components
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_model_access_data.xml',
        'views/cash_flow_dashboard_views.xml',
        'views/cash_flow_debug_line_view.xml',
        'views/cash_flow_config_views.xml',
        'views/cash_flow_menuitem.xml',
        'views/cash_flow_owl_actions.xml',  # New OWL client action
    ],
    'assets': {
        'web.assets_backend': [
            'cash_flow_t/static/src/components/**/*.scss',
            'cash_flow_t/static/src/components/**/*.js',
        ],
        'web.assets_qweb': [
            'cash_flow_t/static/src/components/**/*.xml',
        ],
    },
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}