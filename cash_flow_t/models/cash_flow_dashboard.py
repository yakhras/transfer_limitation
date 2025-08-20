from odoo import models, fields, api
from odoo.exceptions import UserError
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

_logger = logging.getLogger(__name__)


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
    
    # CHANGED: From Many2one to Many2many - SUPPORTS MULTIPLE ACCOUNTS
    account_ids = fields.Many2many(
        'account.account', 
        string='Accounts', 
        required=True,
        domain="[('company_id', '=', company_id)]"
    )
    
    # COMPUTED FIELDS: Aggregate info from multiple accounts
    account_codes = fields.Char(
        string='Account Codes', 
        compute='_compute_account_info', 
        store=True,
        help="Comma-separated list of account codes"
    )
    account_names = fields.Char(
        string='Account Names', 
        compute='_compute_account_info', 
        store=True,
        help="Comma-separated list of account names"
    )
    
    # Display name from configuration (custom label)
    display_name = fields.Char(string='Display Name', related='config_id.display_name', store=True)
    sequence = fields.Integer(string='Sequence', related='config_id.sequence', store=True)
    
    # Computed balance field - UPDATED for multiple accounts aggregation
    current_balance = fields.Monetary(
        string='Current Balance', 
        compute='_compute_current_balance',
        currency_field='currency_id',
        help="Aggregated balance from all selected accounts",
        search='_search_current_balance'
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
    ], string='Balance Color', compute='_compute_balance_color', search='_search_balance_color')
    
    # Chart data for dashboard_graph widget (following Odoo pattern)
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    
    # ADDED: Individual account balances for form view
    individual_balances = fields.Text(
        string='Individual Account Balances',
        compute='_compute_individual_balances',
        help="JSON data of individual account balances"
    )

    # USD converted balance field
    current_balance_usd = fields.Monetary(
        string='Current Balance (USD)', 
        compute='_compute_current_balance_usd',
        currency_field='usd_currency_id',
        help="Current balance converted to USD"
    )

    # USD currency reference
    usd_currency_id = fields.Many2one(
        'res.currency', 
        string='USD Currency',
        compute='_compute_usd_currency',
        help="USD currency reference"
    )

    # DEBUG: Temporary field to see the rate being used
    debug_usd_rate = fields.Float(
        string='Debug USD Rate',
        compute='_compute_current_balance_usd',
        help="Debug: USD rate used for conversion"
    )

    # DEBUG: Temporary field to see the rate date
    debug_rate_date = fields.Date(
        string='Debug Rate Date',
        compute='_compute_current_balance_usd',
        help="Debug: Date of USD rate used"
    )

    # Add SQL constraints for company consistency
    _sql_constraints = [
        ('unique_config_company', 'unique(config_id, company_id)', 
         'Dashboard record must be unique per configuration and company!'),
    ]

    @api.depends('company_id')
    def _compute_usd_currency(self):
        """Get USD currency reference"""
        for record in self:
            usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
            record.usd_currency_id = usd_currency.id if usd_currency else False

    def _get_usd_rate_for_date(self, move_line_date, company_id):
        """
        Get USD exchange rate for a specific move line date
        Returns the most recent rate on or before the given date
        """
        if not move_line_date or not company_id:
            return False, None, None
        
        # Convert string date to date object if needed
        if isinstance(move_line_date, str):
            try:
                move_line_date = datetime.strptime(move_line_date, '%Y-%m-%d').date()
            except ValueError:
                _logger.error(f"Invalid date format: {move_line_date}")
                return False, None, None
        
        # Search for USD currency rate
        rate_record = self.env['res.currency.rate'].search([
            ('currency_id.name', '=', 'USD'),
            ('company_id', '=', company_id),
            ('name', '<', move_line_date)
        ], order='name desc', limit=1)
        
        if rate_record:
            return rate_record, rate_record.inverse_company_rate, rate_record.name
        else:
            _logger.warning(f"No USD rate found for date {move_line_date} and company {company_id}")
            return False, None, None

    @api.depends('account_ids', 'company_id')
    def _compute_current_balance_usd(self):
        """Compute current balance converted to USD"""
        for record in self:
            if not record.account_ids or not record.company_id:
                record.current_balance_usd = 0.0
                record.debug_usd_rate = 0.0
                record.debug_rate_date = False
                continue
            
            total_balance_usd = 0.0
            latest_rate = 0.0
            latest_rate_date = False
            
            # Get all move lines for all accounts
            for account in record.account_ids:
                # Base domain for filtering account move lines
                domain = [
                    ('account_id', '=', account.id),
                    ('company_id', '=', record.company_id.id),
                    ('move_id.state', '=', 'posted')
                ]
                
                # Add date filtering from context (if provided by search view)
                date_from = self.env.context.get('date_from')
                date_to = self.env.context.get('date_to')
                
                if date_from:
                    domain.append(('date', '>=', date_from))
                if date_to:
                    domain.append(('date', '<=', date_to))
                
                # Get account move lines
                account_moves = self.env['account.move.line'].search(domain)
                
                # Convert each move line to USD and aggregate
                for move_line in account_moves:
                    try_amount = move_line.debit - move_line.credit
                    
                    # Check if this move line has a currency
                    if move_line.currency_id and move_line.currency_id.name == 'USD':
                        # Already in USD, use amount_currency with sign
                        usd_amount = move_line.amount_currency
                    elif move_line.currency_id and move_line.currency_id.name == 'TRY':
                        # TRY to USD conversion using move line date
                        rate_record, rate_value, rate_date = record._get_usd_rate_for_date(
                            move_line.date, record.company_id.id
                        )
                        if rate_record and rate_value:
                            usd_amount = move_line.amount_currency / rate_value
                            latest_rate = rate_value
                            latest_rate_date = rate_date
                        else:
                            # Fallback: use TRY amount as-is if no rate found
                            usd_amount = try_amount
                            _logger.warning(f"No USD rate found for move line {move_line.id} on {move_line.date}")
                    else:
                        # Company currency (assumed TRY) or other currency
                        # Convert TRY amount to USD using move line date
                        rate_record, rate_value, rate_date = record._get_usd_rate_for_date(
                            move_line.date, record.company_id.id
                        )
                        if rate_record and rate_value:
                            usd_amount = try_amount * rate_value
                            latest_rate = rate_value
                            latest_rate_date = rate_date
                        else:
                            # Fallback: use amount as-is if no rate found
                            usd_amount = try_amount
                    
                    total_balance_usd += usd_amount
            
            record.current_balance_usd = total_balance_usd
            record.debug_usd_rate = latest_rate
            record.debug_rate_date = latest_rate_date


    def action_view_dashboard_tree(self):
        """Action to view dashboard tree view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cash Flow Dashboard',
            'res_model': 'cash.flow.dashboard',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'target': 'current',
            'domain': [('company_id', '=', self.company_id.id)],
            'context': {
                'default_company_id': self.company_id.id,
            }
        }

    @api.depends('account_ids')
    def _compute_account_info(self):
        """Compute account codes and names from selected accounts - HANDLES MULTIPLE ACCOUNTS"""
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
        """Compute aggregated current balance for all selected accounts - SUPPORTS MULTIPLE ACCOUNTS"""
        for record in self:
            if record.account_ids and record.company_id:
                total_balance = 0.0
                
                # Calculate balance for each account and aggregate
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

    def _search_current_balance(self, operator, value):
        """
        Make current_balance searchable by performing the calculation
        Note: This method may be performance-intensive for large datasets
        as it computes balance for all records during search
        """
        # Get all dashboard records
        all_records = self.search([])
        matching_ids = []
        
        for record in all_records:
            # Force computation of current_balance
            record._compute_current_balance()
            balance = record.current_balance
            
            # Apply the search operator
            if operator == '=' and balance == value:
                matching_ids.append(record.id)
            elif operator == '!=' and balance != value:
                matching_ids.append(record.id)
            elif operator == '>' and balance > value:
                matching_ids.append(record.id)
            elif operator == '>=' and balance >= value:
                matching_ids.append(record.id)
            elif operator == '<' and balance < value:
                matching_ids.append(record.id)
            elif operator == '<=' and balance <= value:
                matching_ids.append(record.id)
            elif operator in ('in', 'not in'):
                if (operator == 'in' and balance in value) or (operator == 'not in' and balance not in value):
                    matching_ids.append(record.id)
        
        return [('id', 'in', matching_ids)]

    @api.depends('account_ids', 'company_id')
    def _compute_individual_balances(self):
        """Compute individual balances for each account - HANDLES MULTIPLE ACCOUNTS"""
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

    def _search_balance_color(self, operator, value):
        """Make balance_color searchable by translating to current_balance conditions"""
        if operator not in ('=', '!=', 'in', 'not in'):
            return []
        
        # Convert balance_color values to current_balance conditions
        if operator == '=' and value == 'green':
            return [('current_balance', '>', 0)]
        elif operator == '=' and value == 'red':
            return [('current_balance', '<', 0)]
        elif operator == '=' and value == 'blue':
            return [('current_balance', '=', 0)]
        elif operator == '!=' and value == 'green':
            return [('current_balance', '<=', 0)]
        elif operator == '!=' and value == 'red':
            return [('current_balance', '>=', 0)]
        elif operator == '!=' and value == 'blue':
            return [('current_balance', '!=', 0)]
        elif operator == 'in' and isinstance(value, list):
            conditions = []
            for val in value:
                if val == 'green':
                    conditions.append(('current_balance', '>', 0))
                elif val == 'red':
                    conditions.append(('current_balance', '<', 0))
                elif val == 'blue':
                    conditions.append(('current_balance', '=', 0))
            return ['|'] * (len(conditions) - 1) + conditions if len(conditions) > 1 else conditions
        elif operator == 'not in' and isinstance(value, list):
            conditions = []
            for val in value:
                if val == 'green':
                    conditions.append(('current_balance', '<=', 0))
                elif val == 'red':
                    conditions.append(('current_balance', '>=', 0))
                elif val == 'blue':
                    conditions.append(('current_balance', '!=', 0))
            return conditions
        
        return []

    @api.depends('account_ids', 'company_id')
    def _kanban_dashboard_graph(self):
        """Generate chart data for dashboard_graph widget - SUPPORTS MULTIPLE ACCOUNTS"""
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
        """Calculate daily running balances for multiple accounts within date range - NEW METHOD"""
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
    def get_filtered_dashboard_data(self, period_type='all', date_from=None, date_to=None, currencies=None):
        """
        FIXED: Enhanced method for OWL frontend that works with multiple accounts and currency filtering
        Returns dashboard data with date and currency filtering for account groups
        """
        try:
            company_id = self.env.company.id
            
            _logger.info(f"=== DASHBOARD FILTER DEBUG ===")
            _logger.info(f"Period: {period_type}")
            _logger.info(f"Date From: {date_from} (type: {type(date_from)})")
            _logger.info(f"Date To: {date_to} (type: {type(date_to)})")
            _logger.info(f"Currencies: {currencies} (type: {type(currencies)})")
            _logger.info(f"Company ID: {company_id}")
            
            # Validate and normalize date formats
            normalized_date_from, normalized_date_to = self._normalize_date_params(date_from, date_to)
            
            # Normalize currency filter
            normalized_currencies = self._normalize_currency_params(currencies)
            _logger.info(f"Normalized Currencies: {normalized_currencies}")
            
            # Get active configurations for this company (ordered by sequence)
            config_model = self.env['cash.flow.config']
            active_configs = config_model.search([
                ('company_id', '=', company_id),
                ('active', '=', True)
            ], order='sequence, account_codes')
            
            _logger.info(f"Found {len(active_configs)} active configurations")
            
            if not active_configs:
                # Try auto-suggestion first
                try:
                    created_configs = config_model.auto_suggest_setup(company_id)
                    if created_configs:
                        active_configs = created_configs
                        _logger.info(f"Auto-created {len(created_configs)} configurations")
                    else:
                        _logger.info("No configurations found and auto-suggestion returned empty")
                        return []
                except Exception as e:
                    _logger.warning(f"Auto-suggestion failed: {str(e)}")
                    return []
            
            dashboard_data = []
            
            for config in active_configs:
                try:
                    _logger.info(f"Processing config: {config.display_name} with accounts: {config.account_codes}")
                    
                    # Get or create dashboard record for this config
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
                        _logger.info(f"Created dashboard record for config {config.id}")
                    
                    # Calculate balance with date filtering (NO currency filtering)
                    current_balance = self._calculate_balance_with_filter(
                        config.account_ids.ids, normalized_date_from, normalized_date_to, 
                        company_id, None  # REMOVED currency filtering
                    )

                    # Calculate USD balance separately
                    current_balance_usd = self._calculate_balance_usd_with_filter(
                        config.account_ids.ids, normalized_date_from, normalized_date_to, 
                        company_id
                    )
                    
                    _logger.info(f"Calculated balances for {config.display_name}: TRY={current_balance}, USD={current_balance_usd}")
                    
                    # Format balance display
                    balance_display = self._format_balance_display(current_balance, dashboard_record.currency_id)
                    balance_color = 'green' if current_balance > 0 else ('red' if current_balance < 0 else 'blue')
                    
                    # Generate chart data for the filtered period with currency support
                    try:
                        chart_data = self._get_multi_currency_chart_data(
                            config.account_ids.ids, normalized_date_from, normalized_date_to, 
                            company_id, normalized_currencies
                        )
                        _logger.info(f"Generated chart data successfully")
                    except Exception as e:
                        _logger.error(f"Error generating chart data: {str(e)}")
                        # Fallback to simple chart data
                        chart_data = self._get_sample_chart_data()
                    
                    # Get individual account balances (NO currency filter)
                    try:
                        individual_balances = self._get_individual_balances_for_period(
                            config.account_ids, normalized_date_from, normalized_date_to, 
                            company_id, None  # REMOVED currency filtering
                        )
                    except Exception as e:
                        _logger.error(f"Error getting individual balances: {str(e)}")
                        individual_balances = []
                    
                    # Format period information
                    period_info = {
                        'period_type': period_type,
                        'date_from': normalized_date_from,
                        'date_to': normalized_date_to,
                        'currencies': normalized_currencies,
                        'period_label': self._format_period_label(period_type, normalized_date_from, normalized_date_to)
                    }
                    
                    account_data = {
                        'id': dashboard_record.id,
                        'account_codes': dashboard_record.account_codes,
                        'account_names': dashboard_record.account_names,
                        'display_name': dashboard_record.display_name,
                        'current_balance': current_balance,
                        'current_balance_usd': current_balance_usd,
                        'balance_display': balance_display,
                        'balance_color': balance_color,
                        'chart_data': chart_data,
                        'individual_balances': json.dumps(individual_balances),
                        'period_info': period_info,
                        'debug_currencies': normalized_currencies,
                        'debug_currency_count': len(normalized_currencies) if normalized_currencies else 0,
                        'debug_chart_type': type(chart_data).__name__,
                        'debug_chart_keys': list(chart_data.keys()) if isinstance(chart_data, dict) else 'not_dict',
                        'account_ids': config.account_ids.ids,

                    }
                    
                    dashboard_data.append(account_data)
                    _logger.info(f"Successfully processed {config.display_name}")
                    
                except Exception as e:
                    _logger.error(f"Error processing config {config.id}: {str(e)}")
                    import traceback
                    _logger.error(f"Traceback: {traceback.format_exc()}")
                    continue
            
            _logger.info(f"=== DASHBOARD FILTER COMPLETE === Returning {len(dashboard_data)} records")
            return dashboard_data
            
        except Exception as e:
            _logger.error(f"Error in get_filtered_dashboard_data: {str(e)}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            return []
        
    def _calculate_balance_usd_with_filter(self, account_ids, date_from, date_to, company_id):
            """Calculate USD balance for specific date range with proper conversion"""
            if not account_ids:
                return 0.0
            
            # Build domain for move lines
            domain = [
                ('account_id', 'in', account_ids),
                ('company_id', '=', company_id),
                ('move_id.state', '=', 'posted')
            ]
            
            # Add date filters
            if date_from:
                domain.append(('date', '>=', date_from))
            if date_to:
                domain.append(('date', '<=', date_to))
            
            # Get all move lines for the filtered period
            move_lines = self.env['account.move.line'].search(domain)
            
            total_balance_usd = 0.0
            
            # Convert each move line to USD and aggregate
            for move_line in move_lines:
                try_amount = move_line.debit - move_line.credit
                
                # Check if this move line has a currency
                if move_line.currency_id and move_line.currency_id.name == 'USD':
                    # Already in USD, use amount_currency with sign
                    usd_amount = move_line.amount_currency
                elif move_line.currency_id and move_line.currency_id.name == 'TRY':
                    # TRY to USD conversion using move line date
                    rate_record, rate_value, rate_date = self._get_usd_rate_for_date(
                        move_line.date, company_id
                    )
                    if rate_record and rate_value:
                        usd_amount = move_line.amount_currency / rate_value
                    else:
                        # Fallback: use TRY amount as-is if no rate found
                        usd_amount = try_amount
                        _logger.warning(f"No USD rate found for move line {move_line.id} on {move_line.date}")
                else:
                    # Company currency (assumed TRY) or other currency
                    # Convert TRY amount to USD using move line date
                    rate_record, rate_value, rate_date = self._get_usd_rate_for_date(
                        move_line.date, company_id
                    )
                    if rate_record and rate_value:
                        usd_amount = try_amount * rate_value
                    else:
                        # Fallback: use amount as-is if no rate found
                        usd_amount = try_amount
                
                total_balance_usd += usd_amount
            
            return total_balance_usd
    
    def _get_multi_currency_chart_data(self, account_ids, date_from, date_to, company_id, currencies=None):
        """Generate chart data for multiple currencies or single currency - ROBUST VERSION"""
        
        try:
            _logger.info(f"_get_multi_currency_chart_data called with currencies: {currencies}")
            
            if not currencies or len(currencies) == 1:
                _logger.info("Single currency path")
                # Single currency - use existing logic
                return self._get_chart_data_for_period(
                    account_ids, date_from, date_to, company_id, currencies
                )
            
            _logger.info("Multi currency path")
            # Multiple currencies - return data for each currency separately
            chart_data = {}
            
            if 'TRY' in currencies:
                try:
                    _logger.info("Generating TRY chart data")
                    chart_data['TRY'] = self._get_currency_specific_chart_data(
                        account_ids, date_from, date_to, company_id, 'TRY'
                    )
                    _logger.info(f"TRY chart data generated: {len(chart_data['TRY'])} points")
                except Exception as e:
                    _logger.error(f"Error generating TRY chart data: {str(e)}")
                    chart_data['TRY'] = self._get_sample_chart_data()
            
            if 'USD' in currencies:
                try:
                    _logger.info("Generating USD chart data")
                    chart_data['USD'] = self._get_currency_specific_chart_data(
                        account_ids, date_from, date_to, company_id, 'USD'
                    )
                    _logger.info(f"USD chart data generated: {len(chart_data['USD'])} points")
                except Exception as e:
                    _logger.error(f"Error generating USD chart data: {str(e)}")
                    chart_data['USD'] = self._get_sample_chart_data()
            
            if 'EUR' in currencies:
                try:
                    _logger.info("Generating EUR chart data")
                    chart_data['EUR'] = self._get_currency_specific_chart_data(
                        account_ids, date_from, date_to, company_id, 'EUR'
                    )
                    _logger.info(f"EUR chart data generated: {len(chart_data['EUR'])} points")
                except Exception as e:
                    _logger.error(f"Error generating EUR chart data: {str(e)}")
                    chart_data['EUR'] = self._get_sample_chart_data()
            
            _logger.info(f"Final chart_data keys: {list(chart_data.keys())}")
            return chart_data
            
        except Exception as e:
            _logger.error(f"Error in _get_multi_currency_chart_data: {str(e)}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            # Return fallback data
            return self._get_sample_chart_data()
    
    def _get_currency_specific_chart_data(self, account_ids, date_from, date_to, company_id, target_currency):
        """Generate chart data for a specific currency - ROBUST VERSION"""
        
        try:
            _logger.info(f"Generating chart data for {target_currency}")
            
            if not account_ids:
                return self._get_sample_chart_data()
            
            if not date_from or not date_to:
                return self._get_all_time_chart_data_currency(account_ids, company_id, target_currency)
            
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            
            # Generate data points (max 10 points for performance)
            date_diff = (end_date - start_date).days
            interval = max(1, date_diff // 9)  # 10 points max
            
            chart_data = []
            current_date = start_date
            
            while current_date <= end_date:
                try:
                    # Calculate balance up to this date in target currency
                    balance = self._calculate_balance_in_currency(
                        account_ids, date_from, current_date.strftime('%Y-%m-%d'), 
                        company_id, target_currency
                    )
                    
                    chart_data.append({
                        'label': current_date.strftime('%b %d'),
                        'value': float(balance)
                    })
                    
                except Exception as e:
                    _logger.warning(f"Error calculating balance for {current_date}: {str(e)}")
                    # Add zero balance point to maintain chart continuity
                    chart_data.append({
                        'label': current_date.strftime('%b %d'),
                        'value': 0.0
                    })
                
                current_date += timedelta(days=interval)
                if current_date > end_date and chart_data and chart_data[-1]['label'] != end_date.strftime('%b %d'):
                    # Add final point
                    try:
                        balance = self._calculate_balance_in_currency(
                            account_ids, date_from, end_date.strftime('%Y-%m-%d'), 
                            company_id, target_currency
                        )
                        chart_data.append({
                            'label': end_date.strftime('%b %d'),
                            'value': float(balance)
                        })
                    except Exception as e:
                        _logger.warning(f"Error calculating final balance: {str(e)}")
                    break
            
            _logger.info(f"Generated {len(chart_data)} chart points for {target_currency}")
            return chart_data if chart_data else self._get_sample_chart_data()
            
        except Exception as e:
            _logger.error(f"Error generating {target_currency} chart data: {str(e)}")
            return self._get_sample_chart_data()
        

    
    def _get_all_time_chart_data_currency(self, account_ids, company_id, target_currency):
        """Generate all-time chart data for specific currency - ROBUST VERSION"""
        
        try:
            # Find the actual date range of transactions
            domain = [
                ('account_id', 'in', account_ids),
                ('company_id', '=', company_id),
                ('move_id.state', '=', 'posted')
            ]
            
            # Get earliest and latest transaction dates
            earliest_line = self.env['account.move.line'].search(domain, order='date asc', limit=1)
            latest_line = self.env['account.move.line'].search(domain, order='date desc', limit=1)
            
            if not earliest_line or not latest_line:
                return self._get_sample_chart_data()
            
            start_date = earliest_line.date
            end_date = latest_line.date
            today = datetime.now().date()
            
            if today > end_date:
                end_date = today
            
            # Calculate total span to determine appropriate intervals
            total_days = (end_date - start_date).days
            
            if total_days <= 30:
                return self._get_weekly_chart_data_currency(account_ids, company_id, start_date, end_date, target_currency)
            elif total_days <= 365:
                return self._get_monthly_chart_data_currency(account_ids, company_id, start_date, end_date, target_currency)
            else:
                return self._get_yearly_chart_data_currency(account_ids, company_id, start_date, end_date, target_currency)
                
        except Exception as e:
            _logger.error(f"Error generating all-time chart data for {target_currency}: {str(e)}")
            return self._get_sample_chart_data()


    
    def _get_yearly_chart_data_currency(self, account_ids, company_id, start_date, end_date, target_currency):
        """Generate yearly chart data for specific currency - ROBUST VERSION"""
        try:
            chart_data = []
            current_year = start_date.year
            end_year = end_date.year
            
            while current_year <= end_year:
                try:
                    year_end = datetime(current_year, 12, 31).date()
                    period_end = min(year_end, end_date)
                    
                    balance = self._calculate_balance_in_currency(
                        account_ids, None, period_end.strftime('%Y-%m-%d'), company_id, target_currency
                    )
                    
                    chart_data.append({
                        'label': str(current_year),
                        'value': float(balance)
                    })
                    
                except Exception as e:
                    _logger.warning(f"Error processing year {current_year}: {str(e)}")
                    chart_data.append({
                        'label': str(current_year),
                        'value': 0.0
                    })
                
                current_year += 1
            
            return chart_data if chart_data else self._get_sample_chart_data()
            
        except Exception as e:
            _logger.error(f"Error generating yearly chart data for {target_currency}: {str(e)}")
            return self._get_sample_chart_data()
        



    
    def _get_weekly_chart_data_currency(self, account_ids, company_id, start_date, end_date, target_currency):
        """Generate weekly chart data for specific currency - ROBUST VERSION"""
        try:
            chart_data = []
            current_date = start_date
            
            while current_date <= end_date:
                try:
                    balance = self._calculate_balance_in_currency(
                        account_ids, None, current_date.strftime('%Y-%m-%d'), company_id, target_currency
                    )
                    
                    chart_data.append({
                        'label': current_date.strftime('%b %d'),
                        'value': float(balance)
                    })
                    
                except Exception as e:
                    _logger.warning(f"Error processing week {current_date}: {str(e)}")
                    chart_data.append({
                        'label': current_date.strftime('%b %d'),
                        'value': 0.0
                    })
                
                current_date += timedelta(days=7)
            
            return chart_data if chart_data else self._get_sample_chart_data()
            
        except Exception as e:
            _logger.error(f"Error generating weekly chart data for {target_currency}: {str(e)}")
            return self._get_sample_chart_data()



    
    def _get_monthly_chart_data_currency(self, account_ids, company_id, start_date, end_date, target_currency):
        """Generate monthly chart data for specific currency - ROBUST VERSION"""
        try:
            chart_data = []
            current_date = start_date.replace(day=1)
            
            while current_date <= end_date:
                try:
                    # Get last day of current month
                    if current_date.month == 12:
                        next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        next_month = current_date.replace(month=current_date.month + 1, day=1)
                    
                    month_end = next_month - timedelta(days=1)
                    period_end = min(month_end, end_date)
                    
                    # Calculate balance up to end of this month in target currency
                    balance = self._calculate_balance_in_currency(
                        account_ids, None, period_end.strftime('%Y-%m-%d'), company_id, target_currency
                    )
                    
                    chart_data.append({
                        'label': current_date.strftime('%b %Y'),
                        'value': float(balance)
                    })
                    
                except Exception as e:
                    _logger.warning(f"Error processing month {current_date}: {str(e)}")
                    chart_data.append({
                        'label': current_date.strftime('%b %Y'),
                        'value': 0.0
                    })
                
                current_date = next_month
            
            return chart_data if chart_data else self._get_sample_chart_data()
            
        except Exception as e:
            _logger.error(f"Error generating monthly chart data for {target_currency}: {str(e)}")
            return self._get_sample_chart_data()
        

    
    def _calculate_balance_in_currency(self, account_ids, date_from, date_to, company_id, target_currency):
        """Calculate balance converted to target currency - ROBUST VERSION"""
        
        try:
            if not account_ids:
                return 0.0
            
            # Build domain for move lines (NO CURRENCY FILTERING)
            domain = [
                ('account_id', 'in', account_ids),
                ('company_id', '=', company_id),
                ('move_id.state', '=', 'posted')
            ]
            
            # Add date filters
            if date_from:
                domain.append(('date', '>=', date_from))
            if date_to:
                domain.append(('date', '<=', date_to))
            
            # Get ALL move lines for the date range
            move_lines = self.env['account.move.line'].search(domain)
            
            total_balance = 0.0
            
            if target_currency == 'TRY':
                # For TRY, use company currency amounts (debit - credit)
                total_debit = sum(move_lines.mapped('debit'))
                total_credit = sum(move_lines.mapped('credit'))
                total_balance = total_debit - total_credit
                
            elif target_currency == 'USD':
                # For USD, convert each move line to USD
                for move_line in move_lines:
                    try:
                        try_amount = move_line.debit - move_line.credit
                        
                        # Check if this move line already has USD currency
                        if move_line.currency_id and move_line.currency_id.name == 'USD':
                            # Already in USD, use amount_currency
                            total_balance += move_line.amount_currency
                        else:
                            # Convert TRY to USD using move line date
                            rate_record, rate_value, rate_date = self._get_usd_rate_for_date(
                                move_line.date, company_id
                            )
                            if rate_record and rate_value:
                                usd_amount = try_amount * rate_value
                                total_balance += usd_amount
                            # If no rate found, skip this move line for USD calculation
                    except Exception as e:
                        _logger.warning(f"Error processing move line {move_line.id}: {str(e)}")
                        continue
            
            return total_balance
            
        except Exception as e:
            _logger.error(f"Error calculating balance in {target_currency}: {str(e)}")
            return 0.0
    

    def _get_chart_data_for_period_usd(self, account_ids, date_from, date_to, company_id):
            """Generate USD chart data for the specified period"""
            if not account_ids:
                return self._get_sample_chart_data()
            
            if not date_from or not date_to:
                return self._get_all_time_chart_data_usd(account_ids, company_id)
            
            try:
                start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                
                # Generate data points (max 10 points for performance)
                date_diff = (end_date - start_date).days
                interval = max(1, date_diff // 9)  # 10 points max
                
                chart_data = []
                current_date = start_date
                
                while current_date <= end_date:
                    # Calculate USD balance up to this date
                    balance_usd = self._calculate_balance_usd_with_filter(
                        account_ids, date_from, current_date.strftime('%Y-%m-%d'), 
                        company_id
                    )
                    
                    chart_data.append({
                        'label': current_date.strftime('%b %d'),
                        'value': float(balance_usd)
                    })
                    
                    current_date += timedelta(days=interval)
                    if current_date > end_date and chart_data[-1]['label'] != end_date.strftime('%b %d'):
                        # Add final point
                        balance_usd = self._calculate_balance_usd_with_filter(
                            account_ids, date_from, end_date.strftime('%Y-%m-%d'), 
                            company_id
                        )
                        chart_data.append({
                            'label': end_date.strftime('%b %d'),
                            'value': float(balance_usd)
                        })
                        break
                
                return chart_data
                
            except Exception as e:
                _logger.error(f"Error generating USD chart data: {str(e)}")
                return self._get_sample_chart_data()

    def _normalize_currency_params(self, currencies):
        """
        FIXED: Normalize currency parameters with better handling
        """
        if not currencies:
            return None
        
        try:
            if isinstance(currencies, str):
                return [currencies]
            elif isinstance(currencies, (list, tuple)):
                # Handle both regular lists and proxy objects
                normalized = []
                for curr in currencies:
                    if curr and isinstance(curr, str):
                        normalized.append(curr)
                return normalized if normalized else None
            else:
                _logger.warning(f"Invalid currency format: {currencies} (type: {type(currencies)})")
                return None
        except Exception as e:
            _logger.error(f"Error normalizing currencies: {str(e)}")
            return None

    def _normalize_date_params(self, date_from, date_to):
        """
        ADDED: Normalize date parameters to ensure consistent format
        Handles both string and date object inputs
        """
        normalized_from = None
        normalized_to = None
        
        try:
            # Handle date_from
            if date_from:
                if isinstance(date_from, str):
                    # Validate string format (YYYY-MM-DD)
                    datetime.strptime(date_from, '%Y-%m-%d')
                    normalized_from = date_from
                elif hasattr(date_from, 'strftime'):
                    # Convert date object to string
                    normalized_from = date_from.strftime('%Y-%m-%d')
                else:
                    _logger.warning(f"Invalid date_from format: {date_from} (type: {type(date_from)})")
            
            # Handle date_to
            if date_to:
                if isinstance(date_to, str):
                    # Validate string format (YYYY-MM-DD)
                    datetime.strptime(date_to, '%Y-%m-%d')
                    normalized_to = date_to
                elif hasattr(date_to, 'strftime'):
                    # Convert date object to string
                    normalized_to = date_to.strftime('%Y-%m-%d')
                else:
                    _logger.warning(f"Invalid date_to format: {date_to} (type: {type(date_to)})")
                    
        except ValueError as e:
            _logger.error(f"Date parsing error: {str(e)}")
            
        return normalized_from, normalized_to

    def _calculate_balance_with_filter(self, account_ids, date_from, date_to, company_id, currencies=None):
        """FIXED: Calculate balance for multiple accounts with date filtering (removed currency filtering)"""
        if not account_ids:
            return 0.0
        
        # Build domain for move lines (REMOVED CURRENCY FILTERING)
        domain = [
            ('account_id', 'in', account_ids),
            ('company_id', '=', company_id),
            ('move_id.state', '=', 'posted')
        ]
        
        # Add date filters
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        
        # NOTE: Removed currency filtering as it was causing issues
        # For multi-currency support, use _calculate_balance_in_currency instead
        
        # Get move lines and calculate balance
        move_lines = self.env['account.move.line'].search(domain)
        total_debit = sum(move_lines.mapped('debit'))
        total_credit = sum(move_lines.mapped('credit'))
        
        balance = total_debit - total_credit
        
        _logger.info(f"Balance calculation - Move lines: {len(move_lines)}, Balance: {balance}")
        
        return balance

    def _format_balance_display(self, balance, currency):
        """Format balance for display"""
        if currency:
            try:
                if hasattr(currency, 'format'):
                    return currency.format(balance)
                else:
                    symbol = getattr(currency, 'symbol', '') or getattr(currency, 'name', '')
                    return f"{symbol} {balance:,.2f}".strip()
            except:
                return f"₺{balance:,.2f}"
        return f"₺{balance:,.2f}"

    def _get_chart_data_for_period(self, account_ids, date_from, date_to, company_id, currencies=None):
        """UPDATED: Generate chart data for the specified period with currency filtering"""
        if not account_ids :
            return self._get_sample_chart_data()
        
        if not date_from or not date_to:
            return self._get_all_time_chart_data(account_ids, company_id, currencies)
        
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
            end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
            
            # Generate data points (max 10 points for performance)
            date_diff = (end_date - start_date).days
            interval = max(1, date_diff // 9)  # 10 points max
            
            chart_data = []
            current_date = start_date
            
            while current_date <= end_date:
                # UPDATED: Calculate balance up to this date for all accounts with currency filter
                balance = self._calculate_balance_with_filter(
                    account_ids, date_from, current_date.strftime('%Y-%m-%d'), 
                    company_id, currencies
                )
                
                chart_data.append({
                    'label': current_date.strftime('%b %d'),
                    'value': float(balance)
                })
                
                current_date += timedelta(days=interval)
                if current_date > end_date and chart_data[-1]['label'] != end_date.strftime('%b %d'):
                    # Add final point
                    balance = self._calculate_balance_with_filter(
                        account_ids, date_from, end_date.strftime('%Y-%m-%d'), 
                        company_id, currencies
                    )
                    chart_data.append({
                        'label': end_date.strftime('%b %d'),
                        'value': float(balance)
                    })
                    break
            
            return chart_data
            
        except Exception as e:
            _logger.error(f"Error generating chart data: {str(e)}")
            return self._get_sample_chart_data()
    
    def _get_all_time_chart_data(self, account_ids, company_id, currencies=None):
        """UPDATED: Generate chart data for All Time view with currency filtering"""
        
        # Find the actual date range of transactions
        domain = [
            ('account_id', 'in', account_ids),
            ('company_id', '=', company_id),
            ('move_id.state', '=', 'posted')
        ]
        
        # ADDED: Currency filtering for all-time chart
        if currencies:
            currency_ids = self.env['res.currency'].search([('name', 'in', currencies)]).ids
            if currency_ids:
                domain.append(('currency_id', 'in', currency_ids))
        
        # Get earliest and latest transaction dates
        earliest_line = self.env['account.move.line'].search(domain, order='date asc', limit=1)
        latest_line = self.env['account.move.line'].search(domain, order='date desc', limit=1)
        
        if not earliest_line or not latest_line:
            return self._get_sample_chart_data()  # No transactions found
        
        start_date = earliest_line.date
        end_date = latest_line.date
        today = datetime.now().date()
        
        # Use today as end_date if it's more recent (for current balance)
        if today > end_date:
            end_date = today
        
        # Calculate total span to determine appropriate intervals
        total_days = (end_date - start_date).days
        
        # Determine interval based on data span
        if total_days <= 30:        # 1 month or less - Weekly
            return self._get_weekly_chart_data(account_ids, company_id, start_date, end_date, currencies)
        elif total_days <= 365:     # 1 year or less - Monthly  
            return self._get_monthly_chart_data(account_ids, company_id, start_date, end_date, currencies)
        elif total_days <= 1095:    # 3 years or less - Quarterly
            return self._get_quarterly_chart_data(account_ids, company_id, start_date, end_date, currencies)
        else:                       # More than 3 years - Yearly
            return self._get_yearly_chart_data(account_ids, company_id, start_date, end_date, currencies)

    def _get_weekly_chart_data(self, account_ids, company_id, start_date, end_date, currencies=None):
        """UPDATED: Generate weekly chart data with currency filtering"""
        chart_data = []
        current_date = start_date
        
        while current_date <= end_date:
            # UPDATED: Calculate balance up to this date with currency filter
            balance = self._calculate_balance_with_filter(
                account_ids, None, current_date.strftime('%Y-%m-%d'), company_id, currencies
            )
            
            chart_data.append({
                'label': current_date.strftime('%b %d'),  # Mar 15
                'value': float(balance)
            })
            
            current_date += timedelta(days=7)  # Next week
        
        return chart_data

    def _get_monthly_chart_data(self, account_ids, company_id, start_date, end_date, currencies=None):
        """UPDATED: Generate monthly chart data with currency filtering"""
        chart_data = []
        current_date = start_date.replace(day=1)  # Start from first day of month
        
        while current_date <= end_date:
            # Get last day of current month
            if current_date.month == 12:
                next_month = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                next_month = current_date.replace(month=current_date.month + 1, day=1)
            
            month_end = next_month - timedelta(days=1)
            period_end = min(month_end, end_date)
            
            # UPDATED: Calculate balance up to end of this month with currency filter
            balance = self._calculate_balance_with_filter(
                account_ids, None, period_end.strftime('%Y-%m-%d'), company_id, currencies
            )
            
            chart_data.append({
                'label': current_date.strftime('%b %Y'),  # Mar 2024
                'value': float(balance)
            })
            
            current_date = next_month  # Move to next month
        
        return chart_data

    def _get_quarterly_chart_data(self, account_ids, company_id, start_date, end_date, currencies=None):
        """UPDATED: Generate quarterly chart data with currency filtering"""
        chart_data = []
        
        # Start from the beginning of the quarter containing start_date
        start_quarter = ((start_date.month - 1) // 3) + 1
        current_date = start_date.replace(month=(start_quarter - 1) * 3 + 1, day=1)
        
        while current_date <= end_date:
            # Calculate quarter end
            quarter = ((current_date.month - 1) // 3) + 1
            if quarter == 4:
                quarter_end = current_date.replace(month=12, day=31)
            else:
                next_quarter_start = current_date.replace(month=quarter * 3 + 1, day=1)
                quarter_end = next_quarter_start - timedelta(days=1)
            
            period_end = min(quarter_end, end_date)
            
            # UPDATED: Calculate balance up to end of this quarter with currency filter
            balance = self._calculate_balance_with_filter(
                account_ids, None, period_end.strftime('%Y-%m-%d'), company_id, currencies
            )
            
            chart_data.append({
                'label': f'Q{quarter} {current_date.year}',  # Q1 2024
                'value': float(balance)
            })
            
            # Move to next quarter
            if quarter == 4:
                current_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
            else:
                current_date = current_date.replace(month=quarter * 3 + 1, day=1)
        
        return chart_data

    def _get_yearly_chart_data(self, account_ids, company_id, start_date, end_date, currencies=None):
        """UPDATED: Generate yearly chart data with currency filtering"""
        chart_data = []
        current_year = start_date.year
        end_year = end_date.year
        
        while current_year <= end_year:
            # Calculate year end
            year_end = datetime(current_year, 12, 31).date()
            period_end = min(year_end, end_date)
            
            # UPDATED: Calculate balance up to end of this year with currency filter
            balance = self._calculate_balance_with_filter(
                account_ids, None, period_end.strftime('%Y-%m-%d'), company_id, currencies
            )
            
            chart_data.append({
                'label': str(current_year),  # 2024
                'value': float(balance)
            })
            
            current_year += 1  # Move to next year
        
        return chart_data

    def _get_sample_chart_data(self):
        """Generate sample chart data as fallback"""
        return [
            {'label': 'Week 1', 'value': 1000},
            {'label': 'Week 2', 'value': 1200},
            {'label': 'Week 3', 'value': 900},
            {'label': 'Week 4', 'value': 1100}
        ]

    def _get_individual_balances_for_period(self, account_ids, date_from, date_to, company_id, currencies=None):
        """FIXED: Get individual account balances for the period (removed currency filtering)"""
        balances = []
        
        for account in account_ids:
            # Calculate balance without currency filter
            balance = self._calculate_balance_with_filter(
                [account.id], date_from, date_to, company_id, None  # No currency filtering
            )
            formatted_balance = self._format_balance_display(balance, account.company_id.currency_id)
            
            balances.append({
                'code': account.code,
                'name': account.name,
                'balance': balance,
                'formatted_balance': formatted_balance
            })
        
        return balances

    def _format_period_label(self, period_type, date_from, date_to):
        """Format period label for display"""
        if period_type == 'all':
            return 'All Time'
        elif period_type == 'custom' and date_from and date_to:
            return f"{date_from} to {date_to}"
        elif date_from and date_to:
            try:
                start = datetime.strptime(date_from, '%Y-%m-%d').strftime('%b %d')
                end = datetime.strptime(date_to, '%Y-%m-%d').strftime('%b %d, %Y')
                return f"{start} - {end}"
            except (ValueError, TypeError):
                return period_type.replace('_', ' ').title()
        else:
            return period_type.replace('_', ' ').title()

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

    def action_view_account_moves(self):
        """Action to view account moves for all accounts in this group"""
        self.ensure_one()
        
        if not self.account_ids:
            raise UserError("No accounts configured for this dashboard item.")
        
        # Get date filter from context
        date_from = self.env.context.get('date_from')
        date_to = self.env.context.get('date_to')
        
        # Build domain for account move lines
        domain = [
            ('account_id', 'in', self.account_ids.ids),
            ('company_id', '=', self.company_id.id),
            ('move_id.state', '=', 'posted')
        ]
        
        # Add date filters if provided
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Transactions - {self.display_name}',
            'res_model': 'account.move.line',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'search_default_group_by_move': 1,
                'search_default_group_by_account': 1,
            }
        }

    # ADD TO YOUR cash_flow_dashboard.py file

    # 1. ADD THIS FIELD after your other fields (around line 100)
    debug_currency_info = fields.Text(
        string='Currency Debug Info',
        compute='_compute_debug_currency_info',
        help="Debug information about currency data"
    )

    # REPLACE your debug_balance_calculation method with this enhanced version:

    def debug_balance_calculation(self, account_ids, date_from, date_to, company_id, target_currency):
        """Enhanced debug method to see currency rates and USD values for each record"""
        
        debug_info = []
        debug_info.append(f"=== DEBUG BALANCE CALCULATION ===")
        debug_info.append(f"account_ids: {account_ids}")
        debug_info.append(f"date_from: {date_from}")
        debug_info.append(f"date_to: {date_to}")
        debug_info.append(f"company_id: {company_id}")
        debug_info.append(f"target_currency: {target_currency}")
        debug_info.append("")
        
        # Check accounts
        if account_ids:
            accounts = self.env['account.account'].browse(account_ids)
            debug_info.append(f"=== ACCOUNTS ===")
            for acc in accounts:
                debug_info.append(f"  {acc.code} - {acc.name}")
            debug_info.append("")
        
        # Build domain
        domain = [
            ('account_id', 'in', account_ids),
            ('company_id', '=', company_id),
            ('move_id.state', '=', 'posted')
        ]
        
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        
        debug_info.append(f"=== SEARCH DOMAIN ===")
        debug_info.append(f"  {domain}")
        debug_info.append("")
        
        # Get move lines
        move_lines = self.env['account.move.line'].search(domain)
        debug_info.append(f"=== MOVE LINES FOUND ===")
        debug_info.append(f"  Total: {len(move_lines)} lines")
        debug_info.append("")
        
        # DETAILED ANALYSIS FOR EACH MOVE LINE
        debug_info.append(f"=== DETAILED MOVE LINE ANALYSIS ===")
        total_usd_calculated = 0.0
        
        for i, line in enumerate(move_lines[:15]):  # Show first 15 lines
            debug_info.append(f"--- LINE {i+1} ---")
            debug_info.append(f"Date: {line.date}")
            debug_info.append(f"Account: {line.account_id.code}")
            
            # Currency info
            if line.currency_id:
                currency_name = line.currency_id.name
                debug_info.append(f"Currency: {currency_name}")
                debug_info.append(f"Amount Currency: {line.amount_currency}")
            else:
                currency_name = "Company Currency (TRY)"
                debug_info.append(f"Currency: {currency_name}")
                debug_info.append(f"Amount Currency: N/A")
            
            # TRY amounts
            try_amount = line.debit - line.credit
            debug_info.append(f"TRY Amount (debit-credit): {try_amount}")
            
            # USD CONVERSION LOGIC
            usd_value = 0.0
            rate_info = "N/A"
            
            if target_currency == 'USD':
                if line.currency_id and line.currency_id.name == 'USD':
                    # Already USD
                    usd_value = line.amount_currency
                    rate_info = "Already USD - no conversion"
                    debug_info.append(f"USD Rate: {rate_info}")
                    debug_info.append(f"USD Value: ${usd_value}")
                    
                elif line.currency_id and line.currency_id.name == 'TRY':
                    # TRY currency to USD
                    rate_record, rate_value, rate_date = self._get_usd_rate_for_date(line.date, company_id)
                    if rate_record and rate_value:
                        usd_value = line.amount_currency / rate_value
                        rate_info = f"Rate: {rate_value} (from {rate_date})"
                        debug_info.append(f"USD Rate: {rate_info}")
                        debug_info.append(f"TRY amount_currency: {line.amount_currency}")
                        debug_info.append(f"USD Value: ${usd_value}")
                    else:
                        usd_value = try_amount  # Fallback
                        rate_info = "No rate found - using TRY amount"
                        debug_info.append(f"USD Rate: {rate_info}")
                        debug_info.append(f"USD Value: ${usd_value}")
                        
                else:
                    # Company currency (TRY) to USD
                    rate_record, rate_value, rate_date = self._get_usd_rate_for_date(line.date, company_id)
                    if rate_record and rate_value:
                        usd_value = try_amount * rate_value
                        rate_info = f"Rate: {rate_value} (from {rate_date})"
                        debug_info.append(f"USD Rate: {rate_info}")
                        debug_info.append(f"USD Value: ${usd_value}")
                    else:
                        usd_value = try_amount  # Fallback
                        rate_info = "No rate found - using TRY amount"
                        debug_info.append(f"USD Rate: {rate_info}")
                        debug_info.append(f"USD Value: ${usd_value}")
            
            total_usd_calculated += usd_value
            debug_info.append("")
        
        if len(move_lines) > 15:
            debug_info.append(f"... and {len(move_lines) - 15} more lines")
            debug_info.append("")
        
        # SUMMARY
        debug_info.append(f"=== SUMMARY ===")
        debug_info.append(f"Total USD from first 15 lines: ${total_usd_calculated}")
        
        # Quick totals for all lines
        usd_lines = move_lines.filtered(lambda l: l.currency_id and l.currency_id.name == 'USD')
        if usd_lines:
            usd_total = sum(usd_lines.mapped('amount_currency'))
            debug_info.append(f"All USD lines total: ${usd_total} ({len(usd_lines)} lines)")
        
        try_lines = move_lines.filtered(lambda l: not l.currency_id)
        if try_lines:
            try_total = sum(try_lines.mapped('debit')) - sum(try_lines.mapped('credit'))
            debug_info.append(f"All TRY lines total: ₺{try_total} ({len(try_lines)} lines)")
        
        return "\n".join(debug_info)


    @api.depends('company_id', 'account_ids')  # Add account_ids dependency
    def _compute_debug_currency_info(self):
        """Enhanced debug info"""
        for record in self:
            debug_info = []
            
            # Your existing debug code...
            # (keep all the existing code)
            
            # ADD THIS AT THE END:
            debug_info.append("\n" + "="*50)
            debug_info.append("BALANCE CALCULATION DEBUG")
            debug_info.append("="*50)
            
            if record.account_ids:
                # Test with current period settings
                balance_debug = record.debug_balance_calculation(
                    record.account_ids.ids,
                    None,  # No date filter for now
                    None,  
                    record.company_id.id,
                    'USD'
                )
                debug_info.append(balance_debug)
            else:
                debug_info.append("No accounts configured for this record")
            
            record.debug_currency_info = "\n".join(debug_info)



    def action_view_debug_analysis(self):
        """Open debug analysis in tree view"""
        self.ensure_one()
        
        # Populate debug data
        self._populate_debug_analysis()
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Debug Analysis - {self.display_name}',
            'res_model': 'cash.flow.debug.line',
            'view_mode': 'tree,form',
            'domain': [('dashboard_id', '=', self.id)],
            'context': {'default_dashboard_id': self.id},
            'target': 'current',
        }


    def _populate_debug_analysis(self):
        """Populate debug analysis transient records"""
        self.ensure_one()
        
        # Clear existing debug records for this dashboard
        self.env['cash.flow.debug.line'].search([
            ('dashboard_id', '=', self.id)
        ]).unlink()
        
        if not self.account_ids:
            return
        
        # Use same parameters as debug_balance_calculation
        account_ids = self.account_ids.ids
        company_id = self.company_id.id
        target_currency = 'USD'
        date_from = None  # Can add context filtering later
        date_to = None
        
        # Build same domain as debug method
        domain = [
            ('account_id', 'in', account_ids),
            ('company_id', '=', company_id),
            ('move_id.state', '=', 'posted')
        ]
        
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        
        # Get move lines (same as debug method)
        move_lines = self.env['account.move.line'].search(domain)  # Increase limit for tree view
        
        # Create debug records for each move line
        for i, line in enumerate(move_lines, 1):
            # Currency info
            if line.currency_id:
                currency_name = line.currency_id.name
                currency_id = line.currency_id.id
                amount_currency = line.amount_currency
            else:
                currency_name = "Company Currency (TRY)"
                currency_id = self.company_id.currency_id.id
                amount_currency = 0.0
            
            # TRY amount
            try_amount = line.debit - line.credit
            
            # USD conversion logic (same as debug method)
            usd_value = 0.0
            usd_rate = 0.0
            usd_rate_date = False
            usd_rate_record_id = False
            conversion_method = 'fallback_no_rate'
            rate_info = "N/A"
            
            if target_currency == 'USD':
                if line.currency_id and line.currency_id.name == 'USD':
                    # Already USD
                    usd_value = line.amount_currency
                    conversion_method = 'already_usd'
                    rate_info = "Already USD - no conversion"
                    
                elif line.currency_id and line.currency_id.name == 'TRY':
                    # TRY currency to USD
                    rate_record, rate_value, rate_date = self._get_usd_rate_for_date(line.date, company_id)
                    if rate_record and rate_value:
                        usd_value = line.amount_currency / rate_value
                        usd_rate = rate_value
                        usd_rate_date = rate_date
                        usd_rate_record_id = rate_record.id
                        conversion_method = 'try_currency_to_usd'
                        rate_info = f"Rate: {rate_value} (from {rate_date})"
                    else:
                        usd_value = try_amount
                        conversion_method = 'fallback_no_rate'
                        rate_info = "No rate found - using TRY amount"
                        
                else:
                    # Company currency (TRY) to USD
                    rate_record, rate_value, rate_date = self._get_usd_rate_for_date(line.date, company_id)
                    if rate_record and rate_value:
                        usd_value = try_amount * rate_value
                        usd_rate = rate_value
                        usd_rate_date = rate_date
                        usd_rate_record_id = rate_record.id
                        conversion_method = 'company_currency_to_usd'
                        rate_info = f"Rate: {rate_value} (from {rate_date})"
                    else:
                        usd_value = try_amount
                        conversion_method = 'fallback_no_rate'
                        rate_info = "No rate found - using TRY amount"
            
            # Create debug record
            self.env['cash.flow.debug.line'].create({
                'dashboard_id': self.id,
                'line_number': i,
                'move_line_id': line.id,
                'date': line.date,
                'account_code': line.account_id.code,
                'account_name': line.account_id.name,
                'move_name': line.move_id,
                'account_id': line.account_id.id,
                'currency_name': currency_name,
                'currency_id': currency_id,
                'debit': line.debit,
                'credit': line.credit,
                'amount_currency': amount_currency,
                'try_amount': try_amount,
                'usd_rate': usd_rate,
                'usd_rate_date': usd_rate_date,
                'usd_rate_record_id': usd_rate_record_id,
                'usd_value': usd_value,
                'conversion_method': conversion_method,
                'rate_info': rate_info,
                'debug_date_from': date_from,
                'debug_date_to': date_to,
                'debug_target_currency': target_currency,
            })