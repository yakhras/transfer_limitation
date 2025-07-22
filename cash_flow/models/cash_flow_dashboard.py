from odoo import models, fields, api
from odoo.exceptions import UserError


class CashFlowDashboard(models.Model):
    _name = 'cash.flow.dashboard'
    _description = 'Cash Flow Dashboard'
    _order = 'account_code'

    # Basic fields
    account_id = fields.Many2one('account.account', string='Account', required=True)
    account_code = fields.Char(related='account_id.code', string='Account Code', store=True)
    account_name = fields.Char(related='account_id.name', string='Account Name', store=True)
    
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
        default=lambda self: self.env.company.currency_id
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

    @api.depends('account_id', 'account_id.current_balance')
    def _compute_current_balance(self):
        """Compute current balance for each account"""
        for record in self:
            if record.account_id:
                # Get current balance from account
                domain = [('account_id', '=', record.account_id.id)]
                account_moves = self.env['account.move.line'].search(domain)
                
                # Calculate balance (debit - credit for asset accounts, credit - debit for liability/equity)
                debit_total = sum(account_moves.mapped('debit'))
                credit_total = sum(account_moves.mapped('credit'))
                
                # Determine balance based on account type
                if record.account_id.account_type in ['asset_receivable', 'asset_cash', 'asset_current', 'asset_fixed']:
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
                record.balance_display = record.currency_id.format(record.current_balance)
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
    def create_dashboard_records(self):
        """Create dashboard records for the 5 specified accounts"""
        target_accounts = ['120002', '120003', '320002', '320003', '153000']
        
        for account_code in target_accounts:
            account = self.env['account.account'].search([('code', '=', account_code)], limit=1)
            if account:
                # Check if dashboard record already exists
                existing = self.search([('account_id', '=', account.id)])
                if not existing:
                    self.create({
                        'account_id': account.id,
                    })
            else:
                raise UserError(f"Account with code {account_code} not found in Chart of Accounts")

    @api.model
    def get_dashboard_data(self):
        """Get dashboard data for the 5 accounts"""
        target_accounts = ['120002', '120003', '320002', '320003', '153000']
        dashboard_data = []
        
        for account_code in target_accounts:
            account = self.env['account.account'].search([('code', '=', account_code)], limit=1)
            if account:
                dashboard_record = self.search([('account_id', '=', account.id)], limit=1)
                if not dashboard_record:
                    dashboard_record = self.create({'account_id': account.id})
                
                dashboard_data.append({
                    'id': dashboard_record.id,
                    'account_code': account.code,
                    'account_name': account.name,
                    'current_balance': dashboard_record.current_balance,
                    'balance_display': dashboard_record.balance_display,
                    'balance_color': dashboard_record.balance_color,
                })
        
        return dashboard_data