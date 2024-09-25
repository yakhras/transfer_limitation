        # -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class ResPartner(models.Model):
    _inherit = 'res.partner'   # Inherit the model

    transfer_limit = fields.Boolean(string='Transfer Limitation')

    '''@api.onchange('transfer_limit')
    def onchange_transfer_limit(self):
        lines = self.move_ids_without_package
        today = date.today() - timedelta(days=1)
        lines_value = 0.0
        for line in lines:
            sale_order = line.sale_line_id
            sub_total = sale_order.price_subtotal
            qty = sale_order.product_uom_qty
            done = line.quantity_done
            tax = sale_order.tax_id.amount
            currency = sale_order.currency_id
            currency_rate = currency.rate_type_ids.filtered(lambda x: x.name == today and x.rate_type_id.code == "forex_selling")
            inverse = currency_rate.inverse_company_rate
            if (currency.name == 'TRY'):
                line_value = (sub_total / qty ) * done * (1 + tax/100)
                lines_value = lines_value + line_value
            else:
                if (not currency_rate):
                    raise ValidationError(('Currency rate for today is not exists.\n\nPlease contact accounting manager to get this value.'))
                else:
                    line_value = (sub_total / qty ) * done * (1 + tax/100) * inverse
                    lines_value = lines_value + line_value
        if (self.transfer_limit):
            self.document_number = lines_value
        else:
            self.document_number = 123456.0'''
