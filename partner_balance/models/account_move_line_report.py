# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_round
from odoo import tools
from io import BytesIO


class AccountMoveLineReport(models.Model):
    _name = 'account.move.line.report'
    _description = 'Account Move Line Report'
    _auto = False
    _order = 'date desc, move_id desc'

    date = fields.Date(string='Date', readonly=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)
    name = fields.Char(string='Label', readonly=True)
    amount_currency = fields.Monetary(string='Amount Currency', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    debit = fields.Monetary(string='Debit', readonly=True)
    credit = fields.Monetary(string='Credit', readonly=True)
    balance = fields.Monetary(string='Balance', readonly=True)

    # Computed instead of SQL
    cumulated_balance = fields.Monetary(
        string='Cumulated Balance',
        compute='_compute_cumulated_balance',
        store=False,
        currency_field='company_currency_id',
        help="Cumulated balance depending on the domain and the order chosen in the view."
    )

    cumulated_balance_amount_currency = fields.Monetary(
        string='Cumulated Amount Currency',
        compute='_compute_cumulated_amount_currency',
        store=False,
        currency_field='company_currency_id',
        help="Cumulated amount currency for non-TRY currencies only."
    )

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', readonly=True)

    def init(self):
        """Initialize the report view"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
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
                    aml.partner_id,
                    aml.account_id,
                    aml.company_id,
                    rc.id as company_currency_id
                FROM account_move_line aml
                INNER JOIN account_move am ON aml.move_id = am.id
                INNER JOIN account_account aa ON aml.account_id = aa.id
                INNER JOIN account_account_type aat ON aa.user_type_id = aat.id
                INNER JOIN res_company comp ON aml.company_id = comp.id
                INNER JOIN res_currency rc ON comp.currency_id = rc.id
                WHERE am.state = 'posted'
                    AND aat.type IN ('payable', 'receivable')
                    AND aml.partner_id IS NOT NULL
            )
        """)

    @api.depends('partner_id', 'date', 'move_id', 'balance')
    def _compute_cumulated_balance(self):
        """
        Compute the cumulated balance dynamically for each partner based on date + move + id ordering.
        This version does NOT depend on context.
        """
        grouped = {}
        for rec in sorted(self, key=lambda r: (r.partner_id.id or 0, r.date or '', r.move_id.id or 0, r.id)):
            key = rec.partner_id.id
            if key not in grouped:
                grouped[key] = 0.0
            grouped[key] += rec.balance
            rec.cumulated_balance = grouped[key]


    @api.depends('partner_id', 'currency_id', 'date', 'move_id', 'amount_currency')
    def _compute_cumulated_amount_currency(self):
        """
        Compute the cumulative amount in currency for non-TRY entries, grouped by partner and currency,
        sorted by date, move_id, and id — no context required.
        """
        # Prepare a dictionary to track running totals for each (partner_id, currency_id)
        grouped = {}

        # Sort records to simulate SQL "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
        sorted_records = sorted(
            self,
            key=lambda r: (
                r.partner_id.id or 0,
                r.currency_id.id or 0,
                r.date or '',
                r.move_id.id or 0,
                r.id
            )
        )

        for rec in sorted_records:
            # Skip TRY currency records
            if rec.currency_id and rec.currency_id.name == 'TRY':
                rec.cumulated_balance_amount_currency = 0
                continue

            key = (rec.partner_id.id, rec.currency_id.id)
            if key not in grouped:
                grouped[key] = 0.0

            grouped[key] += rec.amount_currency or 0.0
            rec.cumulated_balance_amount_currency = grouped[key]


    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
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