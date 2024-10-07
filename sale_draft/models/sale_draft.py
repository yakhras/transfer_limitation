from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class SaleOrder(models.Model):
    _inherit = 'sale.order'   # Inherit the model

    purchase = fields.Boolean(string='purchase')

    @api.onchange('purchase')
    def _onchange_purchase(self):
        #order = self._get_purchase_orders()
        if (self.purchase):
            self.action_cancel()
            #self.client_order_ref = order.name
        else:
            # order.button_cancel()
            # order.unlink()
            # self.client_order_ref = self.qty_delivered
            self.client_order_ref = 'Yes'