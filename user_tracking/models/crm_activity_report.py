# -*- coding: utf-8 -*-

from odoo import models, fields


class ActivityReport(models.Model):

    _inherit = "crm.activity.report"


    lead_id = fields.Many2one('crm.lead', "Opportunity", readonly=False)



    def open_related_lead(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crm.lead',
            'view_mode': 'form',
            'res_id': self.lead_id.id,
            'target': 'current',
        }