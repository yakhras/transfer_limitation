# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2022-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError


class ExportData(http.Controller):
    @http.route('/get_data', auth="user", type='json')
    def get_export_data(self, **kw):
        """
        controller to fetch required retails
        """
        field = kw['field']
        model = kw['model']
        Model = request.env[model]
        res_ids = kw['res_ids']
        field_label = kw['exported_fields']
        columns_headers = [val['label'].strip() for val in field_label]
        records = request.env[model].browse(res_ids)

        if kw['grouped_by']:
            field_names = [f for f in kw['field']]
            groupby_type = [Model._fields[x.split(':')[0]].type for x in
                            kw['grouped_by']]
            domain = kw['domain']

            groups_data = Model.sudo().read_group(domain,
                                                  field_names, kw['grouped_by'],
                                                  lazy=False)
            group_by = []
            for rec in groups_data:
                ids = Model.search(rec['__domain'])
                list_key = [x for x in rec.keys() if
                            x in kw['field'] and x not in kw['grouped_by']]
                new_export_data = [ids.export_data(field).get('datas', [])]
                group_tuple = (
                    {'count': rec['__count']}, rec.get(kw['grouped_by'][0]),
                    new_export_data,
                    [(rec[x], field.index(x)) for x in list_key])
                group_by.append(group_tuple)
            return {'header': columns_headers, 'data': new_export_data,
                    'type': groupby_type, 'other': group_by}
        else:
            new_export_data = records.export_data(field).get('datas', [])
            return {'data': new_export_data, 'header': columns_headers}



# class ExportData(http.Controller):
#     @http.route('/get_data', auth="user", type='json')
#     def fetch_export_data(self, **kwargs):
#         """
#         Controller to fetch required records for export.

#         :param kwargs: Dictionary containing request parameters
#         :return: JSON response with export data
#         """
#         # Extract parameters from the request
#         fields_to_export = kwargs.get('field', [])
#         model_name = kwargs.get('model')
#         record_ids = kwargs.get('res_ids', [])
#         field_labels = kwargs.get('exported_fields', [])
        
#         # Check for mandatory parameters
#         if not model_name or not record_ids:
#             raise UserError("Model name and record IDs are required.")
        
#         # Prepare headers for the exported data
#         column_headers = [label['label'].strip() for label in field_labels]

#         # Fetch records based on provided IDs
#         model = request.env[model_name]
#         records = model.browse(record_ids)

#         # Check if grouping is needed
#         grouped_by_fields = kwargs.get('grouped_by')
#         if grouped_by_fields:
#             return self._get_grouped_export_data(model, records, fields_to_export, grouped_by_fields, column_headers)

#         # Export data if no grouping
#         exported_data = records.export_data(fields_to_export).get('datas', [])
#         return {'data': exported_data, 'header': column_headers}

#     def _get_grouped_export_data(self, model, records, fields_to_export, grouped_by_fields, column_headers):
#         """
#         Helper method to fetch and organize grouped data for export.

#         :param model: Odoo model to operate on
#         :param records: Records to be exported
#         :param fields_to_export: Fields to export
#         :param grouped_by_fields: Fields to group by
#         :param column_headers: Headers for the exported data
#         :return: Grouped data for export
#         """
#         domain = kwargs.get('domain', [])

#         try:
#             # Fetch grouped data using read_group
#             grouped_data = model.sudo().read_group(domain, fields_to_export, grouped_by_fields, lazy=False)
#         except Exception as e:
#             raise UserError(f"Error fetching grouped data: {str(e)}")

#         grouped_export_data = []
#         for group in grouped_data:
#             ids = model.search(group['__domain'])
#             export_data = [ids.export_data(fields_to_export).get('datas', [])]

#             # Create a tuple for group summary
#             group_summary = (
#                 {'count': group['__count']},
#                 group.get(grouped_by_fields[0]),
#                 export_data,
#                 [(group[field], fields_to_export.index(field)) for field in fields_to_export if field in group]
#             )
#             grouped_export_data.append(group_summary)

#         return {
#             'header': column_headers,
#             'data': [],  # Assuming no individual record data needed when grouped
#             'type': [model._fields[f.split(':')[0]].type for f in grouped_by_fields],
#             'other': grouped_export_data
#         }

