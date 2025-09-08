# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools import float_round
from odoo import tools
from io import BytesIO
from collections import defaultdict
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
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', readonly=True)

    # Enhance dta view
    reference = fields.Char(string="Reference", readonly=True)
    note = fields.Char(string="Note", readonly=True)
    type = fields.Char(string='Type', readonly=True)

    # For Normal Report in Company Currency
    debit = fields.Monetary(string='Debit', readonly=True, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', readonly=True, currency_field='company_currency_id')
    balance = fields.Monetary(string='Balance', readonly=True)
    cumulated_balance = fields.Monetary(string='Cumulated Balance', compute='_compute_cumulated_balance', store=False, currency_field='company_currency_id')

    # For Original Currency Report
    debit_amount = fields.Monetary(string='Debit Amount', compute='_compute_debit_amount', currency_field='currency_id', store=False)
    credit_amount = fields.Monetary(string='Credit Amount', compute='_compute_credit_amount', currency_field='currency_id', store=False)
    cumulated_balance_amount_currency = fields.Monetary(string='Cumulated Amount Currency', compute='_compute_cumulated_amount_currency', store=False, currency_field='company_currency_id')
    balance_amount = fields.Monetary(string='Balance Amount', compute='_compute_balance_amount', currency_field='currency_id', store=False)

    # For USD Value Report
    usd_rate_display = fields.Char('Rate Display', compute='_compute_usd_value')
    usd_value = fields.Monetary('USD Value', compute='_compute_usd_value', currency_field='currency_id')
    cumulated_usd_value = fields.Monetary('Cumulated USD Value', compute='_compute_cumulated_usd_value', currency_field='currency_id')

    # For Partner Currency Report
    partner_currency_id = fields.Many2one('res.currency', string='Partner Currency', compute='_compute_partner_currency',)
    partner_currency_value = fields.Monetary('Partner Currency Value', compute='_compute_partner_currency_value', currency_field='partner_currency_id')
    partner_currency_debit = fields.Monetary(string='Partner Currency Debit', compute='_compute_partner_currency_values', currency_field='partner_currency_id', store=False)
    partner_currency_credit = fields.Monetary(string='Partner Currency Credit', compute='_compute_partner_currency_values', currency_field='partner_currency_id', store=False)
    cumulated_partner_currency_value = fields.Monetary('Cumulated Partner Currency Value', compute='_compute_cumulated_partner_currency_value', currency_field='partner_currency_id')

    # Initial Balance for Cumulation
    initial_balance = fields.Monetary(string='Initial Balance', compute='_compute_initial_balance', store=False, currency_field='company_currency_id')
    initial_balance_amount_currency = fields.Monetary(string='Initial Balance Amount Currency', compute='_compute_initial_balance_amount_currency', store=False, currency_field='currency_id')
    initial_balance_partner_currency = fields.Monetary('Initial Balance Partner Currency', compute='_compute_initial_balance_partner_currency',store=False, currency_field='partner_currency_id')


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


    @api.depends('partner_id', 'date', 'move_id', 'balance', 'initial_balance', 'initial_balance_amount_currency')
    @api.depends_context('action_name')
    def _compute_cumulated_balance(self):
        """
        Compute cumulated balance for each partner, starting with appropriate initial balance
        based on report type (detected from action_name context).
        """
        # Detect report type from context
        action_name = self.env.context.get('action_name', '')
        is_currency_based_report = action_name == 'Statement Currency-based of Account'
        
        # Prepare a dictionary to track running totals for each partner
        grouped = {}
        
        # Sort records to simulate SQL "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"
        sorted_records = sorted(
            self,
            key=lambda r: (r.partner_id.id or 0, r.date or '', r.move_id.id or 0, r.id)
        )
        
        for rec in sorted_records:
            key = rec.partner_id.id
            if key not in grouped:
                # Choose appropriate initial balance based on report type
                if is_currency_based_report:
                    # Use currency-specific initial balance
                    grouped[key] = rec.initial_balance_amount_currency or 0.0
                else:
                    # Use mixed-currency initial balance for normal report
                    grouped[key] = rec.initial_balance or 0.0
            
            # add current line balance
            grouped[key] += rec.balance
            rec.cumulated_balance = grouped[key]


    @api.depends('partner_id', 'currency_id', 'date', 'move_id', 'amount_currency', 'initial_balance_amount_currency')
    def _compute_cumulated_amount_currency(self):
        """
        Compute the cumulative amount in currency for all entries, grouped by partner and currency,
        sorted by date, move_id, and id, starting with initial_balance_amount_currency.
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
            key = (rec.partner_id.id, rec.currency_id.id)
            if key not in grouped:
                # seed with the partner-currency initial_balance_amount_currency
                grouped[key] = rec.initial_balance_amount_currency or 0.0

            # add current line amount_currency
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


    @api.depends('debit', 'credit', 'partner_currency_id', 'partner_currency_value')
    def _compute_partner_currency_values(self):
        for rec in self:
            rec.partner_currency_debit = rec.partner_currency_value if rec.partner_currency_value > 0 else 0.0
            rec.partner_currency_credit = abs(rec.partner_currency_value) if rec.partner_currency_value < 0 else 0.0


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
                r.date or '',
                r.move_id.id or 0,
                r.id
            )
        )

        for rec in sorted_records:
            # Skip TRY currency records
            # if rec.currency_id and rec.currency_id.name == 'TRY':
            #     rec.cumulated_usd_value = 0
            #     continue

            key = rec.partner_id.id
            if key not in grouped:
                grouped[key] = 0.0

            grouped[key] += rec.usd_value or 0.0
            rec.cumulated_usd_value = grouped[key]


    @api.depends('partner_id', 'partner_id.property_product_pricelist', 'partner_id.property_product_pricelist.currency_id')
    def _compute_partner_currency(self):
        """Get partner's currency from pricelist"""
        for rec in self:
            if rec.partner_id and rec.partner_id.property_product_pricelist:
                pricelist_currency = rec.partner_id.property_product_pricelist.currency_id
                rec.partner_currency_id = pricelist_currency if pricelist_currency else rec.company_currency_id
            else:
                # Fallback to company currency if no partner or pricelist
                rec.partner_currency_id = rec.company_currency_id


    @api.depends('currency_id', 'amount_currency', 'date', 'company_id', 'partner_currency_id', 'balance')
    def _compute_partner_currency_value(self):
        """Convert transaction amount to partner's currency"""
        for rec in self:
            if not rec.partner_currency_id:
                rec.partner_currency_value = 0.0
                continue
                
            # If transaction currency matches partner currency (comparing objects)
            if rec.currency_id == rec.partner_currency_id:
                rec.partner_currency_value = rec.amount_currency or rec.balance
                
            # If transaction is in company currency (TRY) and partner uses different currency
            elif rec.currency_id and rec.currency_id.name == 'TRY' and rec.partner_currency_id.name != 'TRY':
                # Convert TRY to partner currency using partner_currency_id object
                partner_rate = rec._get_currency_rate(rec.partner_currency_id, rec.date, rec.company_id)
                if partner_rate:
                    rec.partner_currency_value = float_round(
                        (rec.amount_currency or rec.balance) / partner_rate, 
                        precision_digits=2
                    )
                else:
                    rec.partner_currency_value = 0.0
                    
            # If transaction is in foreign currency and needs conversion to partner currency
            else:
                # Convert using currency objects
                try:
                    if rec.amount_currency and rec.currency_id:
                        # Convert from transaction currency to partner currency
                        converted_amount = rec.currency_id._convert(
                            rec.amount_currency,
                            rec.partner_currency_id,  # This is a currency object
                            rec.company_id,
                            rec.date
                        )
                    else:
                        # Convert balance from company currency to partner currency
                        converted_amount = rec.company_currency_id._convert(
                            rec.balance,
                            rec.partner_currency_id,  # This is a currency object
                            rec.company_id,
                            rec.date
                        )
                    rec.partner_currency_value = float_round(converted_amount, precision_digits=2)
                except Exception as e:
                    rec.partner_currency_value = 0.0


    def _get_currency_rate(self, target_currency, date, company):
        """Helper method to get currency rate"""
        rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', target_currency.id),
            ('company_id', '=', company.id),
            ('name', '<', date)
        ], order='name desc', limit=1)
        
        return rate.inverse_company_rate if rate else None


    @api.depends('partner_id', 'date', 'move_id', 'partner_currency_value', 'initial_balance_partner_currency')
    def _compute_cumulated_partner_currency_value(self):
        """Calculate cumulative balance in partner's currency"""
        grouped = {}

        sorted_records = sorted(
            self,
            key=lambda r: (
                r.partner_id.id or 0,
                r.date or '',
                r.move_id.id or 0,
                r.id
            )
        )

        for rec in sorted_records:
            key = rec.partner_id.id
            if key not in grouped:
                grouped[key] = rec.initial_balance_partner_currency or 0.0

            grouped[key] += rec.partner_currency_value or 0.0
            rec.cumulated_partner_currency_value = grouped[key]

    
    @api.depends_context('date_from')
    def _compute_initial_balance(self): 
        """Compute the initial balance for each partner based on the context date_from"""
        date_from = self.env.context.get('date_from')
        
        # Initialize all records to 0.0 first
        for rec in self:
            rec.initial_balance = 0.0
        
        if not date_from:
            return

        partners = self.mapped('partner_id')
        if not partners:
            return
            
        initial_balances = {}

        # Aggregate balances before date_from with journal filter
        self.env.cr.execute("""
            SELECT amlr.partner_id, SUM(amlr.debit) - SUM(amlr.credit) as balance
            FROM account_move_line_report amlr
            JOIN account_move am ON am.id = amlr.move_id
            JOIN account_journal aj ON aj.id = am.journal_id
            WHERE amlr.date < %s 
            AND amlr.partner_id IN %s
            AND aj.code != 'KRFRK'
            GROUP BY amlr.partner_id
        """, (date_from, tuple(partners.ids)))

        for partner_id, total_balance in self.env.cr.fetchall():
            initial_balances[partner_id] = total_balance

        # Assign initial balances to records
        for rec in self:
            rec.initial_balance = initial_balances.get(rec.partner_id.id, 0.0)


    @api.depends_context('date_from')
    def _compute_initial_balance_amount_currency(self):
        """Compute the initial balance in amount currency for each partner-currency combination based on the context date_from"""
        date_from = self.env.context.get('date_from')
        
        # Initialize all records to 0.0 first
        for rec in self:
            rec.initial_balance_amount_currency = 0.0
        
        if not date_from:
            return

        partners = self.mapped('partner_id')
        currencies = self.mapped('currency_id')
        
        if not partners or not currencies:
            return
            
        initial_balances = {}

        # Aggregate amount_currency balances before date_from with journal filter
        # Group by partner_id and currency_id, include all currencies
        self.env.cr.execute("""
            SELECT amlr.partner_id, amlr.currency_id, SUM(amlr.amount_currency) as balance
            FROM account_move_line_report amlr
            JOIN account_move am ON am.id = amlr.move_id
            JOIN account_journal aj ON aj.id = am.journal_id
            WHERE amlr.date < %s 
            AND amlr.partner_id IN %s
            AND amlr.currency_id IN %s
            AND aj.code != 'KRFRK'
            GROUP BY amlr.partner_id, amlr.currency_id
        """, (date_from, tuple(partners.ids), tuple(currencies.ids)))

        for partner_id, currency_id, total_balance in self.env.cr.fetchall():
            initial_balances[(partner_id, currency_id)] = total_balance

        # Assign initial balances to records
        for rec in self:
            key = (rec.partner_id.id, rec.currency_id.id)
            rec.initial_balance_amount_currency = initial_balances.get(key, 0.0)


    @api.depends_context('date_from')
    def _compute_initial_balance_partner_currency(self):
        date_from = self.env.context.get('date_from')

        # Always assign something to every record to satisfy the compute contract
        for rec in self:
            rec.initial_balance_partner_currency = 0.0

        if not date_from:
            return

        # Only consider partners actually present on these records
        partner_ids = [p.id for p in self.mapped('partner_id') if p]
        if not partner_ids:
            return

        # Single batched search, then sum in Python (works for non-stored fields)
        domain = [
            ('date', '<', date_from),
            ('partner_id', 'in', partner_ids),
        ]
        # Fetch minimal fields to reduce overhead; computed fields will be evaluated
        lines = self.search(domain)

        totals = defaultdict(float)
        for line in lines:
            pid = line.partner_id.id or False
            # handle None safely
            totals[pid] += (line.partner_currency_value or 0.0)

        # Assign per record (records without partner stay 0.0)
        for rec in self:
            pid = rec.partner_id.id if rec.partner_id else False
            rec.initial_balance_partner_currency = totals.get(pid, 0.0)


    def partner_details(self, partner):
        user = self.env['res.users'].browse(partner)
        login = user.login
        name = user.partner_id.name if user.partner_id else 'N/A' 
        return {
            'id': partner,
            'name': name,
            'login': login,
        }


    # Add these fields to AccountMoveLineReport class
    # product_id = fields.Many2one('product.product', string='Product', readonly=True)
    # product_code = fields.Char(string='Product Code', readonly=True)
    # product_name = fields.Char(string='Product Name', readonly=True)
    # quantity = fields.Float(string='Quantity', readonly=True)
    # price_unit = fields.Monetary(string='Unit Price', readonly=True, currency_field='currency_id')
    # price_subtotal = fields.Monetary(string='Subtotal', readonly=True, currency_field='currency_id')
    # invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line', readonly=True)
    # row_type = fields.Char(string='Row Type', readonly=True)  # To distinguish main vs detail rows

    # def init(self):
    #     """Initialize the report view with product details"""
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
                
    #             -- Main transaction rows
    #             SELECT
    #                 (aml.id::bigint * 1000000 + 1)::bigint AS id,  -- Use bigint and larger multiplier
    #                 'TRANSACTION' AS row_type,
    #                 aml.date,
    #                 aml.move_id,
    #                 aml.partner_id,
    #                 aml.account_id,
    #                 aml.company_id,
    #                 aml.debit,
    #                 aml.credit,
    #                 aml.balance,
    #                 aml.amount_currency,
    #                 aml.currency_id,
    #                 rc.id AS company_currency_id,
                    
    #                 CASE
    #                     WHEN aj.payment_subtype = 'check' AND ca.check_numbers IS NOT NULL THEN ca.check_numbers
    #                     WHEN aj.payment_subtype = 'bank' AND aml.ref IS NOT NULL THEN aml.ref
    #                     ELSE am.name
    #                 END AS reference,
                    
    #                 CASE 
    #                     WHEN am.move_type = 'out_invoice' THEN 'Invoice'
    #                     WHEN am.move_type = 'in_invoice' THEN 'Bill'
    #                     WHEN am.move_type = 'out_refund' THEN 'Credit Note'
    #                     WHEN am.move_type = 'in_refund' THEN 'Credit Note'
    #                     WHEN aj.payment_subtype = 'bank' THEN 'Bank Payment'
    #                     WHEN aj.payment_subtype = 'check' THEN 'Check'
    #                     ELSE 'Journal Entry'
    #                 END AS type,
                    
    #                 am.document_number AS note,
                    
    #                 -- Product fields (null for main transaction rows)
    #                 NULL::integer AS product_id,
    #                 NULL AS product_code,
    #                 NULL AS product_name,
    #                 NULL::numeric AS quantity,
    #                 NULL::numeric AS price_unit,
    #                 NULL::numeric AS price_subtotal,
    #                 NULL::integer AS invoice_line_id
                    
    #             FROM account_move_line aml
    #             JOIN account_move am ON am.id = aml.move_id
    #             JOIN account_journal aj ON aj.id = am.journal_id
    #             JOIN account_account aa ON aa.id = aml.account_id
    #             JOIN account_account_type aat ON aat.id = aa.user_type_id
    #             JOIN res_company comp ON comp.id = aml.company_id
    #             JOIN res_currency rc ON rc.id = comp.currency_id
    #             LEFT JOIN account_payment ap ON ap.move_id = am.id
    #             LEFT JOIN check_aggregates ca ON ca.payment_id = ap.id
    #             WHERE am.state = 'posted'
    #             AND aat.type IN ('payable','receivable')
    #             AND aml.partner_id IS NOT NULL

    #             UNION ALL

    #             -- Product detail rows for invoices
    #             SELECT
    #                 (aml.id::bigint * 1000000 + 2 + row_number() OVER (PARTITION BY aml.id ORDER BY invoice_lines.id))::bigint AS id,
    #                 'PRODUCT' AS row_type,
    #                 aml.date,
    #                 aml.move_id,
    #                 aml.partner_id,
    #                 aml.account_id,
    #                 aml.company_id,
                    
    #                 0::numeric AS debit,
    #                 0::numeric AS credit,
    #                 0::numeric AS balance,
    #                 0::numeric AS amount_currency,
    #                 aml.currency_id,
    #                 rc.id AS company_currency_id,
                    
    #                 am.name AS reference,
    #                 'Product Line' AS type,
    #                 concat('Line ', COALESCE(invoice_lines.sequence, 1)) AS note,
                    
    #                 invoice_lines.product_id,
    #                 pp.default_code AS product_code,
    #                 pt.name AS product_name,
    #                 invoice_lines.quantity,
    #                 invoice_lines.price_unit,
    #                 invoice_lines.price_subtotal,
    #                 invoice_lines.id AS invoice_line_id
                    
    #             FROM account_move_line aml
    #             JOIN account_move am ON am.id = aml.move_id
    #             JOIN account_journal aj ON aj.id = am.journal_id
    #             JOIN account_account aa ON aa.id = aml.account_id
    #             JOIN account_account_type aat ON aat.id = aa.user_type_id
    #             JOIN res_company comp ON comp.id = aml.company_id
    #             JOIN res_currency rc ON rc.id = comp.currency_id
    #             JOIN account_move_line invoice_lines ON invoice_lines.move_id = am.id 
    #                 AND invoice_lines.product_id IS NOT NULL
    #                 AND invoice_lines.exclude_from_invoice_tab = false
    #             LEFT JOIN product_product pp ON pp.id = invoice_lines.product_id
    #             LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
                
    #             WHERE am.state = 'posted'
    #             AND aat.type IN ('payable','receivable')
    #             AND aml.partner_id IS NOT NULL
    #             AND am.move_type IN ('out_invoice', 'in_invoice', 'out_refund', 'in_refund')
                
    #             ORDER BY date, move_id, row_type DESC
    #         )
    #     """)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def action_view_move_line_report(self):
        """Open Account Move Line Report for this partner"""
        self.ensure_one()  # Ensure only one record is processed
        action_name = _("Statement of Account")  # Default action name
        
        return {
            'type': 'ir.actions.act_window',
            'name': f'{action_name}',
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
    

    def get_move_line_count(self):
        """Get count of move lines for this partner (for display purposes)"""
        return self.env['account.move.line.report'].search_count([
            ('partner_id', '=', self.id)
        ])
    
