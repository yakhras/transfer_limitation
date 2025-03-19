# -*- coding: utf-8 -*-

from odoo import models, fields


class ActivityReport(models.Model):

    _inherit = "crm.activity.report"


    lead_id = fields.Many2one('crm.lead', "Opportunity", readonly=False)
    