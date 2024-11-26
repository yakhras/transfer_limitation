from odoo import models, fields

class MonthRecord(models.Model):
    _name = 'month.record'
    _description = 'Month Record'

    name = fields.Char('Month Name', required=True)
