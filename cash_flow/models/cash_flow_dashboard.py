from odoo import models, fields, api
from odoo.exceptions import UserError


class CashFlowDashboard(models.Model):
    _name = 'cash.flow.dashboard'
    _description = 'Cash Flow Dashboard'
    _order = 'account_code'

    # Basic fields
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                default=lambda self: self.env.company)
    account_id = fields.Many2one('account.account', string='Account', required=True,
                                domain="[('company_id', '=', company_id)]")
    account_code = fields.Char(related='account_id.code', string='Account Code', store=True)
    account_name = fields.Char(related='account_id.name', string='Account Name', store=True)
    
    # Display name from configuration (custom label or account name)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name_from_config')
    
    # Computed balance field
    current_balance = fields.Monetary(
        string='Current Balance', 
        compute='_compute_current_balance',
        currency_field='currency_id',
        store=True
    )
    
    # Currency field
    currency_id = fields.Many2one(
        'res.currency', 
        string='Currency',
        related='company_id.currency_id',
        store=True
    )
    
    # Display fields for kanban
    balance_display = fields.Char(
        string='Balance Display',
        compute='_compute_balance_display'
    )
    
    balance_color = fields.Selection([
        ('green', 'Positive'),
        ('red', 'Negative'),
        ('blue', 'Zero')
    ], string='Balance Color', compute='_compute_balance_color')

    # Add SQL constraints for company consistency
    _sql_constraints = [
        ('unique_account_company', 'unique(account_id, company_id)', 
         'Dashboard record must be unique per account and company!'),
    ]

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        """Override search to automatically filter by current company"""
        # Add company filter if not already present
        company_domain = [('company_id', '=', self.env.company.id)]
        
        # Check if company_id is already in the domain
        has_company_filter = any(arg[0] == 'company_id' for arg in args if isinstance(arg, (list, tuple)) and len(arg) >= 1)
        
        if not has_company_filter:
            args = args + company_domain
            
        return super(CashFlowDashboard, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)

    @api.depends('account_id', 'company_id')
    def _compute_display_name_from_config(self):
        """Get display name from configuration (custom label or account name)"""
        for record in self:
            if record.account_id and record.company_id:
                # Find corresponding configuration record
                config = self.env['cash.flow.config'].search([
                    ('account_id', '=', record.account_id.id),
                    ('company_id', '=', record.company_id.id),
                    ('active', '=', True)
                ], limit=1)
                
                if config:
                    record.display_name = config.display_name
                else:
                    # Fallback to account name if no config found
                    record.display_name = record.account_name
            else:
                record.display_name = record.account_name or ''

    def _is_asset_account(self, account):
        """Determine if account is an asset account - compatible across Odoo versions"""
        # Try different field names depending on Odoo version
        
        # For newer versions (14.0+) that use account_type
        if hasattr(account, 'account_type'):
            asset_types = [
                'asset_receivable', 'asset_cash', 'asset_current', 'asset_fixed',
                'asset_prepayments', 'asset_non_current'
            ]
            return account.account_type in asset_types
            
        # For older versions (11.0-13.0) that use user_type_id
        elif hasattr(account, 'user_type_id') and account.user_type_id:
            # Check by user type code/name
            user_type = account.user_type_id
            asset_codes = ['receivable', 'asset', 'bank', 'cash']
            
            # Try different ways to identify asset accounts
            if hasattr(user_type, 'type'):
                return user_type.type in asset_codes
            elif hasattr(user_type, 'code'):
                return user_type.code in asset_codes
            elif hasattr(user_type, 'name'):
                asset_names = ['Receivable', 'Current Assets', 'Fixed Assets', 'Bank and Cash', 'Asset']
                return any(name in user_type.name for name in asset_names)
                
        # For versions that use internal_type
        elif hasattr(account, 'internal_type'):
            asset_types = ['receivable', 'bank', 'cash', 'asset']
            return account.internal_type in asset_types
            
        # Fallback: check account code patterns (first digit)
        # Most chart of accounts use 1xxx for assets
        if account.code and len(account.code) >= 1:
            first_digit = account.code[0]
            return first_digit in ['1', '2'] and not account.code.startswith('2')  # 1xxx = assets, 2xxx can be assets or liabilities
            
        # Default to False if unable to determine
        return False

    @api.depends('account_id', 'account_id.current_balance', 'company_id')
    def _compute_current_balance(self):
        """Compute current balance for each account (posted entries only)"""
        for record in self:
            if record.account_id and record.company_id:
                # Get current balance from account - filter by company and posted moves only
                domain = [
                    ('account_id', '=', record.account_id.id),
                    ('company_id', '=', record.company_id.id),
                    ('move_id.state', '=', 'posted')  # Only posted journal entries
                ]
                account_moves = self.env['account.move.line'].search(domain)
                
                # Calculate balance (debit - credit for asset accounts, credit - debit for liability/equity)
                debit_total = sum(account_moves.mapped('debit'))
                credit_total = sum(account_moves.mapped('credit'))
                
                # Determine balance based on account type
                if self._is_asset_account(record.account_id):
                    record.current_balance = debit_total - credit_total
                else:
                    record.current_balance = credit_total - debit_total
            else:
                record.current_balance = 0.0

    @api.depends('current_balance', 'currency_id')
    def _compute_balance_display(self):
        """Format balance for display in kanban cards"""
        for record in self:
            if record.currency_id:
                # Handle different Odoo versions with different currency formatting methods
                try:
                    # Try newer version method (some versions have format)
                    if hasattr(record.currency_id, 'format'):
                        record.balance_display = record.currency_id.format(record.current_balance)
                    # Try round method (common in many versions)
                    elif hasattr(record.currency_id, 'round'):
                        rounded_amount = record.currency_id.round(record.current_balance)
                        record.balance_display = f"{record.currency_id.symbol or ''}{rounded_amount:,.2f}".strip()
                    # Try with_context formatting
                    elif hasattr(record.currency_id, 'with_context'):
                        formatted = record.currency_id.with_context(lang=self.env.user.lang).format(record.current_balance)
                        record.balance_display = formatted
                    else:
                        # Fallback: manual formatting with currency symbol
                        symbol = getattr(record.currency_id, 'symbol', '') or getattr(record.currency_id, 'name', '')
                        record.balance_display = f"{symbol} {record.current_balance:,.2f}".strip()
                except Exception:
                    # Final fallback if all methods fail
                    symbol = getattr(record.currency_id, 'symbol', '') or getattr(record.currency_id, 'name', '')
                    record.balance_display = f"{symbol} {record.current_balance:,.2f}".strip()
            else:
                record.balance_display = f"{record.current_balance:,.2f}"

    @api.depends('current_balance')
    def _compute_balance_color(self):
        """Determine card color based on balance"""
        for record in self:
            if record.current_balance > 0:
                record.balance_color = 'green'
            elif record.current_balance < 0:
                record.balance_color = 'red'
            else:
                record.balance_color = 'blue'

    @api.model
    def create_dashboard_records(self, company_id=None):
        """Create dashboard records based on configuration (Legacy - now automatic)"""
        # This method is now legacy since dashboard records are automatically 
        # created when configuration records are saved. Keeping for compatibility.
        
        # Use provided company_id or current user's company
        if not company_id:
            company_id = self.env.company.id
            
        # Get active configurations for this company
        config_model = self.env['cash.flow.config']
        active_configs = config_model.search([
            ('company_id', '=', company_id),
            ('active', '=', True)
        ])
        
        if not active_configs:
            # No configuration exists, try to auto-suggest
            try:
                created_configs = config_model.auto_suggest_setup(company_id)
                # Dashboard records will be created automatically by the config model overrides
                return created_configs
            except Exception:
                # If auto-suggestion fails, raise error
                raise UserError(
                    "No cash flow configuration found for this company. "
                    "Please configure accounts first in Settings > Cash Flow > Dashboard Configuration"
                )
        
        # Sync existing configurations (dashboard records auto-created by config model)
        for config in active_configs:
            config._sync_dashboard_record()

    @api.model
    def get_dashboard_data(self, company_id=None):
        """Get dashboard data based on configuration for the specified company"""
        # Use provided company_id or current user's company
        if not company_id:
            company_id = self.env.company.id
        
        # Get active configurations for this company (ordered by sequence)
        config_model = self.env['cash.flow.config']
        active_configs = config_model.search([
            ('company_id', '=', company_id),
            ('active', '=', True)
        ], order='sequence, account_code')
        
        if not active_configs:
            # No configuration, return empty or auto-suggest
            return []
        
        dashboard_data = []
        
        for config in active_configs:
            # Search for existing dashboard record for this company
            dashboard_record = self.search([
                ('account_id', '=', config.account_id.id),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if not dashboard_record:
                dashboard_record = self.create({
                    'account_id': config.account_id.id,
                    'company_id': company_id,
                })
            
            dashboard_data.append({
                'id': dashboard_record.id,
                'account_code': config.account_code,
                'account_name': config.account_name,
                'display_name': dashboard_record.display_name or config.display_name,  # Use dashboard's computed display_name with fallback
                'current_balance': dashboard_record.current_balance,
                'balance_display': dashboard_record.balance_display,
                'balance_color': dashboard_record.balance_color,
                'company_id': company_id,
                'sequence': config.sequence,
            })
        
        return dashboard_data

    @api.model
    def init_dashboard_for_all_companies(self):
        """Initialize dashboard records for all companies based on their configurations"""
        companies = self.env['res.company'].search([])
        
        for company in companies:
            try:
                # Use with_context to set the company context
                self.with_context(force_company=company.id).create_dashboard_records(company.id)
            except UserError:
                # Skip companies that don't have configuration or accounts
                continue

    @api.model  
    def get_current_company_dashboard(self):
        """Get dashboard data for current user's company"""
        return self.get_dashboard_data(self.env.company.id)
    
    @api.model
    def refresh_dashboard_from_config(self):
        """Refresh dashboard records based on current configuration"""
        # This method can be called to sync dashboard records with configuration changes
        config_model = self.env['cash.flow.config']
        config_model.generate_all_dashboard_records()
        
        # Clean up dashboard records that no longer have configuration
        all_configs = config_model.search([('active', '=', True)])
        configured_accounts = [(config.account_id.id, config.company_id.id) for config in all_configs]
        
        # Find dashboard records that don't have corresponding active configuration
        all_dashboard_records = self.search([])
        for dashboard_record in all_dashboard_records:
            key = (dashboard_record.account_id.id, dashboard_record.company_id.id)
            if key not in configured_accounts:
                dashboard_record.unlink()  # Remove orphaned dashboard records