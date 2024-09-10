# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class CoffeeBrand(models.Model):
    _name = 'coffee.brand'
    _description = 'Coffee Brands'

    name = fields.Char("Brand")

