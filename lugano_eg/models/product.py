# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class CoffeeBrand(models.Model):
    _name = 'coffee.brand'
    _description = 'Coffee Brands'

    name = fields.Char(string="Brand")

class StrengthPoint(models.Model):
    _name = 'strength.point'
    _description = 'Strength Points'

    name = fields.Char(string="Name")

