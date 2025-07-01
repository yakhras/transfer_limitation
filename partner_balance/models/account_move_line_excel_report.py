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
    cumulated_balance = fields.Monetary(string='Cumulated Balance', compute='_compute_cumulated_balance', store=False, currency_field='company_currency_id')

    cumulated_balance_amount_currency = fields.Monetary(string='Cumulated Amount Currency', compute='_compute_cumulated_amount_currency', store=False, currency_field='company_currency_id')

    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    company_currency_id = fields.Many2one('res.currency', string='Company Currency', readonly=True)

    debit_amount = fields.Monetary(string='Debit Amount', compute='_compute_debit_amount', currency_field='currency_id', store=False)
    credit_amount = fields.Monetary(string='Credit Amount', compute='_compute_credit_amount', currency_field='currency_id', store=False)
    balance_amount = fields.Monetary(string='Balance Amount', compute='_compute_balance_amount', currency_field='currency_id', store=False)

    def export_to_excel(self):
        """Export current records to Excel"""
        # Get current domain from context or use all records
        domain = self.env.context.get('active_domain', [])
        records = self.search(domain)
        
        # Create Excel file
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': False})
        worksheet = workbook.add_worksheet('Account Move Lines')
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'align': 'center'
        })
        
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1
        })
        
        text_format = workbook.add_format({
            'border': 1
        })
        
        # Set column widths
        worksheet.set_column('A:A', 12)  # Date
        worksheet.set_column('B:B', 15)  # Journal Entry
        worksheet.set_column('C:C', 30)  # Partner
        worksheet.set_column('D:D', 25)  # Account
        worksheet.set_column('E:E', 35)  # Label
        worksheet.set_column('F:F', 10)  # Currency
        worksheet.set_column('G:G', 15)  # Debit
        worksheet.set_column('H:H', 15)  # Credit
        worksheet.set_column('I:I', 15)  # Balance
        
        # Write headers
        headers = [
            'Date', 'Journal Entry', 'Partner', 'Account', 'Label',
            'Currency', 'Debit Amount', 'Credit Amount', 'Balance Amount'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data
        for row, record in enumerate(records, 1):
            worksheet.write(row, 0, record.date, date_format)
            worksheet.write(row, 1, record.move_id.name or '', text_format)
            worksheet.write(row, 2, record.partner_id.name or '', text_format)
            worksheet.write(row, 3, record.account_id.name or '', text_format)
            worksheet.write(row, 4, record.name or '', text_format)
            worksheet.write(row, 5, record.currency_id.name or '', text_format)
            worksheet.write(row, 6, record.debit_amount or 0, currency_format)
            worksheet.write(row, 7, record.credit_amount or 0, currency_format)
            worksheet.write(row, 8, record.balance_amount or 0, currency_format)
        
        workbook.close()
        output.seek(0)
        
        # Generate filename
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'account_move_lines_{date_str}.xlsx'
        
        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id=0&field=export_excel&download=true&filename={filename}&data={base64.b64encode(output.read()).decode()}',
            'target': 'self',
        }

    @api.depends('currency_id', 'cumulated_balance', 'cumulated_balance_amount_currency')
    def _compute_balance_amount(self):
        for rec in self:
            if rec.currency_id and rec.currency_id.name == 'TRY':
                rec.balance_amount = rec.cumulated_balance
            else:
                rec.balance_amount = rec.cumulated_balance_amount_currency

    @api.depends('credit', 'amount_currency', 'currency_id')
    def _compute_credit_amount(self):
        for rec in self:
            if rec.currency_id and rec.currency_id.name == 'TRY':
                rec.credit_amount = rec.credit
            elif rec.amount_currency and rec.amount_currency < 0:
                rec.credit_amount = rec.amount_currency  # Convert to positive
            else:
                rec.credit_amount = 0.0

    @api.depends('debit', 'amount_currency', 'currency_id')
    def _compute_debit_amount(self):
        for rec in self:
            if rec.currency_id and rec.currency_id.name == 'TRY':
                rec.debit_amount = rec.debit
            elif rec.amount_currency and rec.amount_currency > 0:
                rec.debit_amount = rec.amount_currency
            else:
                rec.debit_amount = 0.0

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