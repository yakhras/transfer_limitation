from odoo import models, fields, api
from datetime import date, timedelta
from odoo.exceptions import ValidationError



class SaleOrder(models.Model):
    _inherit = 'sale.order'   # Inherit the model

    purchase = fields.Boolean(string='purchase')

    def action_unlock(self):
        super().action_unlock()
        self.action_cancel()
        self.action_draft()
        order = self._get_purchase_orders()
        order.button_cancel()
        order.unlink()
        
            