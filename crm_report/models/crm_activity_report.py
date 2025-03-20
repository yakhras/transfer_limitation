# -*- coding: utf-8 -*-

from odoo import models, fields


class ActivityReport(models.Model):

    _inherit = "crm.activity.report"


    lead_id = fields.Many2one('crm.lead', "Opportunity", readonly=False)
    last_stage_update = fields.Datetime(
        string='field_nameLast Stage Update',
        related='lead_id.date_last_stage_update', index=True, store=True, readonly=True)
    

