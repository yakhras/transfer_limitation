# -*- coding: utf-8 -*-

from odoo import models
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class Picking(models.Model):
    _inherit = 'stock.picking'   # Inherit the model
    
    def button_validate(self):
        if (self.picking_type_code == 'outgoing'):
            if (self.partner_id.transfer_limit):
                if not self.env.context.get("bypass_risk", False):
                    for order in self:
                        exception_msg = order.transfer_evaluate()
                        if (exception_msg):
                            res =  self.env['transfer.limit.wizard']
                            res1 = res.create(
                                    {
                                        "exception_msg": exception_msg,
                                        "partner_id": order.partner_id.id,
                                        "origin_reference": "%s,%s" % ("stock.picking", order.id),
                                        "continue_method": "button_validate",
                                    }
                                ).action_show()        
                            return (res1)
        return super(Picking, self).button_validate()
        
    def transfer_evaluate(self):
        self.ensure_one()
        exception_msg = ""
        to_invoice = self.check_partner_to_invoice()
        draft_invoice = self.check_partner_draft_invoice()
        remaining_unpaid_limit = self.compute_remaining_unpaid_limit()
        remaining_open_limit = self.compute_remaining_open_limit()
        remaining_with_open = self.compare_with_open_limit()
        if (to_invoice == True):
            exception_msg = ("Customer has a previous order to invoice, before validate the transfer.\n")
        elif (draft_invoice == True):
            exception_msg = ("Customer has a Draft invoice need to post, before validate the transfer.\n")
        elif (remaining_unpaid_limit == True):
            exception_msg = ("Customer remaining unpaid invoice limit not enough to validate this transfer .\n")
        elif (remaining_open_limit == True):
            exception_msg = ("Customer remaining open invoice limit not enough to validate this transfer.\n")
        elif (remaining_with_open == True):
            exception_msg = ("Customer remaining OPEN invoice limit not enough to validate this transfer.\n")
        return exception_msg
    
    def check_partner_to_invoice(self):
        for order in self:
            sales = order.partner_id.sale_order_ids
            if (sales):
                status = sales.filtered(lambda x: x.invoice_status == "to invoice")
                if (status):
                    toinv = True
                else:
                    toinv = False
        return toinv
    
    def check_partner_draft_invoice(self):
        for order in self:
            invoices = order.partner_id.risk_invoice_draft  # Get 'account.move' recordset for this partner
            if (invoices):  # check if there are records in 'account.move' for this partner
                drftinv = True
            else:
                drftinv = False
        return drftinv
    
    def compute_remaining_unpaid_limit(self):
        for order in self:
            unpaid_used_value = order.partner_id.risk_invoice_unpaid
            unpaid_limit_value = order.partner_id.risk_invoice_unpaid_limit
            if (unpaid_used_value > 0):
                if (unpaid_used_value > unpaid_limit_value):
                    return True
    
    def compute_total_pay(self):
        for order in self:
            total_pay = 0
            unpaid_used_value = order.partner_id.risk_invoice_unpaid
            open_used_value = order.partner_id.risk_invoice_open
            if (unpaid_used_value < 0):
                if (open_used_value < 0):
                    total_pay = abs(unpaid_used_value + open_used_value)
                else:
                    total_pay = abs(unpaid_used_value)
            elif (open_used_value < 0):
                total_pay = abs(open_used_value)
        return total_pay
    
    def compare_transfer_pay(self):
        for order in self:
            transfer_value = order.compute_transfer_value()
            total_pay = order.compute_total_pay()
            remain = transfer_value - total_pay
            if (remain > 0):
                return True
                    
    def compare_with_open_limit(self):
        for order in self:
            open_limit_value = order.partner_id.risk_invoice_open_limit
            transfer_value = order.compute_transfer_value()
            total_pay = order.compute_total_pay()
            if (total_pay):
                remain = transfer_value - total_pay
                if (remain > 0):
                    if (remain > open_limit_value):
                        return True

    def compute_transfer_value(self):
        for order in self:
            lines = order.move_ids_without_package
            today = date.today() - timedelta(days=1)
            lines_value = 0
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
        return lines_value
    
    def compute_remaining_open_limit(self):
        for order in self:
            transfer_value = self.compute_transfer_value()
            open_limit_value = order.partner_id.risk_invoice_open_limit
            open_used_value = order.partner_id.risk_invoice_open
            if (open_used_value >= 0):
                open_remaining_value = open_limit_value - open_used_value
                remain_limit = transfer_value - open_remaining_value
                if (remain_limit > 0):
                    return True
    
    #raise UserError(('Customer unpaid invoice limit not enough to validate this transfer.'))
    #raise UserError(('Customer open invoice limit not enough to validate this transfer.'))
