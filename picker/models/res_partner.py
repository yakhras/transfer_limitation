# -*- coding: utf-8 -*-

from odoo import models, fields



class ResPartner(models.Model):
    _inherit = 'res.partner'   # Inherit the model

    transfer_limit = fields.Boolean('Tansfer Limit')
    