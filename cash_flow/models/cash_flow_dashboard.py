from odoo import models, fields, api
from odoo.exceptions import UserError
import json
from datetime import datetime, timedelta
from collections import defaultdict


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
    
    # Computed balance field - REMOVED store=True to allow context-based filtering
    current_balance = fields.Monetary(
        string='Current Balance', 
        compute='_compute_current_balance',
        currency_field='currency_id'
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
    
    # Chart data for dashboard_graph widget (following Odoo pattern)
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')

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

    @api.depends('account_id', 'company_id')
    def _compute_current_balance(self):
        """Compute current balance for each account with date filtering support"""
        for record in self:
            if record.account_id and record.company_id:
                # Base domain for filtering account move lines
                domain = [
                    ('account_id', '=', record.account_id.id),
                    ('company_id', '=', record.company_id.id),
                    ('move_id.state', '=', 'posted')  # Only posted journal entries
                ]
                
                # Add date filtering from context (if provided by search view)
                date_from = self.env.context.get('date_from')
                date_to = self.env.context.get('date_to')
                
                if date_from:
                    domain.append(('date', '>=', date_from))
                if date_to:
                    domain.append(('date', '<=', date_to))
                
                # Search for account move lines with the filtered domain
                account_moves = self.env['account.move.line'].search(domain)
                
                # Calculate balance (debit - credit for asset accounts, credit - debit for liability/equity)
                debit_total = sum(account_moves.mapped('debit'))
                credit_total = sum(account_moves.mapped('credit'))
                record.current_balance = debit_total - credit_total
                
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

    @api.depends('account_id', 'company_id')
    def _kanban_dashboard_graph(self):
        """Generate chart data for dashboard_graph widget (following Odoo pattern)"""
        for record in self:
            if not record.account_id or not record.company_id:
                record.kanban_dashboard_graph = False
                continue
                
            # Get date range for chart (default last 30 days or from context)
            date_to = self.env.context.get('date_to')
            date_from = self.env.context.get('date_from')
            
            if not date_to:
                date_to = datetime.now().date()
            else:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                
            if not date_from:
                # Default to 30 days back from date_to
                date_from = date_to - timedelta(days=30)
            else:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            
            # Ensure reasonable date range for performance (max 90 days)
            if (date_to - date_from).days > 90:
                date_from = date_to - timedelta(days=90)
            
            # Get daily balances for the date range
            daily_balances = record._get_daily_balances(date_from, date_to)
            
            # Prepare chart data following Odoo pattern
            values = []
            
            current_date = date_from
            while current_date <= date_to:
                balance = daily_balances.get(current_date, 0.0)
                values.append({
                    'label': current_date.strftime('%m/%d'),
                    'value': float(balance),
                    'type': 'past'  # Historical cash flow data
                })
                current_date += timedelta(days=1)
            
            # Return False if no data (like Odoo pattern)
            if not values:
                record.kanban_dashboard_graph = False
                continue
            
            # Create the exact structure as Odoo journals
            chart_data = [{
                'values': values,
                'title': 'Cash Flow Trend',
                'key': record.display_name or record.account_code
            }]
            
            # Store as JSON for dashboard_graph widget
            record.kanban_dashboard_graph = json.dumps(chart_data)

    def _get_daily_balances(self, date_from, date_to):
        """Calculate daily running balances for the account within date range"""
        if not self.account_id or not self.company_id:
            return {}
        
        # Get all move lines for this account up to date_to (to calculate running balance)
        domain = [
            ('account_id', '=', self.account_id.id),
            ('company_id', '=', self.company_id.id),
            ('move_id.state', '=', 'posted'),
            ('date', '<=', date_to.strftime('%Y-%m-%d'))
        ]
        
        # Get all move lines ordered by date
        move_lines = self.env['account.move.line'].search(domain, order='date, id')
        
        # Group transactions by date and calculate running balance
        daily_balances = {}
        running_balance = 0.0
        transactions_by_date = defaultdict(list)
        
        # Group move lines by date
        for line in move_lines:
            line_date = line.date
            transactions_by_date[line_date].append(line)
        
        # Calculate running balance for each day
        for date in sorted(transactions_by_date.keys()):
            day_debit = sum(line.debit for line in transactions_by_date[date])
            day_credit = sum(line.credit for line in transactions_by_date[date])
            running_balance += (day_debit - day_credit)
            
            # Only store balances within our chart date range
            if date_from <= date <= date_to:
                daily_balances[date] = running_balance
        
        # For days without transactions in the range, use previous day's balance
        if daily_balances:
            current_date = date_from
            last_known_balance = running_balance - sum(
                (line.debit - line.credit) for line in move_lines 
                if line.date >= date_from
            ) if move_lines else 0.0
            
            while current_date <= date_to:
                if current_date not in daily_balances:
                    # Find the last known balance before this date
                    previous_balance = last_known_balance
                    for check_date in sorted(daily_balances.keys()):
                        if check_date < current_date:
                            previous_balance = daily_balances[check_date]
                        else:
                            break
                    daily_balances[current_date] = previous_balance
                else:
                    last_known_balance = daily_balances[current_date]
                
                current_date += timedelta(days=1)
        
        return daily_balances

    @api.model
    def get_complete_dashboard_data(self):
        """
        New method for OWL frontend - returns all data needed for dashboard
        """
        try:
            # Get current company
            company_id = self.env.company.id
            
            # Get date filter from context
            date_from = self.env.context.get('date_from')
            date_to = self.env.context.get('date_to')
            
            # Get active configurations for this company (ordered by sequence)
            config_model = self.env['cash.flow.config']
            active_configs = config_model.search([
                ('company_id', '=', company_id),
                ('active', '=', True)
            ], order='sequence, account_code')
            
            if not active_configs:
                # Try auto-suggestion
                try:
                    created_configs = config_model.auto_suggest_setup(company_id)
                    if created_configs:
                        active_configs = created_configs
                    else:
                        return {
                            'success': False,
                            'error': {
                                'message': 'No cash flow configuration found. Please configure accounts first.',
                                'code': 'NO_CONFIG'
                            }
                        }
                except Exception as e:
                    return {
                        'success': False,
                        'error': {
                            'message': f'Failed to auto-configure accounts: {str(e)}',
                            'code': 'AUTO_CONFIG_FAILED'
                        }
                    }
            
            # Prepare account configurations data
            accounts_data = []
            all_account_ids = set()
            
            for config in active_configs:
                account_ids = [config.account_id.id]  # For now, each config maps to one account
                all_account_ids.update(account_ids)
                
                accounts_data.append({
                    'id': config.id,
                    'display_name': config.display_name,
                    'account_ids': account_ids,
                    'sequence': config.sequence,
                    'active': config.active
                })
            
            # Get all transactions for the accounts with date filtering
            transaction_domain = [
                ('account_id', 'in', list(all_account_ids)),
                ('company_id', '=', company_id),
                ('move_id.state', '=', 'posted')
            ]
            
            # Apply date filters if provided
            if date_from:
                transaction_domain.append(('date', '>=', date_from))
            if date_to:
                transaction_domain.append(('date', '<=', date_to))
            
            # Fetch all relevant move lines
            move_lines = self.env['account.move.line'].search(
                transaction_domain,
                order='account_id, date'
            )
            
            # Prepare transactions data
            transactions_data = []
            for line in move_lines:
                transactions_data.append({
                    'id': line.id,
                    'account_id': line.account_id.id,
                    'date': line.date.strftime('%Y-%m-%d'),
                    'debit': float(line.debit),
                    'credit': float(line.credit),
                    'name': line.name or '',
                    'ref': line.ref or '',
                    'move_name': line.move_id.name or ''
                })
            
            # Determine filter info for response
            filter_info = {}
            if date_from or date_to:
                filter_info = {
                    'date_from': date_from,
                    'date_to': date_to,
                    'filtered': True
                }
            else:
                filter_info = {
                    'date_from': None,
                    'date_to': None,
                    'filtered': False
                }
            
            # Success response with data
            return {
                'success': True,
                'data': {
                    'accounts': accounts_data,
                    'transactions': transactions_data,
                    'filter': filter_info
                },
                'meta': {
                    'company_id': company_id,
                    'accounts_count': len(accounts_data),
                    'transactions_count': len(transactions_data),
                    'message': f'Loaded {len(accounts_data)} accounts with {len(transactions_data)} transactions',
                    'timestamp': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            # Error response
            import traceback
            return {
                'success': False,
                'error': {
                    'message': str(e),
                    'code': 'GENERAL_ERROR',
                    'traceback': traceback.format_exc() if self.env.user.has_group('base.group_system') else None
                }
            }

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

    def get_filtered_balance_info(self):
        """Get balance information with current context (including date filters)"""
        # This method can be called to get balance info with current filtering applied
        result = {}
        for record in self:
            result[record.id] = {
                'account_code': record.account_code,
                'display_name': record.display_name,
                'current_balance': record.current_balance,
                'balance_display': record.balance_display,
                'balance_color': record.balance_color,
                'date_from': self.env.context.get('date_from'),
                'date_to': self.env.context.get('date_to'),
            }
        return result