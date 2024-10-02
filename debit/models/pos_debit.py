# -*- coding: utf-8 -*-

from odoo import api, fields, models,

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    cumulated_balance = fields.Monetary(readonly=False)