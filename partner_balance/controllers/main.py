# -*- coding: utf-8 -*-

import json
import operator
from datetime import datetime
import io
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import UserError



from odoo.http import content_disposition, request
from odoo.tools import osutil, pycompat
from odoo.tools.translate import _
from odoo.addons.web.controllers.main import ExcelExport as BaseExcelExport, GroupsTreeNode, ExportXlsxWriter, GroupExportXlsxWriter
from odoo.addons.web.controllers.main import ExportXlsxWriter as BaseExportXlsxWriter
from odoo.addons.web.controllers.main import GroupExportXlsxWriter as BaseGroupExportXlsxWriter
    
class ExcelExport(BaseExcelExport):

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
            tree = GroupsTreeNode(Model, field_names, groupby, groupby_type)
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
        active_id = params.get('active_id')
        if active_id:
            partner_record = request.env['res.partner'].sudo().browse(active_id)
            if partner_record.exists() and partner_record.company_id:
                company_name = partner_record.company_id.name
        header_data = [
            _("Report: %s") % action_name if action_name else "",
            f"Partner: {partner_name}" if partner_name else "",
            # f"Company: {company_name}" if company_name else "",
            # f"Export Date: {datetime.now().strftime('%Y-%m-%d')}",
            f"Date Range: From {date_from}" if date_from else "All" f"To: {date_to}" if date_to else f"Date To: {datetime.now().strftime('%Y-%m-%d')}",
            # f"Date To: {date_to}" if date_to else f"Date To: {datetime.now().strftime('%Y-%m-%d')}",
        ]
        return [item for item in header_data if item]
    
    def from_data(self, fields, rows, params=None):
        with ExportXlsxWriter(fields, len(rows)) as xlsx_writer:
            # Write model name in the first row if provided
            data = self.header_metadata(params)
            for row_index, header_info in enumerate(data):
                xlsx_writer.write(row_index, 0, header_info, xlsx_writer.header_style)
            
            # Write data rows
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    if isinstance(cell_value, (list, tuple)):
                        cell_value = pycompat.to_text(cell_value)
                    xlsx_writer.write_cell(row_index + 6, cell_index, cell_value)

            # Add totals row after all data
            total_row = len(rows) + 6 + 1  # +1 for spacing
            xlsx_writer._write_totals_from_rows(total_row, rows, fields)

        return xlsx_writer.value
        
    def from_group_data(self, fields, groups, params=None):
        with GroupExportXlsxWriter(fields, groups.count) as xlsx_writer:
            data = self.header_metadata(params)
            for row_index, header_info in enumerate(data):
                xlsx_writer.write(row_index, 0, header_info, xlsx_writer.header_style)
            x, y = 4, 0
            for group_name, group in groups.children.items():
                x, y = xlsx_writer.write_group(x, y, group_name, group)

        return xlsx_writer.value
    

class ExportXlsxWriter(BaseExportXlsxWriter):
    # def __init__(self, field_names, row_count=0):
    #     self.field_names = field_names
    #     self.output = io.BytesIO()
    #     self.workbook = xlsxwriter.Workbook(self.output, {'in_memory': True})
    #     self.base_style = self.workbook.add_format({'text_wrap': True})
    #     self.header_style = self.workbook.add_format({'bold': True, 'bg_color': "#f5f50e", 'border': 1})
    #     self.header_bold_style = self.workbook.add_format({'text_wrap': True, 'bold': True, 'bg_color': "#f5f50e"})
    #     self.date_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd'})
    #     self.datetime_style = self.workbook.add_format({'text_wrap': True, 'num_format': 'yyyy-mm-dd hh:mm:ss'})
    #     self.worksheet = self.workbook.add_worksheet()
    #     self.value = False
    #     self.float_format = '#,##0.00'
    #     decimal_places = [res['decimal_places'] for res in request.env['res.currency'].search_read([], ['decimal_places'])]
    #     self.monetary_format = f'#,##0.{max(decimal_places or [2]) * "0"}'

    #     if row_count > self.worksheet.xls_rowmax:
    #         raise UserError(_('There are too many rows (%s rows, limit: %s) to export as Excel 2007-2013 (.xlsx) format. Consider splitting the export.') % (row_count, self.worksheet.xls_rowmax))

    
    def write_header(self):
        for i, fieldname in enumerate(self.field_names):
            self.write(5, i, fieldname, self.header_style)
        self.worksheet.set_column(0, i, 30) # around 220 pixels

    
    def _write_totals_from_rows(self, row, rows_data, fields):
        # Calculate totals first
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
        
        # Calculate debit total
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
        
        # Calculate credit total
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
        
        # Calculate balance
        total_balance = total_debit - abs(total_credit)
        
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


class GroupExportXlsxWriter(BaseGroupExportXlsxWriter):

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
    
    def write_group_header(self, row):
        for i, fieldname in enumerate(self.field_names):
            self.write(row, i, fieldname, self.header_style)
        self.worksheet.set_column(0, i, 30)  # Column width
        return row + 1  # Return next row to continue from
    
    def write_header(self):
        return
    
    def _write_group_header(self, row, column, label, group, group_depth=0):
        label_text = '%s%s (%s)' % ('' * group_depth, label, group.count)

        # Write the label in the first column
        self.write(row, column, label_text, self.header_bold_style)

        # Apply the same style to all other columns in that row
        total_columns = len(self.fields)
        for col in range(1, total_columns):
            self.write(row, col, '', self.header_bold_style)

        return row + 1, 0


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
