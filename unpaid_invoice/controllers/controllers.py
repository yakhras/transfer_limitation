# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)


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
    def send_pdf(self, pdf_data):
        # Log the receipt of PDF data
        _logger.info("Received PDF data for email sending.")

        try:
            # Here you can save the PDF data or send it via email
            pdf_content = base64.b64decode(pdf_data)  # Decode if necessary

            # Optionally save it as an attachment
            request.env['ir.attachment'].create({
                'name': 'Generated_PDF.pdf',
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'your.model',  # Replace with the correct model
            })

            return {'success': True}
        except Exception as e:
            _logger.error("Error handling PDF data: %s", e)
            return {'success': False, 'error': str(e)}
        


class AccountMoveController(http.Controller):

    @http.route('/custom/fetch_account_moves', type='http', auth='user')
    def fetch_account_moves(self):
        # Define the domain as specified
        domain = [
            ('state', '=', 'posted'),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('payment_state', 'in', ['not_paid', 'partial']),
        ]
        
        # Search for records in account.move that meet the criteria
        account_moves = request.env['account.move'].search(domain)
        
        # Perform actions on the filtered records if necessary
        # For example, here we just log the fetched records' names
        
        # Redirect to a relevant page in Odoo, such as the list view of account moves
        return request.redirect('/web#action=account.action_move_out_invoice_type')
