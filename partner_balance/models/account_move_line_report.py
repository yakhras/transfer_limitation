# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_round
from odoo import tools


class AccountMoveLineReport(models.Model):
    _name = 'account.move.line.report'
    _description = 'Account Move Line Report'
    _auto = False  # This prevents creating a physical table
    _order = 'date desc, move_id desc'

    # Fields from account.move.line
    date = fields.Date(string='Date', readonly=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    name = fields.Char(string='Label', readonly=True)
    amount_currency = fields.Monetary(string='Amount Currency', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    debit = fields.Monetary(string='Debit', readonly=True)
    credit = fields.Monetary(string='Credit', readonly=True)
    balance = fields.Monetary(string='Balance', readonly=True)
    cumulated_balance = fields.Monetary(string='Cumulated Balance', readonly=True)
    
    # Additional useful fields for reporting
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)

    def init(self):
        """Initialize the report view"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    aml.id,
                    aml.date,
                    aml.move_id,
                    aml.name,
                    aml.amount_currency,
                    aml.currency_id,
                    aml.debit,
                    aml.credit,
                    aml.balance,
                    SUM(aml.balance) OVER (
                        PARTITION BY aml.account_id, aml.partner_id 
                        ORDER BY aml.date, aml.move_id 
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) as cumulated_balance,
                    aml.partner_id,
                    aml.account_id,
                    aml.journal_id,
                    aml.company_id
                FROM account_move_line aml
                INNER JOIN account_move am ON aml.move_id = am.id
                INNER JOIN account_account aa ON aml.account_id = aa.id
                INNER JOIN account_account_type aat ON aa.user_type_id = aat.id
                WHERE am.state = 'posted'
                    AND aat.type IN ('payable', 'receivable')
                    AND aml.partner_id IS NOT NULL
                ORDER BY aml.date DESC, aml.move_id DESC
            )
        """ % self._table)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override read_group to add custom aggregations"""
        res = super(AccountMoveLineReport, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy
        )
        
        # Add custom calculations if needed
        for group in res:
            if 'balance' in fields and 'debit' in fields and 'credit' in fields:
                group['balance'] = group.get('debit', 0) - group.get('credit', 0)
                
        return res


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_view_move_line_report(self):
        """Open Account Move Line Report for this partner"""
        self.ensure_one()  # Ensure only one record is processed
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'Account Move Line Report - {self.name}',
            'res_model': 'account.move.line.report',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'default_partner_id': self.id,
                'search_default_group_by_account': 1,
                'partner_name': self.name,  # Pass partner name for reference
            },
            'target': 'current',  # Open in current window
        }

    def get_move_line_count(self):
        """Get count of move lines for this partner (for display purposes)"""
        return self.env['account.move.line.report'].search_count([
            ('partner_id', '=', self.id)
        ])