# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class LogisticsPort(models.Model):
    _name = 'logistics.port'
    _description = 'Port'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char('Port Name', required=True)
    code = fields.Char('Port Code', size=5)
    country_id = fields.Many2one('res.country', string='Country', required=True)
    city = fields.Char('City')
    timezone = fields.Selection([
        ('UTC', 'UTC'),
        ('UTC+1', 'UTC+1'), ('UTC+2', 'UTC+2'), ('UTC+3', 'UTC+3'), ('UTC+4', 'UTC+4'),
        ('UTC+5', 'UTC+5'), ('UTC+6', 'UTC+6'), ('UTC+7', 'UTC+7'), ('UTC+8', 'UTC+8'),
        ('UTC+9', 'UTC+9'), ('UTC+10', 'UTC+10'), ('UTC+11', 'UTC+11'), ('UTC+12', 'UTC+12'),
        ('UTC-1', 'UTC-1'), ('UTC-2', 'UTC-2'), ('UTC-3', 'UTC-3'), ('UTC-4', 'UTC-4'),
        ('UTC-5', 'UTC-5'), ('UTC-6', 'UTC-6'), ('UTC-7', 'UTC-7'), ('UTC-8', 'UTC-8'),
        ('UTC-9', 'UTC-9'), ('UTC-10', 'UTC-10'), ('UTC-11', 'UTC-11'), ('UTC-12', 'UTC-12'),
    ], string='Timezone', default='UTC')
    is_active = fields.Boolean('Active', default=True)
    notes = fields.Text('Notes')

    @api.depends('name', 'code')
    def name_get(self):
        result = []
        for port in self:
            name = port.name
            if port.code:
                name = f"[{port.code}] {name}"
            result.append((port.id, name))
        return result
    