# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import float_round
from odoo import tools
from io import BytesIO
import xlsxwriter
import base64
from datetime import datetime


class AccountMoveLineExcelReport(models.TransientModel):
    _name = 'account.move.line.excel.report'
    _description = 'Account Move Line Excel Report Generator'

    # Filter fields
    partner_ids = fields.Many2many('res.partner', string='Partners')
    account_ids = fields.Many2many('account.account', string='Accounts')
    currency_ids = fields.Many2many('res.currency', string='Currencies')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Output
    excel_file = fields.Binary(string='Excel File', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft')

    def generate_excel_report(self):
        """Generate Excel report with multiple sheets"""
        
        # Build domain for filtering
        domain = []
        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))
        if self.account_ids:
            domain.append(('account_id', 'in', self.account_ids.ids))
        if self.currency_ids:
            domain.append(('currency_id', 'in', self.currency_ids.ids))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        if self.company_id:
            domain.append(('company_id', '=', self.company_id.id))

        # Fetch data
        move_lines = self.env['account.move.line.report'].search(domain, order='partner_id, date, move_id')
        
        # Create Excel file
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })
        
        subheader_format = workbook.add_format({
            'bold': True,
            'font_size': 11,
            'bg_color': '#B8CCE4',
            'border': 1,
            'align': 'center'
        })
        
        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'border': 1,
            'align': 'center'
        })
        
        currency_format = workbook.add_format({
            'num_format': '#,##0.00',
            'border': 1,
            'align': 'right'
        })
        
        text_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'top'
        })
        
        center_format = workbook.add_format({
            'border': 1,
            'align': 'center'
        })
        
        total_format = workbook.add_format({
            'bold': True,
            'num_format': '#,##0.00',
            'bg_color': '#FFFF99',
            'border': 1,
            'align': 'right'
        })

        # Sheet 1: Detailed Report
        self._create_detailed_sheet(workbook, move_lines, header_format, subheader_format, 
                                  date_format, currency_format, text_format, center_format, total_format)
        
        # Sheet 2: Partner Summary
        self._create_partner_summary_sheet(workbook, move_lines, header_format, subheader_format,
                                         currency_format, text_format, total_format)
        
        # Sheet 3: Currency Summary
        self._create_currency_summary_sheet(workbook, move_lines, header_format, subheader_format,
                                          currency_format, text_format, total_format)
        
        # Sheet 4: Account Summary
        self._create_account_summary_sheet(workbook, move_lines, header_format, subheader_format,
                                         currency_format, text_format, total_format)

        workbook.close()
        output.seek(0)
        
        # Generate filename
        date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        partner_str = f"_{len(self.partner_ids)}_partners" if self.partner_ids else "_all_partners"
        filename = f"Account_Move_Line_Report{partner_str}_{date_str}.xlsx"
        
        # Save file
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'file_name': filename,
            'state': 'done'
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line.excel.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_initial_mode': 'readonly'}
        }

    def _create_detailed_sheet(self, workbook, move_lines, header_format, subheader_format, 
                             date_format, currency_format, text_format, center_format, total_format):
        """Create detailed move lines sheet"""
        worksheet = workbook.add_worksheet('Detailed Report')
        
        # Set column widths
        worksheet.set_column('A:A', 12)  # Date
        worksheet.set_column('B:B', 15)  # Journal Entry
        worksheet.set_column('C:C', 30)  # Partner
        worksheet.set_column('D:D', 25)  # Account
        worksheet.set_column('E:E', 35)  # Label
        worksheet.set_column('F:F', 12)  # Currency
        worksheet.set_column('G:G', 15)  # Debit Amount
        worksheet.set_column('H:H', 15)  # Credit Amount
        worksheet.set_column('I:I', 15)  # Balance Amount
        worksheet.set_column('J:J', 15)  # Cumulated Balance
        
        # Write header
        headers = [
            'Date', 'Journal Entry', 'Partner', 'Account', 'Label', 
            'Currency', 'Debit Amount', 'Credit Amount', 'Balance Amount', 'Cumulated Balance'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Write data
        row = 1
        current_partner = None
        partner_totals = {}
        
        for line in move_lines:
            # Partner grouping
            if current_partner != line.partner_id.id:
                if current_partner is not None:
                    # Write partner total
                    worksheet.write(row, 2, 'TOTAL', total_format)
                    worksheet.write(row, 6, partner_totals.get('debit', 0), total_format)
                    worksheet.write(row, 7, partner_totals.get('credit', 0), total_format)
                    worksheet.write(row, 8, partner_totals.get('balance', 0), total_format)
                    row += 2
                
                current_partner = line.partner_id.id
                partner_totals = {'debit': 0, 'credit': 0, 'balance': 0}
                
                # Write partner header
                worksheet.write(row, 0, f"Partner: {line.partner_id.name}", subheader_format)
                worksheet.merge_range(row, 0, row, 9, f"Partner: {line.partner_id.name}", subheader_format)
                row += 1
            
            # Write line data
            worksheet.write(row, 0, line.date, date_format)
            worksheet.write(row, 1, line.move_id.name or '', center_format)
            worksheet.write(row, 2, line.partner_id.name or '', text_format)
            worksheet.write(row, 3, line.account_id.name or '', text_format)
            worksheet.write(row, 4, line.name or '', text_format)
            worksheet.write(row, 5, line.currency_id.name or '', center_format)
            worksheet.write(row, 6, line.debit_amount or 0, currency_format)
            worksheet.write(row, 7, line.credit_amount or 0, currency_format)
            worksheet.write(row, 8, line.balance_amount or 0, currency_format)
            worksheet.write(row, 9, line.balance_amount or 0, currency_format)  # Cumulated will be calculated
            
            # Update totals
            partner_totals['debit'] += line.debit_amount or 0
            partner_totals['credit'] += line.credit_amount or 0
            partner_totals['balance'] += line.balance_amount or 0
            
            row += 1
        
        # Write final partner total
        if current_partner is not None:
            worksheet.write(row, 2, 'TOTAL', total_format)
            worksheet.write(row, 6, partner_totals.get('debit', 0), total_format)
            worksheet.write(row, 7, partner_totals.get('credit', 0), total_format)
            worksheet.write(row, 8, partner_totals.get('balance', 0), total_format)

    def _create_partner_summary_sheet(self, workbook, move_lines, header_format, subheader_format,
                                    currency_format, text_format, total_format):
        """Create partner summary sheet"""
        worksheet = workbook.add_worksheet('Partner Summary')
        
        # Set column widths
        worksheet.set_column('A:A', 30)  # Partner
        worksheet.set_column('B:B', 15)  # Currency
        worksheet.set_column('C:C', 15)  # Total Debit
        worksheet.set_column('D:D', 15)  # Total Credit
        worksheet.set_column('E:E', 15)  # Balance
        worksheet.set_column('F:F', 10)  # Line Count
        
        # Write headers
        headers = ['Partner', 'Currency', 'Total Debit', 'Total Credit', 'Balance', 'Transactions']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Group by partner and currency
        partner_summary = {}
        for line in move_lines:
            key = (line.partner_id.id, line.currency_id.id if line.currency_id else 0)
            if key not in partner_summary:
                partner_summary[key] = {
                    'partner_name': line.partner_id.name,
                    'currency_name': line.currency_id.name if line.currency_id else 'No Currency',
                    'total_debit': 0,
                    'total_credit': 0,
                    'count': 0
                }
            
            partner_summary[key]['total_debit'] += line.debit_amount or 0
            partner_summary[key]['total_credit'] += line.credit_amount or 0
            partner_summary[key]['count'] += 1
        
        # Write data
        row = 1
        for key, data in sorted(partner_summary.items()):
            balance = data['total_debit'] - data['total_credit']
            
            worksheet.write(row, 0, data['partner_name'], text_format)
            worksheet.write(row, 1, data['currency_name'], text_format)
            worksheet.write(row, 2, data['total_debit'], currency_format)
            worksheet.write(row, 3, data['total_credit'], currency_format)
            worksheet.write(row, 4, balance, currency_format)
            worksheet.write(row, 5, data['count'], text_format)
            row += 1

    def _create_currency_summary_sheet(self, workbook, move_lines, header_format, subheader_format,
                                     currency_format, text_format, total_format):
        """Create currency summary sheet"""
        worksheet = workbook.add_worksheet('Currency Summary')
        
        # Set column widths
        worksheet.set_column('A:A', 15)  # Currency
        worksheet.set_column('B:B', 15)  # Total Debit
        worksheet.set_column('C:C', 15)  # Total Credit
        worksheet.set_column('D:D', 15)  # Balance
        worksheet.set_column('E:E', 12)  # Partners
        worksheet.set_column('F:F', 12)  # Transactions
        
        # Write headers
        headers = ['Currency', 'Total Debit', 'Total Credit', 'Balance', 'Partners', 'Transactions']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Group by currency
        currency_summary = {}
        for line in move_lines:
            currency_id = line.currency_id.id if line.currency_id else 0
            currency_name = line.currency_id.name if line.currency_id else 'No Currency'
            
            if currency_id not in currency_summary:
                currency_summary[currency_id] = {
                    'currency_name': currency_name,
                    'total_debit': 0,
                    'total_credit': 0,
                    'partners': set(),
                    'count': 0
                }
            
            currency_summary[currency_id]['total_debit'] += line.debit_amount or 0
            currency_summary[currency_id]['total_credit'] += line.credit_amount or 0
            currency_summary[currency_id]['partners'].add(line.partner_id.id)
            currency_summary[currency_id]['count'] += 1
        
        # Write data
        row = 1
        for currency_id, data in sorted(currency_summary.items()):
            balance = data['total_debit'] - data['total_credit']
            
            worksheet.write(row, 0, data['currency_name'], text_format)
            worksheet.write(row, 1, data['total_debit'], currency_format)
            worksheet.write(row, 2, data['total_credit'], currency_format)
            worksheet.write(row, 3, balance, currency_format)
            worksheet.write(row, 4, len(data['partners']), text_format)
            worksheet.write(row, 5, data['count'], text_format)
            row += 1

    def _create_account_summary_sheet(self, workbook, move_lines, header_format, subheader_format,
                                    currency_format, text_format, total_format):
        """Create account summary sheet"""
        worksheet = workbook.add_worksheet('Account Summary')
        
        # Set column widths
        worksheet.set_column('A:A', 25)  # Account
        worksheet.set_column('B:B', 15)  # Currency
        worksheet.set_column('C:C', 15)  # Total Debit
        worksheet.set_column('D:D', 15)  # Total Credit
        worksheet.set_column('E:E', 15)  # Balance
        worksheet.set_column('F:F', 12)  # Partners
        worksheet.set_column('G:G', 12)  # Transactions
        
        # Write headers
        headers = ['Account', 'Currency', 'Total Debit', 'Total Credit', 'Balance', 'Partners', 'Transactions']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Group by account and currency
        account_summary = {}
        for line in move_lines:
            key = (line.account_id.id, line.currency_id.id if line.currency_id else 0)
            if key not in account_summary:
                account_summary[key] = {
                    'account_name': f"{line.account_id.code} - {line.account_id.name}",
                    'currency_name': line.currency_id.name if line.currency_id else 'No Currency',
                    'total_debit': 0,
                    'total_credit': 0,
                    'partners': set(),
                    'count': 0
                }
            
            account_summary[key]['total_debit'] += line.debit_amount or 0
            account_summary[key]['total_credit'] += line.credit_amount or 0
            account_summary[key]['partners'].add(line.partner_id.id)
            account_summary[key]['count'] += 1
        
        # Write data
        row = 1
        for key, data in sorted(account_summary.items()):
            balance = data['total_debit'] - data['total_credit']
            
            worksheet.write(row, 0, data['account_name'], text_format)
            worksheet.write(row, 1, data['currency_name'], text_format)
            worksheet.write(row, 2, data['total_debit'], currency_format)
            worksheet.write(row, 3, data['total_credit'], currency_format)
            worksheet.write(row, 4, balance, currency_format)
            worksheet.write(row, 5, len(data['partners']), text_format)
            worksheet.write(row, 6, data['count'], text_format)
            row += 1

    def download_excel_file(self):
        """Download the generated Excel file"""
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model={self._name}&id={self.id}&field=excel_file&download=true&filename={self.file_name}',
            'target': 'self',
        }