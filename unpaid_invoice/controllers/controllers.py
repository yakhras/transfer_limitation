# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

class ExportData(http.Controller):

    @http.route('/get_data', auth="user", type='json')
    def fetch_exported_data(self, **kwargs):
        """
        Controller to fetch the required details.
        """
        model = kwargs['model']
        fields = kwargs['field']
        res_ids = kwargs['res_ids']
        field_labels = kwargs['exported_fields']
        columns_headers = [val['label'].strip() for val in field_labels]
        
        Model = request.env[model]
        records = Model.browse(res_ids)

        if kwargs['grouped_by']:
            return self._fetch_grouped_data(Model, fields, kwargs, columns_headers)
        else:
            export_data = records.export_data(fields).get('datas', [])
            return {'data': export_data, 'header': columns_headers}

    def _fetch_grouped_data(self, Model, fields, kwargs, columns_headers):
        """
        Fetch and group the data based on the grouped_by fields.
        """
        field_names = [f for f in fields]
        groupby_fields = kwargs['grouped_by']
        domain = kwargs['domain']
        
        groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby_fields]
        groups_data = Model.sudo().read_group(domain, field_names, groupby_fields, lazy=False)
        
        grouped_result = []
        for group in groups_data:
            record_ids = Model.search(group['__domain'])
            field_keys = [k for k in group.keys() if k in fields and k not in groupby_fields]
            export_data = [record_ids.export_data(fields).get('datas', [])]
            group_info = (
                {'count': group['__count']},
                group.get(groupby_fields[0]),
                export_data,
                [(group[k], fields.index(k)) for k in field_keys]
            )
            grouped_result.append(group_info)
        
        return {
            'header': columns_headers,
            'data': export_data,
            'type': groupby_type,
            'other': grouped_result
        }
    
    @http.route('/your_endpoint_to_send_pdf', type='json', auth='user')
    def send_pdf_email(self, pdf_data):
        # Decode the PDF data
        pdf_content = base64.b64decode(pdf_data)
        
        # Create attachment
        attachment = request.env['ir.attachment'].create({
            'name': 'Unpaid_Invoices.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': 'unpaid.invoice',
            # Specify the record if needed
        })

        return {'success': True}