# -*- coding: utf-8 -*-

import json
import operator
import datetime
import functools
import logging
import werkzeug
import io
from datetime import timedelta
from odoo import http
from odoo.http import content_disposition, request, serialize_exception as _serialize_exception
from odoo.tools import osutil, pycompat
from odoo.tools.misc import xlsxwriter
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo.addons.web.controllers.main import ExportFormat as BaseExportFormat, GroupsTreeNode as BaseGroupsTreeNode
_logger = logging.getLogger(__name__)



def serialize_exception(f):
    @functools.wraps(f)
    def wrap(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            _logger.exception("An exception occurred during an http request")
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return werkzeug.exceptions.InternalServerError(json.dumps(error))
    return wrap


class BalanceExcelExport(BaseExportFormat, http.Controller):

    @http.route('/web/balance_export/xlsx', type='http', auth="user")
    @serialize_exception
    def index(self, data):
        return self.base(data)


    @property
    def content_type(self):
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


    @property
    def extension(self):
        return '.xlsx'


    def base(self, data):
        params = json.loads(data)
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

        Model = request.env[model].with_context(import_compat=import_compat, **params.get('context', {}))
        if not Model._is_an_ordinary_table():
            fields = [field for field in fields if field['name'] != 'id']

        header_data = params.get('context', {})

        field_names = [f['name'] for f in fields]
        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]

        groupby = params.get('groupby')
        if not import_compat and groupby:
            groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby]
            domain = [('id', 'in', ids)] if ids else domain
            groups_data = Model.read_group(domain, [x if x != '.id' else 'id' for x in field_names], groupby, lazy=False)

            # read_group(lazy=False) returns a dict only for final groups (with actual data),
            # not for intermediary groups. The full group tree must be re-constructed.
            tree = BaseGroupsTreeNode(Model, field_names, groupby, groupby_type)
            for leaf in groups_data:
                tree.insert_leaf(leaf)

            response_data = self.from_group_data(fields, tree, params)
        else:
            records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)

            export_data = records.export_data(field_names).get('datas',[])
            # response_data = self.from_data(columns_headers, export_data)
            response_data = self.from_data(columns_headers, export_data, params)

        # TODO: call `clean_filename` directly in `content_disposition`?
        return request.make_response(response_data,
            headers=[('Content-Disposition',
                            content_disposition(
                                osutil.clean_filename(self.filename(model) + self.extension))),
                     ('Content-Type', self.content_type)],
        )
    
    
    def header_metadata(self, params, xlsx_writer, summary_data=None, running_balance=None):
        """Write headers with styling and return next available row"""
        row = 0
        # xlsx_writer.write(31, 0, params, xlsx_writer.header_style)
        # Company name with special style
        partner_id = params.get('default_partner_id')
        if partner_id:
            partner_record = request.env['res.partner'].sudo().browse(partner_id)
            if partner_record.exists() and partner_record.company_id:
                company_name = partner_record.company_id.name
                xlsx_writer.worksheet.merge_range(row, 0, row, 8, f"{company_name}", xlsx_writer.company_header_style)
                row += 1
        
        # Report title with special style
        action_name = params.get('action_name', '')
        report_title = f"{action_name}" if action_name else "STATEMENT OF ACCOUNT - DETAILED ANALYSIS"
        xlsx_writer.worksheet.merge_range(row, 0, row, 8, report_title, xlsx_writer.report_title_style)
        row += 2

        xlsx_writer.worksheet.merge_range(row, 0, row, 8, "EXECUTIVE SUMMARY", xlsx_writer.section_header_style)
        row += 1
        
        # Other metadata with regular style
        partner_name = params.get('partner_name', '')
        if partner_name:
            xlsx_writer.write(row, 0, "Partner:", xlsx_writer.partner_name_style)
            xlsx_writer.worksheet.merge_range(row, 1, row, 8, partner_name, xlsx_writer.partner_name_style)
            row += 1

        date_from = params.get('date_from')
        date_to = params.get('date_to')

        oldest_date = self.get_oldest_date_for_partner(partner_id)
        
        # Report Period row - multiple labels and values
        period = f"{date_from or oldest_date} to {date_to or datetime.datetime.now().strftime('%Y-%m-%d')}"
        xlsx_writer.write(row, 0, "Report Period:", xlsx_writer.summary_metric_style)
        xlsx_writer.worksheet.merge_range(row, 1, row, 2, period, xlsx_writer.base_style)
        
        export_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        xlsx_writer.write(row, 4, "Generated:", xlsx_writer.summary_metric_style)
        xlsx_writer.worksheet.merge_range(row, 5, row, 6, export_date, xlsx_writer.base_style)

        xlsx_writer.write(row, 7, "Days:", xlsx_writer.summary_metric_style)
        xlsx_writer.write(row, 8, "14 days", xlsx_writer.base_style)
        row += 1


        period_movement = running_balance['closing_balance'] - (summary_data['balance'] if summary_data['balance'] else 0.0)

        # Financial summary row
        xlsx_writer.write(row, 0, "Opening Balance:", xlsx_writer.summary_metric_style)
        xlsx_writer.worksheet.merge_range(row, 1, row, 2, summary_data['balance'], xlsx_writer.summary_value_style if summary_data['balance'] >= 0 else xlsx_writer.negative_value_style)
        xlsx_writer.write(row, 3, "Period Movement", xlsx_writer.summary_metric_style)
        xlsx_writer.worksheet.merge_range(row, 4, row, 5, period_movement, xlsx_writer.negative_value_style if period_movement < 0 else xlsx_writer.summary_value_style)
        xlsx_writer.write(row, 6, "Closing Balance:", xlsx_writer.summary_metric_style)
        xlsx_writer.worksheet.merge_range(row, 7, row, 8, running_balance['closing_balance'], xlsx_writer.summary_value_style if running_balance['closing_balance'] >= 0 else xlsx_writer.negative_value_style)
        row += 1
        
        return row


    def from_data(self, fields, rows, params=None):
        ctx = params.get('context', {})
        with BalanceExportXlsxWriter(fields, len(rows)) as xlsx_writer:

            # Get opening balance
            opening_data = self.calculate_opening_balance(params)
            running_balance = self.calculate_period_summary(params, rows)

            row_index = self.header_metadata(ctx, xlsx_writer, opening_data, running_balance)

            opening_debit = 0
            opening_credit = 0
            
            # Write opening balance row if exists
            if opening_data['balance'] != 0.0:
                opening_row = self.create_opening_balance_row(opening_data)
                opening_debit = opening_row[4] if opening_row[4] else 0  # Debit column
                opening_credit = opening_row[5] if opening_row[5] else 0

                for cell_index, cell_value in enumerate(opening_row):
                    xlsx_writer.write_cell_with_style(9, cell_index, cell_value, xlsx_writer.opening_balance_style)
                    # xlsx_writer.write_cell(31, cell_index, params)
                period_start_row = 10  # Period data starts at row 8
            else:
                period_start_row = 9  # Period data starts at row 7
                opening_data['balance'] = 0.0  # Ensure balance is 0 if no opening balance
            
            # Write period data rows with updated running balance
            running_balance = opening_data['balance']  # Start from opening balance
            for row_index, row in enumerate(rows):
                # Update running balance for this row
                debit = float(row[4]) if row[4] else 0.0
                credit = float(row[5]) if row[5] else 0.0
                running_balance += debit - credit
                
                # Update the cumulated balance column (assuming it's column 5)
                row = list(row)  # Convert to list to modify
                row[6] = running_balance  # Update cumulated balance
                
                for cell_index, cell_value in enumerate(row):
                    if isinstance(cell_value, (list, tuple)):
                        cell_value = pycompat.to_text(cell_value)
                    xlsx_writer.write_cell(period_start_row + row_index, cell_index, cell_value)

            # Add totals row after all data
            totals_row = period_start_row + len(rows) + 1  # +1 for spacing
            xlsx_writer._write_totals_from_rows(totals_row, rows, fields, opening_debit, opening_credit)


        return xlsx_writer.value

            

    def get_oldest_date_for_partner(self, partner_id):
        """Get the oldest transaction date for a specific partner"""
        if not partner_id:
            return 'Beginning'
        
        result = request.env['account.move.line'].sudo().read_group(
            domain=[('partner_id', '=', partner_id)],
            fields=['date:min'],
            groupby=[]
        )
        
        if result and result[0].get('date'):
            return result[0]['date']
        
        return 'Beginning'


    def export_partner_balance(self, **params):
        ctx = params.get('context', {})
        date_from = ctx.get('date_from')
        partner_id = ctx.get('default_partner_id')
        
        # Query 1: Get initial balance (current domain)
        balance_records = request.env['account.move.line.report'].with_context(
            date_from=date_from
        ).search_read(
            domain=[('partner_id', '=', partner_id),
                    ('date', '>=', date_from),
                    ],
            fields=['currency_id', 'initial_balance_amount_currency']
        )
        
        # Query 2: Get debit/credit amounts (different domain)
        debit_credit_records = request.env['account.move.line.report'].search_read(
            domain=[('partner_id', '=', partner_id),
                    ('date', '<', date_from),
                    ('move_id.journal_id.code', '!=', 'KRFRK')
                    ],
            fields=['currency_id', 'debit_amount', 'credit_amount']
        )
        
        # Process initial balances
        currency_balances = {}
        for record in balance_records:
            currency_name = record['currency_id'][1] if record['currency_id'] else 'Unknown'
            balance = record['initial_balance_amount_currency'] or 0
            
            if currency_name not in currency_balances:
                currency_balances[currency_name] = {'balance': 0, 'debit': 0, 'credit': 0}
            currency_balances[currency_name]['balance'] = balance
        
        # Process debit/credit amounts
        for record in debit_credit_records:
            currency_name = record['currency_id'][1] if record['currency_id'] else 'Unknown'
            debit = record['debit_amount'] or 0
            credit = record['credit_amount'] or 0
            
            if currency_name not in currency_balances:
                currency_balances[currency_name] = {'balance': 0, 'debit': 0, 'credit': 0}
                
            currency_balances[currency_name]['debit'] += debit
            currency_balances[currency_name]['credit'] += credit

        return currency_balances
    

    def calculate_opening_balance(self, params, filter_field=None, filter_value=None):
        """Calculate opening balance before date_from for the given partner"""

        ctx = params.get('context', {})
        date_from = ctx.get('date_from')
        partner_id = ctx.get('default_partner_id')
        
        if not date_from or not partner_id:
            return {
                'debit': 0.0,
                'credit': 0.0,
                'balance': 0.0,
                'balance_currency': 0.0,
                'currency': filter_value if filter_field == 'currency_id.name' else 'TRY',
                'date': ''
            }
        
        # Calculate opening balance
        Model = request.env['account.move.line.report']
        opening_domain = [
            ('partner_id', '=', partner_id),
            ('date', '<', date_from),
            ('move_id.journal_id.code', '!=', 'KRFRK')
        ]
        
        # Add specific field filter if provided
        if filter_field and filter_value:
            opening_domain.append((filter_field, '=', filter_value))
        
        opening_records = Model.search(opening_domain)
        debit = sum(opening_records.mapped('debit'))
        credit = sum(opening_records.mapped('credit'))
        balance = sum(opening_records.mapped('debit')) - sum(opening_records.mapped('credit'))
        
        # Determine currency for display
        currency = 'TRY'  # Default
        if filter_field == 'currency_id.name':
            currency = filter_value
        elif opening_records:
            currency = opening_records[0].currency_id.name or 'TRY'
        
        opening_date = (datetime.datetime.strptime(date_from, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        
        return {
            'debit': debit,
            'credit': credit,
            'balance': balance,
            'currency': currency,
            'date': opening_date
        }


    def calculate_grouped_opening_balance(self, params, filter_field=None, filter_value=None):
        """Calculate opening balance before date_from for the given partner"""

        ctx = params.get('context', {})
        date_from = ctx.get('date_from')
        partner_id = ctx.get('default_partner_id')
        
        if not date_from or not partner_id:
            return {
                'debit': 0.0,
                'credit': 0.0,
                'balance': 0.0,
                'balance_currency': 0.0,
                'currency': filter_value if filter_field == 'currency_id.name' else 'TRY',
                'date': ''
            }
        
        # Get corrected balances from our method
        currency_balances = self.export_partner_balance(**params)  # {"TRY": 87300.94, "USD": 90908.91}
        
        # Calculate opening balance (for debit/credit - keep original logic)
        Model = request.env['account.move.line.report']
        opening_domain = [
            ('partner_id', '=', partner_id),
            ('date', '<', date_from),
            ('move_id.journal_id.code', '!=', 'KRFRK')
        ]
        
        # Add specific field filter if provided
        if filter_field and filter_value:
            opening_domain.append((filter_field, '=', filter_value))
        
        opening_records = Model.search(opening_domain)
        # debit = sum(opening_records.mapped('debit'))
        # credit = sum(opening_records.mapped('credit'))
        
        # Determine currency for display
        currency = 'TRY'  # Default
        if filter_field == 'currency_id.name':
            currency = filter_value
        elif opening_records:
            currency = opening_records[0].currency_id.name or 'TRY'
        
        # Use corrected balance from our method instead of calculating
        balance = currency_balances.get(currency, {}).get('balance', 0.0)
        debit = currency_balances.get(currency, {}).get('debit', 0.0)
        credit = currency_balances.get(currency, {}).get('credit', 0.0)
        
        opening_date = (datetime.datetime.strptime(date_from, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        
        return {
            'debit': debit,
            'credit': credit,
            'balance': balance,  # Updated with corrected value
            'currency': currency,
            'date': opening_date
        }

    def calculate_period_summary(self, params, data):
        """
        Calculate period summary for both grouped and ungrouped data
        Args:
            params: Parameters dictionary
            data: Either GroupsTreeNode (grouped) or list (ungrouped data)
        """
        opening_data = self.calculate_opening_balance(params)
        
        # Calculate running balance through all rows
        running_balance = opening_data['balance']
        total_debit = 0.0
        total_credit = 0.0
        
        # Detect data type and extract rows accordingly
        if hasattr(data, 'children'):
            # Case 1: Grouped data (GroupsTreeNode)
            all_rows = self._extract_rows_from_groups(data)
        else:
            # Case 2: Ungrouped data (list of rows)
            all_rows = data
        
        # Process all rows
        for row in all_rows:
            debit = float(row[4]) if len(row) > 4 and row[4] else 0.0
            credit = float(row[5]) if len(row) > 5 and row[5] else 0.0
            running_balance += debit - credit
            total_debit += debit
            total_credit += credit
        
        return {
            'opening_balance': opening_data['balance'],
            'closing_balance': running_balance,
            'period_movement': total_debit - total_credit,
            'total_debit': total_debit,
            'total_credit': total_credit,
        }


    def _extract_rows_from_groups(self, groups_node):
        """
        Recursively extract all data rows from GroupsTreeNode structure
        """
        rows_data = []
        
        # Get data from current group
        if hasattr(groups_node, 'data') and groups_node.data:
            rows_data.extend(groups_node.data)
        
        # Get data from child groups recursively
        if hasattr(groups_node, 'children'):
            for child_group in groups_node.children.values():
                rows_data.extend(self._extract_rows_from_groups(child_group))
        
        return rows_data


    def create_opening_balance_row(self, opening_data):
        """Create opening balance row data"""
        return [
            opening_data['date'],           
            '',                              
            'Opening Balance',             
            '',                            
            opening_data['debit'],         
            opening_data['credit'],          
            opening_data['balance'],       
            '',                            
            # opening_data['balance_currency'] # Amount Currency
            '',
        ]


    def from_group_data(self, fields, groups, params=None):
        ctx = params.get('context', {})
        with BalanceGroupExportXlsxWriter(fields, groups.count) as xlsx_writer:

            running_balance = self.calculate_period_summary(params, groups)
            xlsx_writer.write(31, 0, running_balance, xlsx_writer.partner_name_style)
            opening_data = self.calculate_opening_balance(params)
            initial_balances = self.export_partner_balance(**params)
            xlsx_writer.write(35, 0, initial_balances, xlsx_writer.partner_name_style)
            row_index = self.header_metadata(ctx, xlsx_writer, opening_data, running_balance)
            
            # Start groups from row 9
            groups_start_row = 9
            x, y = groups_start_row, 0
            
            # Smart detection of grouping field
            groupby = params.get('groupby', [])
            groupby_field = groupby[0].split(':')[0] if groupby else ''
            
            # Determine filter approach based on grouping field
            opening_balances = {}
            grouped_balances = {}
            for group_name in groups.children.keys():
                # xlsx_writer.write(31, 0, group_name, xlsx_writer.partner_name_style)
                filter_field = None
                filter_value = None
                
                if groupby_field == 'currency_id':
                    # Currency grouping - filter by currency
                    filter_field = 'currency_id.name'
                    filter_value = group_name[1] if isinstance(group_name, tuple) else group_name
                elif groupby_field == 'account_id':
                    # Account grouping - filter by account
                    filter_field = 'account_id.id'
                    filter_value = group_name[0] if isinstance(group_name, tuple) else group_name
                else:
                    # Other grouping - no filtering (total opening balance)
                    filter_field = None
                    filter_value = None
                opening_data = self.calculate_grouped_opening_balance(params, filter_field, filter_value)
                # grouped_balance = self.calculate_grouped_opening_balance(params, filter_field, filter_value)
                # grouped_balances[group_name] = grouped_balance
                # Use group_name as key for consistency
                opening_balances[group_name] = opening_data
            
            # xlsx_writer.write(37, 0, opening_balances, xlsx_writer.partner_name_style)
            # xlsx_writer.write(38, 0, grouped_balances, xlsx_writer.partner_name_style)
            # Update group balances with respective opening balances
            self._update_group_balances_per_currency(groups, opening_balances)
            
            # Write groups with opening balances
            for group_name, group in groups.children.items():
                x, y = xlsx_writer.write_group(x, y, group_name, group, opening_balances)

        return xlsx_writer.value


    def _update_group_balances_per_currency(self, groups, opening_balances):
        """Update cumulated balances in group data with per-currency opening balances"""
        
        def update_group_recursive(group_node, currency_key):
            opening_balance = opening_balances.get(currency_key, {}).get('balance', 0.0)
            running_balance = opening_balance
            
            # Update data records in this group
            for record in group_node.data:
                debit = float(record[4]) if len(record) > 4 and record[4] else 0.0
                credit = float(record[5]) if len(record) > 5 and record[5] else 0.0
                running_balance += debit - credit
                
                # Update cumulated balance column (assuming index 5)
                if len(record) > 6:
                    record[6] = running_balance
            
            # Update child groups recursively
            for child_group in group_node.children.values():
                update_group_recursive(child_group, currency_key)
        
        # Start updating from root groups
        for group_name, group in groups.children.items():
            currency = group_name[1] if isinstance(group_name, tuple) else group_name
            update_group_recursive(group, currency)


    

class BalanceExportXlsxWriter:

    def __init__(self, field_names, row_count=0):
        self.field_names = field_names
        self.output = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(self.output, {'in_memory': True})
        self.base_style = self.workbook.add_format({'text_wrap': True,'font_size': 8,'align': 'left','valign': 'vcenter','border': 1})
        self.header_style = self.workbook.add_format({'bold': True})
        self.header_bold_style = self.workbook.add_format({'text_wrap': True, 'bold': True, 'bg_color': '#e9ecef'})
        self.date_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd', 'font_size': 8,'align': 'left','valign': 'vcenter','border': 1})
        self.datetime_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd hh:mm:ss', 'font_size': 8,'align': 'left','valign': 'vcenter','border': 1})
        self.worksheet = self.workbook.add_worksheet()
        self.value = False
        self.float_format = '#,##0.00'
        decimal_places = [res['decimal_places'] for res in request.env['res.currency'].search_read([], ['decimal_places'])]
        self.monetary_format = f'#,##0.{max(decimal_places or [2]) * "0"}'
        self.company_header_style = self.workbook.add_format({'bold': True,'font_size': 12,'align': 'center','valign': 'vcenter','bg_color': '#1e3a8a','font_color': 'white','border': 1,'border_color': '#3b82f6'})
        self.report_title_style = self.workbook.add_format({'bold': True,'font_size': 12,'align': 'center','valign': 'vcenter','bg_color': '#f1f5f9','font_color': '#1e40af',    'border': 1,'border_color': '#e2e8f0'})
        self.summary_metric_style = self.workbook.add_format({'align': 'left','valign': 'vcenter','text_wrap': True, 'font_size': 10,'bold': True,'bg_color': '#ecfdf5','border': 1})
        self.metadata_style = self.workbook.add_format({'bg_color': '#f8f9fa','border': 1})
        self.section_header_style = self.workbook.add_format({'bold': True,'align': 'center','valign': 'vcenter','bg_color': '#374151','font_color': 'white','border': 1})
        self.summary_value_style = self.workbook.add_format({'num_format': '#,##0.00', 'bold': True,'align': 'center','valign': 'vcenter', 'font_color': '#059669','bg_color': '#f0fdf4','border': 1})
        self.negative_value_style = self.workbook.add_format({'align': 'center','valign': 'vcenter', 'bold': True,'font_color': '#dc2626','border': 1, 'num_format': '#,##0.00'})
        self.transaction_header_style = self.workbook.add_format({'text_wrap': True,'bold': True,'align': 'left','valign': 'vcenter','bg_color': '#475569','font_color': 'white','border': 1,'font_size': 10})
        self.opening_balance_style = self.workbook.add_format({'num_format': '#,##0.00', 'align': 'left','valign': 'vcenter','text_wrap': True,'bold': True,'bg_color': '#dbeafe','border': 1, 'font_size': 8})
        self.partner_name_style = self.workbook.add_format({'align': 'left','valign': 'vcenter', 'text_wrap': True,'bold': True,'bg_color': '#f3f4f6','border': 1, 'font_size': 11})
        self.monetary_style = self.workbook.add_format({ 'bold': True, 'bg_color': '#4F81BD', 'font_size': 8, 'font_color': 'white', 'border': 1, 'align': 'center', 'num_format': self.monetary_format})

        if row_count > self.worksheet.xls_rowmax:
            raise UserError(_('There are too many rows (%s rows, limit: %s) to export as Excel 2007-2013 (.xlsx) format. Consider splitting the export.') % (row_count, self.worksheet.xls_rowmax))


    def __enter__(self):
        self.write_header()
        return self


    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()


    def write_cell_with_style(self, row, column, cell_value, style):
        self.write(row, column, cell_value, style)
  

    def write_header(self):
        for i, fieldname in enumerate(self.field_names):
            self.write(8, i, fieldname, self.transaction_header_style)
        self.worksheet.set_column(0, i, 9) # around 220 pixels


    def close(self):
        self.workbook.close()
        with self.output:
            self.value = self.output.getvalue()


    @staticmethod
    def _safe_cell_value(val):
        # Keep "native" excel types untouched
        if val is None:
            return ""                          # avoid TypeError in sharedStrings
        if isinstance(val, (int, float, bool)):
            return val
        if isinstance(val, (datetime.datetime, datetime.date)):
            return val
        if isinstance(val, (bytes, bytearray)):
            try:
                return val.decode("utf-8")
            except Exception:
                return val.decode("latin-1", "ignore")

        # Odoo relations sometimes come as (id, name)
        if isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], int):
            return "" if val[1] is None else str(val[1])

        # Structures: make them readable instead of crashing xlsxwriter
        if isinstance(val, (dict, list, set, tuple)):
            try:
                return json.dumps(val, ensure_ascii=False, default=str)
            except Exception:
                return str(val)

        return str(val)


    def write(self, row, column, cell_value, style=None):
        cell_value = self._safe_cell_value(cell_value)
        self.worksheet.write(row, column, cell_value, style)


    def write_cell(self, row, column, cell_value):
        cell_style = self.base_style

        if isinstance(cell_value, bytes):
            try:
                # because xlsx uses raw export, we can get a bytes object
                # here. xlsxwriter does not support bytes values in Python 3 ->
                # assume this is base64 and decode to a string, if this
                # fails note that you can't export
                cell_value = pycompat.to_text(cell_value)
            except UnicodeDecodeError:
                raise UserError(_("Binary fields can not be exported to Excel unless their content is base64-encoded. That does not seem to be the case for %s.", self.field_names)[column])

        if isinstance(cell_value, str):
            if len(cell_value) > self.worksheet.xls_strmax:
                cell_value = _("The content of this cell is too long for an XLSX file (more than %s characters). Please use the CSV format for this export.", self.worksheet.xls_strmax)
            else:
                cell_value = cell_value.replace("\r", " ")
        elif isinstance(cell_value, datetime.datetime):
            cell_style = self.datetime_style
        elif isinstance(cell_value, datetime.date):
            cell_style = self.date_style
        elif isinstance(cell_value, float):
            cell_style.set_num_format(self.float_format)
        self.write(row, column, cell_value, cell_style)


    def _write_totals_from_rows(self, row, rows_data, fields, opening_debit=0, opening_credit=0):
        # Calculate totals from period transactions
        total_debit = 0
        total_credit = 0
        
        # Find debit and credit column positions
        debit_column_index = None
        credit_column_index = None
        
        for field_index, field_name in enumerate(fields):
            if 'debit' in field_name.lower():
                debit_column_index = field_index
            elif 'credit' in field_name.lower():
                credit_column_index = field_index
        
        # Calculate period totals
        if debit_column_index is not None:
            for row_data in rows_data:
                if debit_column_index < len(row_data):
                    cell_value = row_data[debit_column_index]
                    if isinstance(cell_value, (int, float)):
                        total_debit += cell_value
                    elif isinstance(cell_value, str):
                        try:
                            total_debit += float(cell_value)
                        except (ValueError, TypeError):
                            pass
        
        if credit_column_index is not None:
            for row_data in rows_data:
                if credit_column_index < len(row_data):
                    cell_value = row_data[credit_column_index]
                    if isinstance(cell_value, (int, float)):
                        total_credit += cell_value
                    elif isinstance(cell_value, str):
                        try:
                            total_credit += float(cell_value)
                        except (ValueError, TypeError):
                            pass
        
        # ADD opening balance to period totals
        total_debit += opening_debit
        total_credit += opening_credit
        
        # Calculate final balance
        total_balance = total_debit - total_credit
        
        # Round values
        total_debit = round(total_debit, 2)
        total_credit = round(total_credit, 2)
        total_balance = round(total_balance, 2)
        
        # Write static totals row
        for column in range(len(fields)):
            if column == 0:
                # Column 0: "Total" label
                self.write(row, column, _("Total"), self.header_bold_style)
            elif column == 4:
                # Column 4: Total debit
                self.write(row, column, total_debit, self.monetary_style)
            elif column == 5:
                # Column 5: Total credit
                self.write(row, column, total_credit, self.monetary_style)
            elif column == 6:
                # Column 6: Total balance (debit - credit)
                self.write(row, column, total_balance, self.monetary_style)
            else:
                # All other columns: empty
                self.write(row, column, '', self.header_bold_style)

        return row + 2, 0
    

class BalanceGroupExportXlsxWriter(BalanceExportXlsxWriter):

    def __init__(self, fields, row_count=0):
        super().__init__([f['label'].strip() for f in fields], row_count)
        self.fields = fields


    def _write_group_totals(self, row, group, balance=None,balance_value=None):
        column = 0
        aggregates = group.aggregated_values
        # self.write(31, 0, balance[3], self.partner_name_style)
        self.write(row, column, _("Total"), self.header_bold_style)
        column += 1

        # Fields that need custom calculation instead of sum
        calculated_fields = {
            'debit': lambda: aggregates.get('debit', 0) + balance[4],
            'debit_amount': lambda: aggregates.get('debit_amount', 0) + (balance[4] if balance else 0),
            'credit': lambda: aggregates.get('credit', 0) + balance[5],
            'credit_amount': lambda: aggregates.get('credit_amount', 0) + (balance[5] if balance else 0),
            'balance': lambda: balance_value if balance_value is not None else (aggregates.get('debit', 0) - abs(aggregates.get('credit', 0))) + (balance[6] if balance else 0),
            'balance_amount': lambda: balance_value if balance_value is not None else (aggregates.get('debit_amount', 0) - abs(aggregates.get('credit_amount', 0))) + (balance[6] if balance else 0),
            'cumulated_balance': lambda: balance_value if balance_value is not None else (aggregates.get('debit', 0) - abs(aggregates.get('credit', 0))) + (balance[6] if balance else 0),
            'amount_currency': lambda: '',
            
        }

        for field in self.fields[1:]:
            field_name = field['name']
            
            # Check if field needs custom calculation
            if field_name in calculated_fields:
                aggregated_value = calculated_fields[field_name]()
            else:
                aggregated_value = aggregates.get(field_name)
            
            # Apply formatting based on field type
            if field.get('type') == 'monetary':
                self.header_bold_style.set_num_format(self.monetary_format)
            elif field.get('type') == 'float':
                self.header_bold_style.set_num_format(self.float_format)
            else:
                aggregated_value = str(aggregated_value if aggregated_value is not None else '')
                
            self.write(row, column, aggregated_value, self.monetary_style)
            column += 1

        return row + 2, 0
    

    def write_group(self, row, column, group_name, group, opening_balances, group_depth=0):
        group_name_display = group_name[1] if isinstance(group_name, tuple) and len(group_name) > 1 else group_name
        currency = group_name[1] if isinstance(group_name, tuple) else group_name
        
        if group._groupby_type[group_depth] != 'boolean':
            group_name_display = group_name_display or _("Undefined")

        # Write group header
        row, column = self._write_group_header(row, column, group_name_display, group, group_depth)

        # Write transaction header
        row = self.write_group_header(row)
        opening_row = None
        # Write opening balance for this currency group
        balance_value = opening_balances.get(group_name, {}).get('balance', 0.0)
        if group_name in opening_balances and opening_balances[group_name]['balance'] != 0.0:
            opening_data = opening_balances[group_name]
            opening_row = self._create_opening_balance_row(opening_data)
            
            for cell_index, cell_value in enumerate(opening_row):
                if cell_index < len(self.field_names):
                    self.write(row, cell_index, cell_value, self.opening_balance_style)
            row += 1

        # Write child groups
        for child_group_name, child_group in group.children.items():
            row, column = self.write_group(row, column, child_group_name, child_group, opening_balances, group_depth + 1)

        
        # Write group data
        for record in group.data:
            row, column, balance_value = self._write_row(row, column, record, balance_value)
        
        # Write group totals
        row, column = self._write_group_totals(row, group, opening_row, balance_value)

        return row, column


    def _write_row(self, row, column, data, balance=None):
        debit = float(data[4]) if data[4] else 0.0
        credit = float(data[5]) if data[5] else 0.0
        balance_value = debit - credit
        if balance is None:
            balance = balance_value
        else:

            balance += balance_value
        data[6] = balance
        data = list(data)  # Convert to list to modify
            
            
        for value in data:
            self.write_cell(row, column, value)
            column += 1
        return row + 1, 0, balance


    def write_group_header(self, row):
        for i, fieldname in enumerate(self.field_names):
            self.write(row, i, fieldname, self.transaction_header_style)
        self.worksheet.set_column(0, i, 9)  # Column width
        return row + 1  # Return next row to continue from
    

    def _write_group_header(self, row, column, label, group, group_depth=0):
        label_text = '%s%s (%s)' % ('' * group_depth, label, group.count)

        # Write the label in the first column
        self.write(row, column, label_text, self.header_bold_style)

        # Apply the same style to all other columns in that row
        total_columns = len(self.fields)
        for col in range(1, total_columns):
            self.write(row, col, '', self.header_bold_style)

        return row + 1, 0
    

    def write_header(self):
        return
    

    def _create_opening_balance_row(self, opening_data):
        """Create opening balance row data using existing logic"""
        return [
            opening_data.get('date', ''),           # Date
            '',                                     # Journal Entry  
            'Opening Balance',                      # Label
            '',                                     # Reference
            opening_data.get('debit', 0.0),        # Debit
            opening_data.get('credit', 0.0),       # Credit  
            opening_data.get('balance', 0.0),      # Cumulated Balance
            '',
            opening_data.get('currency', ''),      # Currency
            '',
        ]
    
