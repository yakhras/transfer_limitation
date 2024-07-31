        # -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, timedelta



class AccountMove(models.Model):
    _inherit = 'account.move'   # Inherit the model


