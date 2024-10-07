from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class SaleOrder(models.Model):
    _inherit = 'sale.order'   # Inherit the model

    purchase = fields.Boolean(string='purchase')

    @api.onchange('purchase')
    def _onchange_purchase(self):
        order = self._get_purchase_orders()
        if (self.purchase):
            self.client_order_ref = order.name
        else:
            order.button_cancel()
            order._unlink_if_cancelled()
            self.client_order_ref = order