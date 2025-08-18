# -*- coding: utf-8 -*-

import json
import operator
import datetime
from datetime import timedelta, date
import functools
import logging
import werkzeug
import io
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)



from odoo.http import content_disposition, request
from odoo.tools import osutil, pycompat
from odoo.tools.translate import _
from odoo.addons.web.controllers.main import ExportFormat as BaseExportFormat
from odoo.addons.web.controllers.main import GroupsTreeNode as BaseGroupsTreeNode




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

            response_data = self.from_group_data(fields, tree, header_data)
        else:
            records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)

            export_data = records.export_data(field_names).get('datas',[])
            # response_data = self.from_data(columns_headers, export_data)
            response_data = self.from_data(columns_headers, export_data, header_data)

        # TODO: call `clean_filename` directly in `content_disposition`?
        return request.make_response(response_data,
            headers=[('Content-Disposition',
                            content_disposition(
                                osutil.clean_filename(self.filename(model) + self.extension))),
                     ('Content-Type', self.content_type)],
        )
    
    def header_metadata(self, params):
        partner_name = params.get('partner_name', '')
        action_name = params.get('action_name', '')
        company_name = ''
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        partner_id = params.get('default_partner_id')

        if partner_id:
            partner_record = request.env['res.partner'].sudo().browse(partner_id)
            if partner_record.exists() and partner_record.company_id:
                company_name = partner_record.company_id.name

        oldest_date = self.get_oldest_date_for_partner(partner_id)

        header_data = [
            _("Report: %s") % action_name if action_name else "",
            f"Partner: {partner_name}" if partner_name else "",
            f"Company: {company_name}" if company_name else "",
            f"Export Date: {datetime.datetime.now().strftime('%Y-%m-%d')}",
            f"Date Range: {date_from or oldest_date} To {date_to or datetime.datetime.now().strftime('%Y-%m-%d')}",
        ]
        return [item for item in header_data if item]
    
    def from_data(self, fields, rows, params=None):
        with BalanceExportXlsxWriter(fields, len(rows)) as xlsx_writer:
            # Write model name in the first row if provided
            data = self.header_metadata(params)
            for row_index, header_info in enumerate(data):
                xlsx_writer.write(row_index, 0, header_info, xlsx_writer.header_style)

            # Get opening balance
            opening_data = self.calculate_opening_balance(params)

            opening_debit = 0
            opening_credit = 0
            
            # Write opening balance row if exists
            if opening_data['balance'] != 0.0:
                opening_row = self.create_opening_balance_row(opening_data)
                opening_debit = opening_row[3] if opening_row[3] else 0  # Debit column
                opening_credit = opening_row[4] if opening_row[4] else 0

                for cell_index, cell_value in enumerate(opening_row):
                    xlsx_writer.write_cell(7, cell_index, cell_value)
                period_start_row = 8  # Period data starts at row 8
            else:
                period_start_row = 7  # Period data starts at row 7
                opening_data['balance'] = 0.0  # Ensure balance is 0 if no opening balance
            
            # Write period data rows with updated running balance
            running_balance = opening_data['balance']  # Start from opening balance
            for row_index, row in enumerate(rows):
                # Update running balance for this row
                debit = float(row[3]) if row[3] else 0.0
                credit = float(row[4]) if row[4] else 0.0
                running_balance += debit - credit
                
                # Update the cumulated balance column (assuming it's column 5)
                row = list(row)  # Convert to list to modify
                row[5] = running_balance  # Update cumulated balance
                
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

    def calculate_opening_balance(self, params):
        """Calculate opening balance before date_from for the given partner"""
        date_from = params.get('date_from')
        partner_id = params.get('default_partner_id')
        
        if not date_from or not partner_id:
            return {
                'balance': 0.0,
                'balance_currency': 0.0,
                'currency': 'USD',
                'date': None
            }
        
        # Calculate opening balance
        Model = request.env['account.move.line.report']
        opening_domain = [
            ('partner_id', '=', partner_id),
            ('date', '<', date_from),
            ('move_id.journal_id.code', '!=', 'KRFRK')
        ]
        
        opening_records = Model.search(opening_domain)
        debit = sum(opening_records.mapped('debit'))
        credit = sum(opening_records.mapped('credit'))
        balance = sum(opening_records.mapped('debit')) - sum(opening_records.mapped('credit'))
        
        # Calculate currency amounts if needed
        balance_currency = sum(opening_records.mapped('amount_currency'))
        currency = opening_records[0].currency_id.name if opening_records else 'TRY'
        
        opening_date = (datetime.strptime(date_from, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        
        return {
            'debit': debit,
            'credit': credit,
            'balance': balance,
            'balance_currency': balance_currency,
            'currency': currency,
            'date': opening_date
        }

    def create_opening_balance_row(self, opening_data):
        """Create opening balance row data"""
        return [
            opening_data['date'],           # Date
            '',                            # Journal Entry  
            'Opening Balance',             # Label
            opening_data['debit'],         # Debit
            opening_data['credit'],        # Credit  
            opening_data['balance'],       # Cumulated Balance
            opening_data['currency'],      # Currency
            opening_data['balance_currency'] # Amount Currency
        ]
    

    def from_group_data(self, fields, groups, params=None):
        with BalanceGroupExportXlsxWriter(fields, groups.count) as xlsx_writer:
            # Write headers
            data = self.header_metadata(params)
            for row_index, header_info in enumerate(data):
                xlsx_writer.write(row_index, 0, header_info, xlsx_writer.header_style)
            
            # Get opening balance
            opening_data = self.calculate_opening_balance(params)
            
            # Write opening balance row if exists
            if opening_data['balance'] != 0.0:
                opening_row = self.create_opening_balance_row(opening_data)
                for cell_index, cell_value in enumerate(opening_row):
                    xlsx_writer.write(5, cell_index, cell_value, xlsx_writer.base_style)
                groups_start_row = 6  # Groups start after opening balance
            else:
                groups_start_row = 5  # Groups start normally
                opening_data['balance'] = 0.0  # Ensure balance is 0
            
            # Write groups with updated starting position
            x, y = groups_start_row, 0
            
            # Update group data to include opening balance in running calculations
            if opening_data['balance'] != 0.0:
                self._update_group_balances(groups, opening_data['balance'])
            
            for group_name, group in groups.children.items():
                x, y = xlsx_writer.write_group(x, y, group_name, group)

        return xlsx_writer.value

    def _update_group_balances(self, groups, opening_balance):
        """Update cumulated balances in group data to start from opening balance"""
        running_balance = opening_balance
        
        def update_group_recursive(group_node):
            nonlocal running_balance
            
            # Update data records in this group
            for record in group_node.data:
                debit = float(record[3]) if len(record) > 3 and record[3] else 0.0
                credit = float(record[4]) if len(record) > 4 and record[4] else 0.0
                running_balance += debit - credit
                
                # Update cumulated balance column (assuming index 5)
                if len(record) > 5:
                    record[5] = running_balance
            
            # Update child groups recursively
            for child_group in group_node.children.values():
                update_group_recursive(child_group)
        
        # Start updating from root groups
        for group in groups.children.values():
            update_group_recursive(group)


class BalanceExportXlsxWriter:

    def __init__(self, field_names, row_count=0):
        self.field_names = field_names
        self.output = io.BytesIO()
        self.workbook = xlsxwriter.Workbook(self.output, {'in_memory': True})
        self.base_style = self.workbook.add_format({'text_wrap': True})
        self.header_style = self.workbook.add_format({'bold': True})
        self.header_bold_style = self.workbook.add_format({'text_wrap': True, 'bold': True, 'bg_color': '#e9ecef'})
        self.date_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd'})
        self.datetime_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd hh:mm:ss'})
        self.worksheet = self.workbook.add_worksheet()
        self.value = False
        self.float_format = '#,##0.00'
        decimal_places = [res['decimal_places'] for res in request.env['res.currency'].search_read([], ['decimal_places'])]
        self.monetary_format = f'#,##0.{max(decimal_places or [2]) * "0"}'

        if row_count > self.worksheet.xls_rowmax:
            raise UserError(_('There are too many rows (%s rows, limit: %s) to export as Excel 2007-2013 (.xlsx) format. Consider splitting the export.') % (row_count, self.worksheet.xls_rowmax))

    def __enter__(self):
        self.write_header()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def write_header(self):
        for i, fieldname in enumerate(self.field_names):
            self.write(6, i, fieldname, self.header_style)
        self.worksheet.set_column(0, i, 30) # around 220 pixels

    def close(self):
        self.workbook.close()
        with self.output:
            self.value = self.output.getvalue()

    def write(self, row, column, cell_value, style=None):
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

        # Create monetary style
        monetary_style = self.workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'num_format': self.monetary_format
        })
        
        # Write static totals row
        for column in range(len(fields)):
            if column == 0:
                # Column 0: "Total" label
                self.write(row, column, _("Total"), self.header_bold_style)
            elif column == 3:
                # Column 3: Total debit
                self.write(row, column, total_debit, monetary_style)
            elif column == 4:
                # Column 4: Total credit
                self.write(row, column, total_credit, monetary_style)
            elif column == 5:
                # Column 5: Total balance (debit - credit)
                self.write(row, column, total_balance, monetary_style)
            else:
                # All other columns: empty
                self.write(row, column, '', self.header_bold_style)

        return row + 2, 0
    

