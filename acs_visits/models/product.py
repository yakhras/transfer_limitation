# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class product_template(models.Model):
    _inherit = 'product.template'

    is_visit = fields.Boolean("Visit Type Product", default=False, help="Set True if want to Invoice related visits only from SO.")

