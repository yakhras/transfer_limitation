# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import float_round
from odoo import tools
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime


class AccountMoveLineReport(models.Model):
    _name = 'account.move.line.report'
    _description = 'Account Move Line Report'
    _auto = False

    date = fields.Date(string='Date', readonly=True)
    move_id = fields.Many2one('account.move', string='Reference', readonly=True)
    # name = fields.Char(string='Note', readonly=True)
    amount_currency = fields.Monetary(string='Amount Currency', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Original Currency', readonly=True)
    debit = fields.Monetary(string='Debit', readonly=True, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', readonly=True, currency_field='company_currency_id')
    balance = fields.Monetary(string='Balance', readonly=True)

    # Adjusted fields
    reference = fields.Char(string="Reference", readonly=True)  # will hold am.name
    note = fields.Char(string="Note", readonly=True)            # will hold am.ref
    type = fields.Char(string='Type', readonly=True)


    # Computed instead of SQL
    cumulated_balance = fields.Monetary(string='Cumulated Balance', compute='_compute_cumulated_balance', store=False, currency_field='company_currency_id')

    cumulated_balance_amount_currency = fields.Monetary(string='Cumulated Amount Currency', compute='_compute_cumulated_amount_currency', store=False, currency_field='company_currency_id')

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', readonly=True)

    debit_amount = fields.Monetary(string='Debit Amount', compute='_compute_debit_amount', currency_field='currency_id', store=False)
    credit_amount = fields.Monetary(string='Credit Amount', compute='_compute_credit_amount', currency_field='currency_id', store=False)
    balance_amount = fields.Monetary(string='Balance Amount', compute='_compute_balance_amount', currency_field='currency_id', store=False)


    usd_rate_display = fields.Char('Rate Display', compute='_compute_usd_value')
    usd_value = fields.Monetary('USD Value', compute='_compute_usd_value', currency_field='currency_id')
    cumulated_usd_value = fields.Monetary('Cumulated USD Value', compute='_compute_cumulated_usd_value', currency_field='currency_id')



    # def init(self):
    #     """Initialize the report view"""
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute(f"""
    #         CREATE OR REPLACE VIEW {self._table} AS (
    #             WITH check_aggregates AS (
    #                 SELECT 
    #                     ap.id as payment_id,
    #                     string_agg(DISTINCT ac.number::text, ', ' ORDER BY ac.number::text) as check_numbers
    #                 FROM account_payment ap
    #                 JOIN account_check ac ON ac.payment_id = ap.id
    #                 GROUP BY ap.id
    #             )
                
    #             SELECT
    #                 aml.id                AS id,
    #                 aml.date              AS date,
    #                 aml.move_id           AS move_id,
    #                 aml.partner_id        AS partner_id,
    #                 aml.account_id        AS account_id,
    #                 aml.company_id        AS company_id,

    #                 aml.debit             AS debit,
    #                 aml.credit            AS credit,
    #                 aml.balance           AS balance,
    #                 aml.amount_currency   AS amount_currency,
    #                 aml.currency_id       AS currency_id,
    #                 rc.id                 AS company_currency_id,

    #                 -- Enhanced reference logic with check numbers and bank ref
    #                 CASE
    #                     WHEN aj.payment_subtype = 'check' AND ca.check_numbers IS NOT NULL THEN
    #                         ca.check_numbers  -- Show aggregated check numbers
    #                     WHEN aj.payment_subtype = 'bank' AND aml.ref IS NOT NULL THEN
    #                         aml.ref          -- Show bank reference from move line
    #                     ELSE
    #                         am.name          -- Default journal entry reference
    #                 END AS reference,
                    
    #                 -- Transaction type classification
    #                 CASE 
    #                     WHEN am.move_type = 'out_invoice' THEN 'Invoice'
    #                     WHEN am.move_type = 'in_invoice' THEN 'Bill'
    #                     WHEN am.move_type = 'out_refund' THEN 'Credit Note'
    #                     WHEN am.move_type = 'in_refund' THEN 'Credit Note'
    #                     WHEN aj.payment_subtype = 'bank' THEN 'Bank Payment'
    #                     WHEN aj.payment_subtype = 'check' THEN 'Check'
    #                     WHEN aj.type = 'purchase' THEN 'Purchase'
    #                     WHEN aj.type = 'sale' THEN 'Sale'
    #                     ELSE 'Journal Entry'
    #                 END AS type,
                    
    #                 am.document_number    AS note        -- Document number / Reference
                    
    #             FROM account_move_line aml
    #             JOIN account_move am
    #             ON am.id = aml.move_id
    #             JOIN account_journal aj
    #             ON aj.id = am.journal_id  -- Added for payment_subtype
    #             JOIN account_account aa
    #             ON aa.id = aml.account_id
    #             JOIN account_account_type aat
    #             ON aat.id = aa.user_type_id
    #             JOIN res_company comp
    #             ON comp.id = aml.company_id
    #             JOIN res_currency rc
    #             ON rc.id = comp.currency_id
    #             LEFT JOIN account_payment ap
    #             ON ap.move_id = am.id     -- Link to payment for check lookup
    #             LEFT JOIN check_aggregates ca
    #             ON ca.payment_id = ap.id  -- Get aggregated check numbers
    #             WHERE am.state = 'posted'
    #             AND aat.type IN ('payable','receivable')
    #             AND aml.partner_id IS NOT NULL
    #         )
    #     """)

    def init(self):
        """Initialize the report view"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH check_aggregates AS (
                    SELECT 
                        ap.id as payment_id,
                        string_agg(DISTINCT ac.number::text, ', ' ORDER BY ac.number::text) as check_numbers
                    FROM account_payment ap
                    JOIN account_check ac ON ac.payment_id = ap.id
                    GROUP BY ap.id
                )
                
                -- Main transaction data
                SELECT
                    aml.id                AS id,
                    aml.date              AS date,
                    aml.move_id           AS move_id,
                    aml.partner_id        AS partner_id,
                    aml.account_id        AS account_id,
                    aml.company_id        AS company_id,

                    aml.debit             AS debit,
                    aml.credit            AS credit,
                    aml.balance           AS balance,
                    aml.amount_currency   AS amount_currency,
                    aml.currency_id       AS currency_id,
                    rc.id                 AS company_currency_id,

                    -- Enhanced reference logic with check numbers and bank ref
                    CASE
                        WHEN aj.payment_subtype = 'check' AND ca.check_numbers IS NOT NULL THEN
                            ca.check_numbers  -- Show aggregated check numbers
                        WHEN aj.payment_subtype = 'bank' AND aml.ref IS NOT NULL THEN
                            aml.ref          -- Show bank reference from move line
                        ELSE
                            am.name          -- Default journal entry reference
                    END AS reference,
                    
                    -- Transaction type classification
                    CASE 
                        WHEN am.move_type = 'out_invoice' THEN 'Invoice'
                        WHEN am.move_type = 'in_invoice' THEN 'Bill'
                        WHEN am.move_type = 'out_refund' THEN 'Credit Note'
                        WHEN am.move_type = 'in_refund' THEN 'Credit Note'
                        WHEN aj.payment_subtype = 'bank' THEN 'Bank Payment'
                        WHEN aj.payment_subtype = 'check' THEN 'Check'
                        WHEN aj.type = 'purchase' THEN 'Purchase'
                        WHEN aj.type = 'sale' THEN 'Sale'
                        ELSE 'Journal Entry'
                    END AS type,
                    
                    am.document_number    AS note        -- Document number / Reference
                    
                FROM account_move_line aml
                JOIN account_move am
                ON am.id = aml.move_id
                JOIN account_journal aj
                ON aj.id = am.journal_id  -- Added for payment_subtype
                JOIN account_account aa
                ON aa.id = aml.account_id
                JOIN account_account_type aat
                ON aat.id = aa.user_type_id
                JOIN res_company comp
                ON comp.id = aml.company_id
                JOIN res_currency rc
                ON rc.id = comp.currency_id
                LEFT JOIN account_payment ap
                ON ap.move_id = am.id     -- Link to payment for check lookup
                LEFT JOIN check_aggregates ca
                ON ca.payment_id = ap.id  -- Get aggregated check numbers
                WHERE am.state = 'posted'
                AND aat.type IN ('payable','receivable')
                AND aml.partner_id IS NOT NULL

                UNION ALL

                -- Static Opening Balance Record
                SELECT
                    -1                    AS id,
                    '1900-01-01'::date    AS date,
                    NULL                  AS move_id,
                    rp.id                 AS partner_id,
                    NULL                  AS account_id,
                    rc.id                 AS company_id,

                    0.00                  AS debit,
                    0.00                  AS credit,
                    0.00                  AS balance,
                    2500000.00            AS amount_currency,
                    curr.id               AS currency_id,
                    rc.id                 AS company_currency_id,

                    'OPENING-BALANCE'     AS reference,
                    'Opening Balance'     AS type,
                    'Period Opening Balance' AS note

                FROM res_partner rp
                CROSS JOIN res_company comp
                JOIN res_currency rc ON rc.id = comp.currency_id
                JOIN res_currency curr ON curr.name = 'USD'
                WHERE rp.id = 54487  -- Your specific partner ID

                UNION ALL

                -- Static Summary Record  
                SELECT
                    -2                    AS id,
                    '2099-12-31'::date    AS date,
                    NULL                  AS move_id,
                    rp.id                 AS partner_id,
                    NULL                  AS account_id,
                    rc.id                 AS company_id,

                    1359987.41            AS debit,
                    3617000.00            AS credit,
                    -2257012.59           AS balance,
                    242987.41             AS amount_currency,
                    curr.id               AS currency_id,
                    rc.id                 AS company_currency_id,

                    'PERIOD-SUMMARY'      AS reference,
                    'Period Summary'      AS type,
                    'Invoices: +$1.36M | Payments: -$3.62M' AS note

                FROM res_partner rp
                CROSS JOIN res_company comp
                JOIN res_currency rc ON rc.id = comp.currency_id
                JOIN res_currency curr ON curr.name = 'USD'
                WHERE rp.id = 54487  -- Your specific partner ID
            )
        """)


    @api.depends('debit', 'amount_currency', 'currency_id')
    def _compute_debit_amount(self):
        for rec in self:
            if rec.currency_id and rec.currency_id.name == 'TRY':
                rec.debit_amount = rec.debit
            elif rec.amount_currency and rec.amount_currency > 0:
                rec.debit_amount = rec.amount_currency
            else:
                rec.debit_amount = 0.0


    @api.depends('credit', 'amount_currency', 'currency_id')
    def _compute_credit_amount(self):
        for rec in self:
            if rec.currency_id and rec.currency_id.name == 'TRY':
                rec.credit_amount = rec.credit
            elif rec.amount_currency and rec.amount_currency < 0:
                rec.credit_amount = abs(rec.amount_currency)  # Convert to positive
            else:
                rec.credit_amount = 0.0


    @api.depends('currency_id', 'cumulated_balance', 'cumulated_balance_amount_currency')
    def _compute_balance_amount(self):
        for rec in self:
            if rec.currency_id and rec.currency_id.name == 'TRY':
                rec.balance_amount = rec.cumulated_balance
            else:
                rec.balance_amount = rec.cumulated_balance_amount_currency


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


    @api.depends('currency_id', 'amount_currency', 'date', 'company_id')
    def _compute_usd_value(self):
        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        for rec in self:
            if rec.currency_id == usd_currency:
                rec.usd_value = rec.amount_currency
                rec.usd_rate_display = "1.0000"
            elif rec.currency_id and rec.currency_id.name == 'TRY':
                rate = self.env['res.currency.rate'].search([
                    ('currency_id.name', '=', 'USD'),
                    ('company_id', '=', rec.company_id.id),
                    ('name', '<', rec.date)
                ], order='name desc', limit=1)
                if rate and rate.inverse_company_rate:
                    rec.usd_rate_display = f"{rate.inverse_company_rate:.4f}"
                    rec.usd_value = float_round(rec.amount_currency / rate.inverse_company_rate, precision_digits=2)
                else:
                    rec.usd_value = 0.0
                    rec.usd_rate_display = "0.0000"
            else:
                rec.usd_value = 0.0
                rec.usd_rate_display = "N/A"


    @api.depends('partner_id', 'currency_id', 'date', 'move_id', 'usd_value')
    def _compute_cumulated_usd_value(self):
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
                rec.cumulated_usd_value = 0
                continue

            key = (rec.partner_id.id, rec.currency_id.id)
            if key not in grouped:
                grouped[key] = 0.0

            grouped[key] += rec.usd_value or 0.0
            rec.cumulated_usd_value = grouped[key]

    @api.model
    def create_simple_static_record(self):
        """Create a simple record with static values"""
        
        # Method 1: Using create()
        static_record = self.new({
            'date': '2020-08-01',
            'type': 'Opening Balance',
            'reference': 'OB-2025',
            'note': 'Opening Balance Note',
            'amount_currency': 2500000.00,
            'currency_id': self.env['res.currency'].search([('name', '=', 'USD')]).id,
            'debit': 0.00,
            'credit': 0.00,
            'cumulated_balance': 2500000.00,
            'partner_id': 54487,
            'company_id': self.env.company.id,
        })
        
        return static_record

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_view_move_line_report(self):
        """Open Account Move Line Report for this partner"""
        self.ensure_one()  # Ensure only one record is processed
        action_name = _("Statement of Account")  # Default action name
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'{action_name} - {self.name}',
            'res_model': 'account.move.line.report',
            'view_mode': 'tree',
            'view_id' : self.env.ref("partner_balance.view_account_move_line_report_tree").id,
            'domain': [('partner_id', '=', self.id),
                       ('move_id.journal_id.code', '!=', 'KRFRK')],
            'context': {
                'default_partner_id': self.id,
                'search_default_group_by_account': 1,
                'partner_name': self.name,
                'action_name': action_name,
            },
            'target': 'current',  # Open in current window
        }
    
    def action_view_move_line_report_currency(self):
        """Open Account Move Line Report for this partner"""
        self.ensure_one()  # Ensure only one record is processed
        action_name = _('Statement Currency-based of Account')
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'{action_name} - {self.name}',
            'res_model': 'account.move.line.report',
            'view_mode': 'tree',
            'view_id' : self.env.ref("partner_balance.view_account_move_line_report_currency_tree").id,
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'group_by': 'currency_id',
                'default_partner_id': self.id,
                'search_default_group_by_account': 1,
                'partner_name': self.name,
                'action_name': action_name,  # Pass partner name for reference
            },
            'target': 'current',  # Open in current window
        }

    def get_move_line_count(self):
        """Get count of move lines for this partner (for display purposes)"""
        return self.env['account.move.line.report'].search_count([
            ('partner_id', '=', self.id)
        ])