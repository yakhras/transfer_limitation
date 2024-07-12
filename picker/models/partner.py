# -*- coding: utf-8 -*-

from odoo import models, fields, api



class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'   # Inherit the model

    transfer_limit = fields.Boolean(string='Transfer Limitation')

    @api.onchange('transfer_limit')
    def _onchange_transfer_limit(self):
        if (self.transfer_limit):
            self.credit_limit = self.risk_invoice_unpaid
        else:
            self.credit_limit = 0.0
        