class BalanceGroupExportXlsxWriter(BalanceExportXlsxWriter):

    def __init__(self, fields, row_count=0):
        super().__init__([f['label'].strip() for f in fields], row_count)
        self.fields = fields


    def _write_group_totals(self, row, group):
        column = 0  # skip the first column (reserved for group label or index)
        aggregates = group.aggregated_values
        self.write(row, column, _("Total"), self.header_bold_style)
        column += 1

        # Fields that need custom calculation instead of sum
        calculated_fields = {
            'balance': lambda: aggregates.get('debit', 0) - abs(aggregates.get('credit', 0)),
            'balance_amount': lambda: aggregates.get('debit_amount', 0) - abs(aggregates.get('credit_amount', 0)),
            'cumulated_balance': lambda: aggregates.get('debit', 0) - abs(aggregates.get('credit', 0)),
            'cumulated_balance_amount_currency': lambda: aggregates.get('debit_amount', 0) - abs(aggregates.get('credit_amount', 0))
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
                
            self.write(row, column, aggregated_value, self.header_bold_style)
            column += 1

        return row + 2, 0

    def write_group(self, row, column, group_name, group, group_depth=0):
        group_name = group_name[1] if isinstance(group_name, tuple) and len(group_name) > 1 else group_name
        if group._groupby_type[group_depth] != 'boolean':
            group_name = group_name or _("Undefined")

        row, column = self._write_group_header(row, column, group_name, group, group_depth)

        for child_group_name, child_group in group.children.items():
            row, column = self.write_group(row, column, child_group_name, child_group, group_depth + 1)

        row = self.write_group_header(row)

        for record in group.data:
            row, column = self._write_row(row, column, record)
        
        row, column = self._write_group_totals(row, group)

        return row, column

    def _write_row(self, row, column, data):
        for value in data:
            self.write_cell(row, column, value)
            column += 1
        return row + 1, 0

    def write_group_header(self, row):
        for i, fieldname in enumerate(self.field_names):
            self.write(row, i, fieldname, self.header_style)
        self.worksheet.set_column(0, i, 30)  # Column width
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


    
    
    
    
    
    
    


    
