from odoo import _, api, fields, models
import datetime


class ResPartner(models.Model):
    _inherit = 'res.partner'



    def formal_invoice(self):
        return self.write({property_is_printed_invoice: True})