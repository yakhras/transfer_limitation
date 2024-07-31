        # -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date, timedelta



class UnpaidInvoice(models.Model):
    _name = 'unpaid.invoice'
    _inherit = 'account.move'   # Inherit the model


