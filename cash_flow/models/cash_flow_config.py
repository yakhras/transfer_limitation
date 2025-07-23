from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class CashFlowConfig(models.Model):
    _name = 'cash.flow.config'
    _description = 'Cash Flow Dashboard Configuration'
    _order = 'company_id, sequence, account_code'

    # Basic Configuration Fields
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                default=lambda self: self.env.company)
    account_id = fields.Many2one('account.account', string='Account', required=True,
                                domain="[('company_id', '=', company_id)]")
    account_code = fields.Char(related='account_id.code', string='Account Code', store=True)
    account_name = fields.Char(related='account_id.name', string='Default Account Name', store=True)
    
    # Configuration Options
    custom_label = fields.Char(string='Custom Label', 
                              help="Custom display name for this account on the dashboard. Leave empty to use account name.")
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    active = fields.Boolean(string='Active', default=True,
                           help="If unchecked, this account will not appear on the dashboard")
    sequence = fields.Integer(string='Display Order', default=10,
                             help="Determines the order of accounts on the dashboard")
    
    # Computed fields for dashboard integration
    suggested_type = fields.Char(string='Suggested Type', compute='_compute_suggested_type', store=True)
    
    # SQL Constraints
    _sql_constraints = [
        ('unique_account_company', 'unique(account_id, company_id)', 
         'Each account can only be configured once per company!'),
    ]

    @api.depends('custom_label', 'account_name')
    def _compute_display_name(self):
        """Compute the display name: custom label if provided, otherwise account name"""
        for record in self:
            record.display_name = record.custom_label or record.account_name

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
            return first_digit in ['1']
            
        # Default to False if unable to determine
        return False

    def _get_account_type_name(self, account):
        """Get a human-readable account type name"""
        if not account:
            return 'Unknown'
            
        # Try to get account type from various Odoo version approaches
        if hasattr(account, 'account_type'):
            type_map = {
                'asset_cash': 'Cash',
                'asset_receivable': 'Receivables', 
                'asset_current': 'Current Assets',
                'asset_fixed': 'Fixed Assets',
                'liability_payable': 'Payables',
                'liability_current': 'Current Liabilities',
                'equity': 'Equity'
            }
            return type_map.get(account.account_type, account.account_type.replace('_', ' ').title())
            
        elif hasattr(account, 'user_type_id') and account.user_type_id:
            return account.user_type_id.name
            
        elif hasattr(account, 'internal_type'):
            type_map = {
                'receivable': 'Receivables',
                'payable': 'Payables', 
                'bank': 'Bank',
                'cash': 'Cash',
                'asset': 'Assets'
            }
            return type_map.get(account.internal_type, account.internal_type.title())
            
        # Fallback to account code pattern
        if account.code:
            if account.code.startswith('1'):
                return 'Assets'
            elif account.code.startswith('2'):
                return 'Liabilities'
            elif account.code.startswith('3'):
                return 'Equity'
                
        return 'Other'

    @api.depends('account_id')
    def _compute_suggested_type(self):
        """Compute suggested account type for display"""
        for record in self:
            if record.account_id:
                record.suggested_type = self._get_account_type_name(record.account_id)
            else:
                record.suggested_type = ''

    @api.model
    def get_suggested_accounts(self, company_id=None):
        """Get suggested accounts for cash flow monitoring"""
        if not company_id:
            company_id = self.env.company.id
            
        suggested_accounts = []
        
        # Get all accounts for the company
        accounts = self.env['account.account'].search([('company_id', '=', company_id)])
        
        # Filter for common cash flow accounts
        for account in accounts:
            account_type = self._get_account_type_name(account)
            
            # Suggest accounts that are commonly monitored for cash flow
            if any(keyword in account_type.lower() for keyword in ['cash', 'bank', 'receivable']):
                # Check if already configured
                existing = self.search([
                    ('account_id', '=', account.id),
                    ('company_id', '=', company_id)
                ])
                
                if not existing:
                    suggested_accounts.append({
                        'account_id': account.id,
                        'account_code': account.code,
                        'account_name': account.name,
                        'suggested_type': account_type,
                        'suggested_label': f"{account_type} - {account.name}"
                    })
        
        # Sort by account code
        suggested_accounts.sort(key=lambda x: x['account_code'])
        return suggested_accounts

    @api.model
    def auto_suggest_setup(self, company_id=None):
        """Auto-suggest and create configuration for common accounts"""
        if not company_id:
            company_id = self.env.company.id
            
        # Get suggested accounts
        suggested = self.get_suggested_accounts(company_id)
        
        # Create configuration records for top suggestions (limit to 10)
        created_configs = []
        sequence = 10
        
        for suggestion in suggested[:10]:  # Limit to top 10 suggestions
            config = self.create({
                'company_id': company_id,
                'account_id': suggestion['account_id'],
                'custom_label': suggestion['suggested_label'],
                'sequence': sequence,
                'active': True
            })
            created_configs.append(config)
            sequence += 10
            
        return created_configs

    def action_generate_dashboard_records(self):
        """Generate dashboard records based on this configuration (Legacy method)"""
        # This method is now legacy since records are auto-generated
        # But keeping it for manual refresh if needed
        active_configs = self.env['cash.flow.config'].search([('active', '=', True)])
        
        for config in active_configs:
            config._sync_dashboard_record()

    @api.model
    def generate_all_dashboard_records(self):
        """Generate dashboard records for all active configurations (Legacy method)"""
        # This method is now legacy since records are auto-generated
        # But keeping it for manual refresh/cleanup if needed
        active_configs = self.search([('active', '=', True)])
        
        for config in active_configs:
            config._sync_dashboard_record()
            
        # Clean up orphaned dashboard records (records without active config)
        dashboard_model = self.env['cash.flow.dashboard']
        all_dashboard_records = dashboard_model.search([])
        
        for dashboard_record in all_dashboard_records:
            # Check if there's an active config for this dashboard record
            config_exists = self.search([
                ('account_id', '=', dashboard_record.account_id.id),
                ('company_id', '=', dashboard_record.company_id.id),
                ('active', '=', True)
            ])
            
            if not config_exists:
                dashboard_record.unlink()  # Remove orphaned dashboard record

    def name_get(self):
        """Custom name display for configuration records"""
        result = []
        for record in self:
            name = f"{record.account_code} - {record.display_name}"
            if not record.active:
                name += " (Inactive)"
            result.append((record.id, name))
        return result

    @api.model
    def create(self, vals):
        """Override create to automatically generate dashboard records"""
        config = super(CashFlowConfig, self).create(vals)
        
        # Automatically create dashboard record if config is active
        if config.active:
            config._create_dashboard_record()
            
        return config

    def write(self, vals):
        """Override write to automatically sync dashboard records"""
        result = super(CashFlowConfig, self).write(vals)
        
        for config in self:
            if config.active:
                # Create or update dashboard record
                config._sync_dashboard_record()
            else:
                # Remove dashboard record if config is deactivated
                config._remove_dashboard_record()
                
        return result

    def unlink(self):
        """Override unlink to automatically remove dashboard records"""
        # Remove corresponding dashboard records before deleting config
        for config in self:
            config._remove_dashboard_record()
            
        return super(CashFlowConfig, self).unlink()

    def _create_dashboard_record(self):
        """Create dashboard record for this configuration"""
        dashboard_model = self.env['cash.flow.dashboard']
        
        # Check if dashboard record already exists
        existing = dashboard_model.search([
            ('account_id', '=', self.account_id.id),
            ('company_id', '=', self.company_id.id)
        ])
        
        if not existing:
            dashboard_model.create({
                'account_id': self.account_id.id,
                'company_id': self.company_id.id,
            })

    def _sync_dashboard_record(self):
        """Create or update dashboard record for this configuration"""
        dashboard_model = self.env['cash.flow.dashboard']
        
        # Find existing dashboard record
        dashboard_record = dashboard_model.search([
            ('account_id', '=', self.account_id.id),
            ('company_id', '=', self.company_id.id)
        ])
        
        if not dashboard_record:
            # Create new dashboard record
            dashboard_model.create({
                'account_id': self.account_id.id,
                'company_id': self.company_id.id,
            })
        # Note: Dashboard record doesn't need updating since it uses computed fields
        # that automatically reflect current account data

    def _remove_dashboard_record(self):
        """Remove dashboard record for this configuration"""
        dashboard_model = self.env['cash.flow.dashboard']
        
        # Find and remove corresponding dashboard record
        dashboard_record = dashboard_model.search([
            ('account_id', '=', self.account_id.id),
            ('company_id', '=', self.company_id.id)
        ])
        
        if dashboard_record:
            dashboard_record.unlink()

    def toggle_active(self):
        """Toggle active status and sync dashboard"""
        for record in self:
            record.active = not record.active