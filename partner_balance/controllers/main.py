# -*- coding: utf-8 -*-

import json
import operator
from datetime import datetime


from odoo.http import content_disposition, request
from odoo.tools import osutil, pycompat
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

            response_data = self.from_group_data(fields, tree)
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
        company_name = ''
        active_id = params.get('active_id')
        if active_id:
            partner_record = request.env['res.partner'].sudo().browse(active_id)
            if partner_record.exists() and partner_record.company_id:
                company_name = partner_record.company_id.name
        header_data = [
            f"Partner: {partner_name}" if partner_name else "",
            f"Company: {company_name}" if company_name else "",
            f"Export Date: {datetime.now().strftime('%Y-%m-%d')}"
        ]
        return [item for item in header_data if item]
    
    def from_data(self, fields, rows, params=None):
        with ExportXlsxWriter(fields, len(rows)) as xlsx_writer:
            # Write model name in the first row if provided
            # if partner_name:
            #     xlsx_writer.write(0, 0, f"Customer: {partner_name}", xlsx_writer.header_style)
            data = self.header_metadata(params)
            for row_index, header_info in enumerate(data):
                xlsx_writer.write(row_index, 0, header_info, xlsx_writer.header_style)
            
            for row_index, row in enumerate(rows):
                for cell_index, cell_value in enumerate(row):
                    if isinstance(cell_value, (list, tuple)):
                        cell_value = pycompat.to_text(cell_value)
                    xlsx_writer.write_cell(row_index + 5, cell_index, cell_value)

        return xlsx_writer.value
    
    def from_group_data(self, fields, groups):
        with GroupExportXlsxWriter(fields, groups.count) as xlsx_writer:
            x, y = 1, 0
            for group_name, group in groups.children.items():
                x, y = xlsx_writer.write_group(x, y, group_name, group)

        return xlsx_writer.value
    

class ExportXlsxWriter(BaseExportXlsxWriter):
    def write_header(self):
        for i, fieldname in enumerate(self.field_names):
            self.write(4, i, fieldname, self.header_style)
        self.worksheet.set_column(0, i, 30) # around 220 pixels


class GroupExportXlsxWriter(BaseGroupExportXlsxWriter):

    def write_group(self, row, column, group_name, group, group_depth=0):
        group_name = group_name[1] if isinstance(group_name, tuple) and len(group_name) > 1 else group_name
        if group._groupby_type[group_depth] != 'boolean':
            group_name = group_name or _("Undefined")

        row, column = self._write_group_header(row, column, group_name, group, group_depth)
        self.write(row, column, row, column)

        return row, column
    
    



