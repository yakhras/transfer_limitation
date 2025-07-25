from odoo import models, fields, api
from odoo.exceptions import UserError
import json
from datetime import datetime, timedelta
from collections import defaultdict


class CashFlowDashboard(models.Model):
    _name = 'cash.flow.dashboard'
    _description = 'Cash Flow Dashboard'
    _order = 'sequence, account_codes'

    # Basic fields - UPDATED for multiple accounts
    company_id = fields.Many2one('res.company', string='Company', required=True, 
                                default=lambda self: self.env.company)
    
    # ADDED: Link to configuration record
    config_id = fields.Many2one('cash.flow.config', string='Configuration', required=True,
                               ondelete='cascade')
    
    # CHANGED: From Many2one to Many2many
    account_ids = fields.Many2many(
        'account.account', 
        string='Accounts', 
        required=True,
        domain="[('company_id', '=', company_id)]"
    )
    
    # CHANGED: Now computed from multiple accounts
    account_codes = fields.Char(string='Account Codes', compute='_compute_account_info', store=True)
    account_names = fields.Char(string='Account Names', compute='_compute_account_info', store=True)
    
    # Display name from configuration (custom label)
    display_name = fields.Char(string='Display Name', related='config_id.display_name', store=True)
    sequence = fields.Integer(string='Sequence', related='config_id.sequence', store=True)
    
    # Computed balance field - UPDATED for multiple accounts aggregation
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
    
    # ADDED: Individual account balances for form view
    individual_balances = fields.Text(
        string='Individual Account Balances',
        compute='_compute_individual_balances'
    )

    # Add SQL constraints for company consistency
    _sql_constraints = [
        ('unique_config_company', 'unique(config_id, company_id)', 
         'Dashboard record must be unique per configuration and company!'),
    ]

    @api.depends('account_ids')
    def _compute_account_info(self):
        """Compute account codes and names from selected accounts"""
        for record in self:
            if record.account_ids:
                # Sort accounts by code for consistent display
                sorted_accounts = record.account_ids.sorted('code')
                record.account_codes = ', '.join(sorted_accounts.mapped('code'))
                record.account_names = ', '.join(sorted_accounts.mapped('name'))
            else:
                record.account_codes = ''
                record.account_names = ''

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

    @api.depends('account_ids', 'company_id')
    def _compute_current_balance(self):
        """Compute aggregated current balance for all selected accounts with date filtering support"""
        for record in self:
            if record.account_ids and record.company_id:
                total_balance = 0.0
                
                # Calculate balance for each account
                for account in record.account_ids:
                    # Base domain for filtering account move lines
                    domain = [
                        ('account_id', '=', account.id),
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
                    account_balance = debit_total - credit_total
                    
                    total_balance += account_balance
                
                record.current_balance = total_balance
            else:
                record.current_balance = 0.0

    @api.depends('account_ids', 'company_id')
    def _compute_individual_balances(self):
        """Compute individual balances for each account for form view display"""
        for record in self:
            if record.account_ids and record.company_id:
                balances_data = []
                
                for account in record.account_ids.sorted('code'):
                    # Base domain for filtering account move lines
                    domain = [
                        ('account_id', '=', account.id),
                        ('company_id', '=', record.company_id.id),
                        ('move_id.state', '=', 'posted')
                    ]
                    
                    # Add date filtering from context (if provided)
                    date_from = self.env.context.get('date_from')
                    date_to = self.env.context.get('date_to')
                    
                    if date_from:
                        domain.append(('date', '>=', date_from))
                    if date_to:
                        domain.append(('date', '<=', date_to))
                    
                    # Calculate individual account balance
                    account_moves = self.env['account.move.line'].search(domain)
                    debit_total = sum(account_moves.mapped('debit'))
                    credit_total = sum(account_moves.mapped('credit'))
                    account_balance = debit_total - credit_total
                    
                    # Format balance for display
                    try:
                        if record.currency_id:
                            if hasattr(record.currency_id, 'format'):
                                formatted_balance = record.currency_id.format(account_balance)
                            else:
                                symbol = getattr(record.currency_id, 'symbol', '') or getattr(record.currency_id, 'name', '')
                                formatted_balance = f"{symbol} {account_balance:,.2f}".strip()
                        else:
                            formatted_balance = f"{account_balance:,.2f}"
                    except Exception:
                        formatted_balance = f"{account_balance:,.2f}"
                    
                    balances_data.append({
                        'code': account.code,
                        'name': account.name,
                        'balance': account_balance,
                        'formatted_balance': formatted_balance
                    })
                
                # Store as JSON for easy access in form view
                record.individual_balances = json.dumps(balances_data)
            else:
                record.individual_balances = json.dumps([])

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

    @api.depends('account_ids', 'company_id')
    def _kanban_dashboard_graph(self):
        """Generate chart data for dashboard_graph widget (following Odoo pattern)"""
        for record in self:
            if not record.account_ids or not record.company_id:
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
            
            # Get daily balances for the date range - UPDATED for multiple accounts
            daily_balances = record._get_daily_balances_multiple_accounts(date_from, date_to)
            
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
                'key': record.display_name or record.account_codes
            }]
            
            # Store as JSON for dashboard_graph widget
            record.kanban_dashboard_graph = json.dumps(chart_data)

    def _get_daily_balances_multiple_accounts(self, date_from, date_to):
        """Calculate daily running balances for multiple accounts within date range"""
        if not self.account_ids or not self.company_id:
            return {}
        
        # Get all move lines for all accounts up to date_to (to calculate running balance)
        domain = [
            ('account_id', 'in', self.account_ids.ids),
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
        ], order='sequence, account_codes')
        
        if not active_configs:
            # No configuration, return empty or auto-suggest
            return []
        
        dashboard_data = []
        
        for config in active_configs:
            # Search for existing dashboard record for this company
            dashboard_record = self.search([
                ('config_id', '=', config.id),
                ('company_id', '=', company_id)
            ], limit=1)
            
            if not dashboard_record:
                dashboard_record = self.create({
                    'config_id': config.id,
                    'account_ids': [(6, 0, config.account_ids.ids)],
                    'company_id': company_id,
                })
            
            dashboard_data.append({
                'id': dashboard_record.id,
                'account_codes': dashboard_record.account_codes,
                'account_names': dashboard_record.account_names,
                'display_name': dashboard_record.display_name,
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
        configured_config_ids = [config.id for config in all_configs]
        
        # Find dashboard records that don't have corresponding active configuration
        all_dashboard_records = self.search([])
        for dashboard_record in all_dashboard_records:
            if dashboard_record.config_id.id not in configured_config_ids:
                dashboard_record.unlink()  # Remove orphaned dashboard records

    def get_filtered_balance_info(self):
        """Get balance information with current context (including date filters)"""
        # This method can be called to get balance info with current filtering applied
        result = {}
        for record in self:
            result[record.id] = {
                'account_codes': record.account_codes,
                'display_name': record.display_name,
                'current_balance': record.current_balance,
                'balance_display': record.balance_display,
                'balance_color': record.balance_color,
                'individual_balances': json.loads(record.individual_balances) if record.individual_balances else [],
                'date_from': self.env.context.get('date_from'),
                'date_to': self.env.context.get('date_to'),
            }
        return result

    def get_individual_balances_list(self):
        """Get individual account balances as a list for form view"""
        self.ensure_one()
        if self.individual_balances:
            return json.loads(self.individual_balances)
        return []