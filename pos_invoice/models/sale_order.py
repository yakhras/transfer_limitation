from odoo import _, api, fields, models
import datetime


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_pos_created = fields.Boolean(string='Create from POS')


    @api.model
    def formal_invoice(self):
        return self.property_is_printed_invoice = True