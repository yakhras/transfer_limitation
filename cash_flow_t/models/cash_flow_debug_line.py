from odoo import models, fields, api

class CashFlowDebugLine(models.TransientModel):
    _name = 'cash.flow.debug.line'
    _description = 'Cash Flow Debug Line Analysis'
    _order = 'line_number'

    # Relation to dashboard
    dashboard_id = fields.Many2one(
        'cash.flow.dashboard', 
        string='Dashboard Record',
        required=True,
        ondelete='cascade'
    )
    
    # Line identification
    line_number = fields.Integer('Line #', required=True)
    move_line_id = fields.Many2one('account.move.line', string='Journal Entry Line')
    
    # Basic move line info
    date = fields.Date('Date', required=True)
    account_code = fields.Char('Account Code', required=True)
    account_name = fields.Char('Account Name')
    account_id = fields.Many2one('account.account', string='Account')
    move_name = fields.Char('Journal Entry')
    
    # Currency information
    currency_name = fields.Char('Currency', required=True)  # "USD", "TRY", "Company Currency (TRY)"
    currency_id = fields.Many2one('res.currency', string='Currency Record')
    
    # Original amounts from move line
    debit = fields.Monetary('Debit', currency_field='company_currency_id')
    credit = fields.Monetary('Credit', currency_field='company_currency_id')
    amount_currency = fields.Monetary('Amount Currency', currency_field='currency_id')
    try_amount = fields.Monetary('TRY Amount (debit-credit)', currency_field='company_currency_id')
    
    # USD conversion data
    usd_rate = fields.Float('USD Rate', digits=(16, 6))
    usd_rate_date = fields.Date('Rate Date')
    usd_rate_record_id = fields.Many2one('res.currency.rate', string='Rate Record')
    usd_value = fields.Monetary('USD Value', currency_field='usd_currency_id')
    
    # Conversion method tracking
    conversion_method = fields.Selection([
        ('already_usd', 'Already USD - no conversion'),
        ('try_currency_to_usd', 'TRY currency to USD'),
        ('company_currency_to_usd', 'Company currency (TRY) to USD'),
        ('fallback_no_rate', 'No rate found - using TRY amount')
    ], string='Conversion Method')
    
    rate_info = fields.Char('Rate Info')  # "Rate: 40.657300064982564 (from 2025-08-14)"
    
    # Filter context (for debugging)
    debug_date_from = fields.Date('Filter Date From')
    debug_date_to = fields.Date('Filter Date To')
    debug_target_currency = fields.Char('Target Currency')
    
    # Currency references
    company_currency_id = fields.Many2one(
        'res.currency', 
        string='Company Currency',
        related='dashboard_id.currency_id',
        store=True
    )
    
    usd_currency_id = fields.Many2one(
        'res.currency',
        string='USD Currency',
        default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
    )
    
    # Computed display fields
    amount_currency_display = fields.Char('Amount Display', compute='_compute_display_fields')
    usd_rate_display = fields.Char('Rate Display', compute='_compute_display_fields')
    
    @api.depends('amount_currency', 'currency_name', 'usd_rate', 'usd_rate_date', 'conversion_method')
    def _compute_display_fields(self):
        for record in self:
            # Amount display
            if record.currency_name == 'TRY' or 'TRY' in (record.currency_name or ''):
                record.amount_currency_display = f"₺{record.amount_currency:,.2f}" if record.amount_currency else "N/A"
            elif record.currency_name == 'USD':
                record.amount_currency_display = f"${record.amount_currency:,.2f}" if record.amount_currency else "N/A"
            else:
                record.amount_currency_display = f"{record.amount_currency:,.2f}" if record.amount_currency else "N/A"
            
            # Rate display
            if record.conversion_method == 'already_usd':
                record.usd_rate_display = "Already USD - no conversion"
            elif record.usd_rate and record.usd_rate_date:
                record.usd_rate_display = f"Rate: {record.usd_rate:.6f} (from {record.usd_rate_date})"
            elif record.conversion_method == 'fallback_no_rate':
                record.usd_rate_display = "No rate found - using TRY amount"
            else:
                record.usd_rate_display = "N/A"