# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_is_printed_invoice = fields.Boolean('Is Printed Invoice', default=False, company_dependent=True)
