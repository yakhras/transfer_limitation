# -*- coding: utf-8 -*-

from odoo import models, fields

class CheckReportQueue(models.Model):
    _name = 'check.report.queue'
    _description = 'Queued Checks for Weekly Report'

    check_id = fields.Many2one('account.check', required=True, ondelete='cascade')
    status = fields.Selection([('holiday', 'Holiday'), ('week', 'Week')], required=True)
    emailed = fields.Boolean(default=False)
